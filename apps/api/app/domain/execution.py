from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Protocol

from app.domain.policy import PolicyDecision
from app.domain.decision import DecisionContext


class ExecutionError(Exception):
    pass


class RecoveryProviderResult:
    def __init__(self, status: str, provider_reference: Optional[str] = None, message: str = "", evidence: Dict[str, Any] | None = None):
        self.status = status
        self.provider_reference = provider_reference
        self.message = message
        self.evidence = evidence or {}


class RecoveryProvider(Protocol):
    def execute(self, action: str, context: DecisionContext, idempotency_key: str) -> RecoveryProviderResult:
        ...


EXEC_STATUS_EXECUTED = "EXECUTED"
EXEC_STATUS_FAILED = "FAILED"
EXEC_STATUS_REJECTED = "REJECTED"
EXEC_STATUS_PENDING = "PENDING"


@dataclass
class ExecutionResult:
    action: str
    status: str
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    provider_reference: Optional[str]
    message: str
    evidence: Dict[str, Any]


class ExecutionManager:
    def __init__(self, idempotency_store: Optional[object] = None):
        """
        idempotency_store: optional object implementing two methods:
          - get(action: str, idempotency_key: str) -> ExecutionResult|None
          - create(action, idempotency_key, execution_result_dict) -> ExecutionResult

        If not provided, falls back to an in-memory dict (not durable).
        """
        self._idempotency_store: Dict[str, ExecutionResult] = {}
        self._store = idempotency_store

    def _idempotency_key(self, idempotency_key: str, action: str) -> str:
        return f"{action}::{idempotency_key}"

    def execute(self, policy_decision: PolicyDecision, context: DecisionContext, idempotency_key: Optional[str], provider: RecoveryProvider) -> ExecutionResult:
        now = datetime.now(tz=timezone.utc)

        # Safety checks
        if idempotency_key is None or idempotency_key == "":
            raise ExecutionError("missing idempotency_key")
        if not isinstance(policy_decision, PolicyDecision):
            raise ExecutionError("policy_decision must be a PolicyDecision")
        if policy_decision.decision != "APPROVED" or not policy_decision.approved:
            raise ExecutionError("policy decision must be APPROVED to execute")

        action = policy_decision.action
        if not action:
            raise ExecutionError("approved policy must include an action")

        # idempotency lookup
        store_key = self._idempotency_key(idempotency_key, action)
        # durable store lookup if available
        if self._store is not None:
            existing = self._store.get(action, idempotency_key)
            if existing is not None:
                return existing
        else:
            if store_key in self._idempotency_store:
                return self._idempotency_store[store_key]

        # Supported actions are not enforced here; providers may reject unknowns
        # Perform provider execution
        started_at = now

        # Manual/non-provider actions: represent deterministically without calling provider
        manual_actions = {"manual_review", "collect_more_evidence", "create_recovery_case"}
        if action in manual_actions:
            exec_id = f"exec-{action}-{idempotency_key}"
            res = ExecutionResult(
                action=action,
                status=EXEC_STATUS_PENDING,
                execution_id=exec_id,
                started_at=started_at,
                completed_at=None,
                provider_reference=None,
                message="manual action - requires human",
                evidence={"manual": True},
            )
            # store idempotent result
            self._idempotency_store[store_key] = res
            return res

        # Otherwise call provider adapter
        provider_result = provider.execute(action, context, idempotency_key)

        # Map provider_result.status to execution statuses
        mapping = {
            "success": EXEC_STATUS_EXECUTED,
            "failed": EXEC_STATUS_FAILED,
            "pending": EXEC_STATUS_PENDING,
            "rejected": EXEC_STATUS_REJECTED,
        }
        status = mapping.get(provider_result.status, EXEC_STATUS_FAILED)
        completed_at = None if status == EXEC_STATUS_PENDING else datetime.now(tz=timezone.utc)
        exec_id = f"exec-{action}-{idempotency_key}"

        result = ExecutionResult(
            action=action,
            status=status,
            execution_id=exec_id,
            started_at=started_at,
            completed_at=completed_at,
            provider_reference=provider_result.provider_reference,
            message=provider_result.message,
            evidence=provider_result.evidence,
        )

        # persist idempotent result in store if provided, else in-memory
        if self._store is not None:
            self._store.create(action, idempotency_key, {
                "action": result.action,
                "status": result.status,
                "execution_id": result.execution_id,
                "started_at": result.started_at,
                "completed_at": result.completed_at,
                "provider_reference": result.provider_reference,
                "message": result.message,
                "evidence": result.evidence,
            })
        else:
            self._idempotency_store[store_key] = result
        return result
