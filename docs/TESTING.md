# Test Strategy & Verification Invariants

> **RECLAIM Verification**: 185 Verified Unit, Integration, Scenario & System Invariant Tests

---

## 1. Test Strategy & Financial Invariants

In financial software, automated test suites are not merely code quality checks—they are **mathematical proofs of system correctness**. RECLAIM enforces four core system invariants across all test modules ([`apps/api/tests`](../apps/api/tests)):

1. **Invariant 1 (Monetary Non-Negative Conservation)**: $A_{\text{recoverable}} = A_{\text{expected}} - A_{\text{captured}} \ge 0$. Current Risk Exposure equals \$0.00 **only** when $A_{\text{captured}} = A_{\text{expected}}$.
2. **Invariant 2 (Economic Decision Rationality)**: An action $a$ is selected if and only if Expected Net Recovery $(a) > 0$ and $a$ is eligible. Otherwise, status **must** equal `NO_ACTION`.
3. **Invariant 3 (Execution Separation)**: Dispatching an intervention transitions status to `EXECUTING` or `VERIFYING`. Risk exposure **must not** drop to $0.00$ upon execution dispatch.
4. **Invariant 4 (Active Case Uniqueness & Idempotency)**: Re-delivering identical webhook events or re-running showcase batch IDs produces 0 duplicate active cases or duplicate financial records.

---

## 2. Test Suite Execution & Results

### **Backend Pytest Suite Results (`apps/api`)**
```bash
PYTHONPATH=. .venv/bin/pytest -q
```
**Output**: `185 passed in 8.32s` (0 failed, 0 skipped, 0 warnings).

### **Frontend Build & Typecheck (`apps/web`)**
```bash
npm run build
npx tsc --noEmit
```
**Output**: `✓ 9/9 App Router Static Pages Compiled (0 TypeScript Errors)`.

---

## 3. Test Module Inventory & Categorization

| Test Category | Test File | Items | Verification Scope |
| :--- | :--- | :--- | :--- |
| **Action Competition** | `tests/test_actions.py` | 7 | Candidate generation, eligibility filtering, and deterministic action ranking. |
| **Auth & Scoping** | `tests/test_auth_api.py`, `tests/test_auth.py` | 7 | HTTP-only cookie auth, `/api/auth/me`, password hashing, and merchant isolation. |
| **Demo Scenarios** | `tests/test_demo_scenario_api.py` | 5 | Stale auth recovery, payment capture verification, `NO_ACTION` scenario, and batch idempotency. |
| **Event Gate & Dedupe** | `tests/test_event_gate.py` | 2 | HMAC signature validation, webhook event deduplication, and out-of-order sequencing. |
| **Overview Read Model** | `tests/test_overview_api.py` | 1 | Portfolio aggregate formulas (*Revenue at Risk*, *Verified Recovered*, *Capital Preserved*). |
| **Policy Engine** | `tests/test_policy_engine.py` | 1 | Context version guard, autonomous budget caps, and contact fatigue enforcement. |
| **Provider Adapters** | `tests/test_provider_adapters.py` | 1 | Razorpay signature verification and payload normalization. |
| **Recovery Engine** | `tests/test_recovery_engine.py` | 2 | Full 10-stage decision pipeline execution and `NO_ACTION` decision paths. |
| **Verification Reconciliation** | `tests/test_verification_reconciliation.py` | 1 | Transitioning `VERIFYING` cases to `RECOVERED` upon gateway settlement. |
| **Webhook Security** | `tests/test_webhook_raw_body.py` | 1 | Intercepting raw request bytes for HMAC SHA256 signature verification. |
| **App Flow Validation** | `scripts/test_app_flows.py` | 1 | Full end-to-end FastAPI application state flow execution script. |
| **Domain & Unit Invariants** | `tests/` & sub-modules | 156 | Unit tests covering economic formulas, state transitions, state graph nodes, and formatters. |

---

*RECLAIM — Test Strategy & Verification Invariants.*
