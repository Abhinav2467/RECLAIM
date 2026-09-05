# Showcase Batch & Judge Evidence Playbook

> **RECLAIM Judge Playbook**: Scenario Proofs, Idempotency Verification & 3-Minute Demo Script

---

## 1. Overview

RECLAIM includes a deterministic **Showcase Batch Runner** ([`apps/api/app/api/demo.py`](../apps/api/app/api/demo.py)) designed to demonstrate RECLAIM's multi-scenario decisioning, capital preservation, and gateway outcome verification to hackathon judges.

---

## 2. Showcase Scenario Matrix

Executing `POST /api/demo/batch` creates a representative multi-case population:

| Scenario # | Scenario Code | Recoverable Amount | Initial State | Final State | Demonstration Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `auth_stale_verifying` | \$249.00 | `VERIFYING` | `VERIFYING` | Active gateway capture retry pending provider reconciliation. |
| **2** | `auth_stale_recovered` | \$1,499.00 | `VERIFYING` | `RECOVERED` | Capture simulation confirms settlement; risk drops to \$0.00. |
| **3** | `payment_failure_notify` | \$320.00 | `RECOMMENDATION_READY` | `RECOMMENDATION_READY` | Action Arena selects payment update customer notification. |
| **4** | `checkout_abandonment` | \$780.00 | `RECOMMENDATION_READY` | `RECOMMENDATION_READY` | Action Arena evaluates cart recovery email outreach. |
| **5** | `economically_unjustified` | \$47.00 | `NO_ACTION` | `NO_ACTION` | Net recovery $\le 0.00$; graph halts at Economic Gate (Capital Preserved). |
| **6** | `auth_stale_recovered_small` | \$89.00 | `VERIFYING` | `RECOVERED` | Small-value authorization capture recovery verification. |

---

## 3. Evidence & Proof Statements

### **Proof 1: Authoritative Outcome Verification (`RECOVERED`)**
* Select Case #2 (\$1,499.00 Stale Authorization).
* Click **Simulate Payment Capture**.
* **Evidence**: Case status transitions to `RECOVERED`. Current Risk Exposure drops from `\$1,499.00` to **`\$0.00`** in emerald. Portfolio aggregate *Verified Recovered* increases by `\$1,499.00`.

### **Proof 2: Intentional Non-Intervention (`NO_ACTION`)**
* Select Case #5 (\$47.00 Economically Unjustified Failure).
* Inspect the Visual Decision Engine (`/engine`).
* **Evidence**: The decision map intentionally halts at **Node 05 (Economic Gate)**. Future execution/verification nodes remain `BYPASSED`. Node Inspector correctly displays `Decision: NO_ACTION` and `Recommended Strategy: None (NO_ACTION)`. Portfolio aggregate *Capital Preserved* increases by `\$47.00`.

### **Proof 3: Showcase Batch Idempotency**
* Execute `POST /api/demo/batch` with `batch_run_id = "judge-test-1"`.
* Re-execute `POST /api/demo/batch` with identical `batch_run_id = "judge-test-1"`.
* **Evidence**: Both calls return HTTP 200 with identical case IDs (`cases_created` array). Zero duplicate orders or payments are inserted into PostgreSQL.

---

## 4. Suggested 3-Minute Judge Demo Script

1. **Minute 1: Executive Overview (`/operations`)**
   * Open `/operations`. Note the editorial financial position statement: *Revenue at Risk*, *Expected Net Recovery*, *Verified Recovered*, and *Capital Preserved*.
   * Click **⚡ Launch Showcase Batch** to seed representative cases.

2. **Minute 2: The Visual Decision Machine (`/engine`)**
   * Navigate to `/engine`. Select Case #1 (\$249.00 Stale Authorization).
   * Click **▶ Replay Decision**. Watch the case token travel through Event Gate → Revenue Truth → Diagnosis → Action Arena → Economic Gate → Policy Gate → Execution Dispatch → Verification.
   * Observe the **Action Arena**: Competing candidate strategies appear; non-viable options recede while `attempt_capture_retry` wins with `+\$186.25 Net`.

3. **Minute 3: Proof of `NO_ACTION` & Recovery Verification**
   * Switch to Case #5 (\$47.00 Failure). Replay the decision. Watch the engine halt at Stage 05 displaying `SYSTEM STOPPED // CAPITAL PRESERVED: \$47.00`.
   * Return to Case #1 (\$249.00). Click **Simulate Payment Capture**. Watch the risk transition to `\$0.00` in emerald (`RECOVERED`).

---

*RECLAIM — Showcase Batch & Judge Evidence Playbook.*
