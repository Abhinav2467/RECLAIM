# Safety, Policy & Autonomous Guardrails

> **RECLAIM Safety Framework**: Multi-Layered Policy Bounds & Bounded Autonomy Enforcement

---

## 1. Overview

RECLAIM implements strict policy guardrails at every phase of the decision lifecycle ([`apps/api/app/domain/policy.py`](../apps/api/app/domain/policy.py)). An intervention is dispatched **only** if it passes both the economic test ($\text{Net Recovery} > 0.00$) and all policy safety checks.

---

## 2. Five-Phase Safety Architecture

```
BEFORE DECISION  ──►  DURING DECISION  ──►  BEFORE EXECUTION  ──►  DURING EXECUTION  ──►  AFTER EXECUTION
Stale Context        Action Arena          Policy Approval         Bounded Dispatch        Reconciliation
Protection           Net Calc > 0          Safety Checks           Exec != Rec             Gateway Truth
```

### **1. Before Decision (Context Freshness Guard)**
* Checks that `context_version` matches the case version (`version`).
* Rejects decision evaluation if new gateway events arrived after context building began.

### **2. During Decision (Economic Viability Gate)**
* Verifies that Expected Net Recovery > \$0.00.
* If Expected Net Recovery $\le 0.00$, selects **`NO_ACTION`** (Capital Preserved).

### **3. Before Execution (Policy Safety Approval Gate)**
* **Autonomous Budget Cap**: Checks that merchant monthly intervention expenditure has not exceeded the designated cap.
* **Contact Fatigue Guard**: Restricts customer outreach (email/SMS retry links) to a maximum of 1 attempt per 24 hours.
* **Candidate Eligibility**: Confirms that action preconditions are met for the specific failure code.

### **4. During Execution (Bounded Dispatch Boundary)**
* Action dispatch is executed within a strictly bounded adapter boundary ([`apps/api/app/domain/execution.py`](../apps/api/app/domain/execution.py)).
* Transitions status to `EXECUTING` / `VERIFYING`. *Execution completion is never treated as proof of recovery.*

### **5. After Execution (Authoritative Gateway Verification)**
* Current risk exposure remains exposed until gateway reconciliation processes a signed webhook confirming payment settlement (`payment_state = 'captured'`).
* Only gateway settlement transitions case status to `RECOVERED` and risk to `\$0.00`.

---

## 3. Implemented Policy Checks Inventory

| Policy Check | Rule Definition | Failure Result | Source Module |
| :--- | :--- | :--- | :--- |
| **Context Freshness** | `context_version == case.version` | Re-evaluate pipeline | `policy.py` |
| **Action Eligibility** | `action in eligible_actions(diagnosis_code)` | Candidate eliminated | `actions.py` |
| **Economic Viability** | `expected_net_recovery > 0.0` | Select `NO_ACTION` | `economics.py` |
| **Autonomous Budget** | `merchant_monthly_spend + cost <= budget_cap` | Route to `NEEDS_REVIEW` | `policy.py` |
| **Contact Fatigue** | `last_outreach_at < now - 24h` | Suppress outreach | `policy.py` |
| **State Separation** | `status != 'RECOVERED' until provider capture` | Remain in `VERIFYING` | `verification.py` |

---

## 4. Immutable Audit Ledger

Every decision event, policy check result, state transition, and provider response emits an immutable audit record to `case_audit_events` ([`apps/api/app/services/audit.py`](../apps/api/app/services/audit.py)):

```json
{
  "id": 8492,
  "case_id": 1614,
  "event_type": "POLICY_CHECK_PASSED",
  "actor": "PolicyEngine",
  "message": "Policy gate approved action 'attempt_capture_retry' (context_version=1, budget_ok=true).",
  "occurred_at": "2026-09-04T19:54:58.102Z"
}
```

---

*RECLAIM — Safety, Policy & Autonomous Guardrails.*
