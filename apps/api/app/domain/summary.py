from dataclasses import dataclass
from typing import Protocol, Dict, Any, Optional
from app.core.config import settings


@dataclass(frozen=True)
class ExecutiveSummaryResult:
    text: str
    provider: str
    authoritative: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "provider": self.provider,
            "authoritative": self.authoritative,
        }


class ExecutiveSummaryGenerator(Protocol):
    def generate_summary(self, snapshot: Dict[str, Any]) -> ExecutiveSummaryResult:
        ...


class DeterministicFallbackSummaryGenerator:
    """Returns the existing authoritative deterministic rationale."""

    def generate_summary(self, snapshot: Dict[str, Any]) -> ExecutiveSummaryResult:
        rationale = snapshot.get("decision_rationale") or "Deterministic rationale unavailable."
        return ExecutiveSummaryResult(
            text=str(rationale),
            provider="deterministic",
            authoritative=False,
        )


class MockExecutiveSummaryGenerator:
    """Produces a clearly labeled, deterministic executive-friendly summary from immutable decision snapshot."""

    def generate_summary(self, snapshot: Dict[str, Any]) -> ExecutiveSummaryResult:
        try:
            decision = snapshot.get("decision") or "NO_ACTION"
            diag = snapshot.get("diagnosis") or "UNKNOWN"
            amount = snapshot.get("recoverable_amount") or "0.00"
            currency = snapshot.get("currency") or "USD"
            action = snapshot.get("recommended_action")

            if decision == "NO_ACTION" or not action:
                text = (
                    f"RECLAIM Executive Summary (Mock AI): Evaluated failure event for {diag}. "
                    f"All candidate actions yielded expected net recovery <= $0.00. "
                    f"Recommended NO_ACTION to preserve merchant capital."
                )
            else:
                text = (
                    f"RECLAIM Executive Summary (Mock AI): Analyzed {diag} event for ${amount} {currency}. "
                    f"Recommended autonomous action '{action}' to maximize expected net recovery under merchant policy constraints."
                )

            return ExecutiveSummaryResult(
                text=text,
                provider="mock",
                authoritative=False,
            )
        except Exception:
            return DeterministicFallbackSummaryGenerator().generate_summary(snapshot)


def get_summary_generator(provider_name: Optional[str] = None) -> ExecutiveSummaryGenerator:
    name = (provider_name or getattr(settings, "llm_provider", "disabled")).lower()
    if name == "mock":
        return MockExecutiveSummaryGenerator()
    return DeterministicFallbackSummaryGenerator()


def generate_executive_summary(snapshot: Dict[str, Any], provider_name: Optional[str] = None) -> Dict[str, Any]:
    """Safe helper that invokes generator with immutable snapshot and guarantees fallback on error."""
    try:
        generator = get_summary_generator(provider_name)
        result = generator.generate_summary(snapshot)
        return result.to_dict()
    except Exception:
        fallback = DeterministicFallbackSummaryGenerator().generate_summary(snapshot)
        return fallback.to_dict()
