from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select, update

from app.db.session import SessionLocal
from app.db.models import RecoveryCase, RecoveryAuditEvent, ExecutionRecord
from app.domain.execution import ExecutionResult as DomainExecutionResult


class RecoveryRepository:
    def __init__(self, db=None):
        self.db = db or SessionLocal()

    def create_case(self, merchant_id: int, customer_id: Optional[int], order_id: Optional[int], payment_id: Optional[int], status: str, reason: Optional[str], details: Optional[dict], context_version: Optional[int], recoverable_amount: Optional[str], currency: Optional[str]) -> RecoveryCase:
        rc = RecoveryCase(
            merchant_id=merchant_id,
            customer_id=customer_id,
            order_id=order_id,
            payment_id=payment_id,
            status=status,
            version=1,
            reason=reason,
            details=details,
            context_version=context_version,
            recoverable_amount=recoverable_amount,
            currency=currency,
        )
        try:
            self.db.add(rc)
            self.db.commit()
            self.db.refresh(rc)
            return rc
        except IntegrityError:
            self.db.rollback()
            # Database unique constraint prevented duplicate active case creation. Fetch and return existing active case.
            query = select(RecoveryCase).where(
                RecoveryCase.merchant_id == merchant_id,
                RecoveryCase.status.not_in([
                    "RECOVERED",
                    "NO_ACTION",
                    "NOT_RECOVERABLE",
                    "FAILED",
                    "ABORTED",
                ]),
            )
            if payment_id is not None:
                query = query.where(RecoveryCase.payment_id == payment_id)
            elif order_id is not None:
                query = query.where(RecoveryCase.order_id == order_id)

            existing = self.db.execute(query).scalars().first()
            if existing is None:
                raise
            return existing

    def append_event(self, recovery_case_id: int, event_type: str, actor: Optional[str], action: Optional[str], status: Optional[str], idempotency_key: Optional[str], evidence: Optional[Dict[str, Any]], message: Optional[str]) -> RecoveryAuditEvent:
        ev = RecoveryAuditEvent(
            recovery_case_id=recovery_case_id,
            event_type=event_type,
            event_version=1,
            actor=actor,
            action=action,
            status=status,
            idempotency_key=idempotency_key,
            evidence=evidence,
            message=message,
        )
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    def create_execution_record(self, recovery_case_id: Optional[int], action: str, idempotency_key: str, status: str, provider_reference: Optional[str], started_at: Optional[datetime], completed_at: Optional[datetime], result: Optional[dict]) -> ExecutionRecord:
        er = ExecutionRecord(
            recovery_case_id=recovery_case_id,
            action=action,
            idempotency_key=idempotency_key,
            status=status,
            provider_reference=provider_reference,
            started_at=started_at,
            completed_at=completed_at,
            result=result,
        )
        try:
            self.db.add(er)
            self.db.commit()
            self.db.refresh(er)
            return er
        except IntegrityError:
            self.db.rollback()
            # existing record — fetch and return
            q = self.db.execute(select(ExecutionRecord).where(ExecutionRecord.action == action, ExecutionRecord.idempotency_key == idempotency_key)).scalars().first()
            if q is None:
                raise
            return q

    def get_execution_record(self, action: str, idempotency_key: str) -> Optional[ExecutionRecord]:
        return self.db.execute(select(ExecutionRecord).where(ExecutionRecord.action == action, ExecutionRecord.idempotency_key == idempotency_key)).scalars().first()

    def _execution_record_by_execution_id(self, execution_id: str) -> Optional[ExecutionRecord]:
        return self.db.execute(
            select(ExecutionRecord).where(
                func.concat("exec-", ExecutionRecord.action, "-", ExecutionRecord.idempotency_key) == execution_id
            )
        ).scalars().first()

    def update_case_with_version(self, case_id: int, expected_version: int, updates: dict) -> Optional[RecoveryCase]:
        # optimistic concurrency: only update if version matches expected_version
        stmt = (
            update(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .where(RecoveryCase.version == expected_version)
            .values(**updates, version=expected_version + 1)
            .execution_options(synchronize_session=False)
        )
        res = self.db.execute(stmt)
        if res.rowcount == 0:
            self.db.rollback()
            return None
        self.db.commit()
        case = self.db.get(RecoveryCase, case_id)
        return case

    def record_execution(self, recovery_case_id: int, action: str, idempotency_key: str, status: str, provider_reference: Optional[str] = None, result: Optional[dict] = None) -> ExecutionRecord:
        now = datetime.now(timezone.utc)
        return self.create_execution_record(
            recovery_case_id=recovery_case_id,
            action=action,
            idempotency_key=idempotency_key,
            status=status,
            provider_reference=provider_reference,
            started_at=now,
            completed_at=now if status in ("EXECUTED", "FAILED") else None,
            result=result,
        )

    def record_verification(self, execution_id: str, verification_outcome: str, evidence: Optional[dict] = None) -> Optional[ExecutionRecord]:
        er = self._execution_record_by_execution_id(execution_id)
        if er is None:
            return None
        er.status = verification_outcome
        if evidence:
            er.result = {**(er.result or {}), "verification_evidence": evidence}
        self.db.commit()
        self.db.refresh(er)
        return er

    def get_case(self, case_id: int) -> Optional[RecoveryCase]:
        return self.db.get(RecoveryCase, case_id)


class PostgresIdempotencyStore:
    def __init__(self, db=None):
        self.repo = RecoveryRepository(db=db)

    def get(self, action: str, idempotency_key: str):
        er = self.repo.get_execution_record(action=action, idempotency_key=idempotency_key)
        if er is None:
            return None
        return DomainExecutionResult(
            action=er.action,
            status=er.status or "PENDING",
            execution_id=f"exec-{er.action}-{er.idempotency_key}",
            started_at=er.started_at or datetime.now(timezone.utc),
            completed_at=er.completed_at,
            provider_reference=er.provider_reference,
            message=(er.result.get("message") if isinstance(er.result, dict) else ""),
            evidence=er.result or {},
        )

    def create(self, action: str, idempotency_key: str, payload: dict):
        case_id = None
        if isinstance(payload, dict) and isinstance(payload.get("evidence"), dict):
            case_id = payload["evidence"].get("case_id")
        return self.repo.create_execution_record(
            recovery_case_id=case_id,
            action=action,
            idempotency_key=idempotency_key,
            status=payload.get("status", "PENDING") if isinstance(payload, dict) else "PENDING",
            provider_reference=payload.get("provider_reference") if isinstance(payload, dict) else None,
            started_at=payload.get("started_at") if isinstance(payload, dict) else None,
            completed_at=payload.get("completed_at") if isinstance(payload, dict) else None,
            result=payload.get("evidence") if isinstance(payload, dict) and isinstance(payload.get("evidence"), dict) else payload,
        )

    def save(self, action: str, idempotency_key: str, result: DomainExecutionResult):
        return self.repo.record_execution(
            recovery_case_id=result.evidence.get("case_id") if isinstance(result.evidence, dict) else None,
            action=action,
            idempotency_key=idempotency_key,
            status=result.status,
            provider_reference=result.provider_reference,
            result=result.evidence if isinstance(result.evidence, dict) else {},
        )

    def record_execution(self, recovery_case_id: int, action: str, idempotency_key: str, status: str, provider_reference: Optional[str] = None, result: Optional[dict] = None) -> ExecutionRecord:
        return self.repo.record_execution(
            recovery_case_id=recovery_case_id,
            action=action,
            idempotency_key=idempotency_key,
            status=status,
            provider_reference=provider_reference,
            result=result,
        )

    def get_execution_record(self, action: str, idempotency_key: str) -> Optional[ExecutionRecord]:
        return self.repo.get_execution_record(action=action, idempotency_key=idempotency_key)
