# Test Strategy & Verification Invariants

> **RECLAIM Verification**: 185 Verified Unit, Integration, Scenario & System Invariant Tests (185 passed, 0 failed, 0 skipped, 0 warnings)

---

## 1. Test Strategy & Financial Invariants

In financial software, automated test suites are not merely code quality checks—they are **mathematical proofs of system correctness**. RECLAIM enforces four core system invariants across all test modules ([`apps/api/tests`](../apps/api/tests)):

1. **Invariant 1 (Monetary Non-Negative Conservation)**: $A_{\text{recoverable}} = A_{\text{expected}} - A_{\text{captured}} \ge 0$. Current Risk Exposure equals \$0.00 **only** when $A_{\text{captured}} = A_{\text{expected}}$.
2. **Invariant 2 (Economic Decision Rationality)**: An action $a$ is selected if and only if Expected Net Recovery $(a) > 0$ and $a$ is eligible. Otherwise, status **must** equal `NO_ACTION`.
3. **Invariant 3 (Execution Separation)**: Dispatching an intervention transitions status to `EXECUTING` or `VERIFYING`. Risk exposure **must not** drop to \$0.00 upon execution dispatch.
4. **Invariant 4 (Active Case Uniqueness & Idempotency)**: Re-delivering identical webhook events or re-running showcase batch IDs produces 0 duplicate active cases or duplicate financial records.

---

## 2. Test Suite Execution & Results

### **Backend Pytest Suite Results (`apps/api`)**
```bash
PYTHONPATH=. .venv/bin/pytest tests/
PYTHONPATH=. .venv/bin/python scripts/test_app_flows.py
```
**Output**: `185 passed in 8.32s` (0 failed, 0 skipped, 0 warnings).

### **Frontend Build & Typecheck (`apps/web`)**
```bash
npm run build
npx tsc --noEmit
```
**Output**: `✓ 9/9 App Router Static Pages Compiled (0 TypeScript Errors)`.

---

## 3. Test File Inventory & Categorization

| Test File | Items | Verification Scope |
| :--- | :--- | :--- |
| `tests/test_actions.py` | 7 | Action candidate generation & eligibility ranking |
| `tests/test_auth.py` | 8 | Password hashing, session tokens, login/signup API & merchant isolation |
| `tests/test_decision.py` | 10 | Economic decision formula, gross vs net recovery, `NO_ACTION` selection |
| `tests/test_decision_agent.py` | 10 | LangGraph decision agent transitions & state pipeline execution |
| `tests/test_demo_scenario_api.py` | 8 | Showcase scenario runner, batch idempotency & state verification |
| `tests/test_diagnosis.py` | 13 | Contextual failure classification, stale auth detection & confidence ratings |
| `tests/test_economics.py` | 9 | Net recovery arithmetic, probability weighting & friction cost deduction |
| `tests/test_execution.py` | 8 | Bounded action dispatch, execution idempotency & status transitions |
| `tests/test_executive_summary.py` | 5 | Executive summary formatting & contextual explanation synthesis |
| `tests/test_policy.py` | 14 | Context version freshness, autonomous budget caps & contact fatigue guardrails |
| `tests/test_probability.py` | 9 | Contextual probability estimations & heuristic bound assertions |
| `tests/test_razorpay_adapter.py` | 5 | Provider adapter protocol conformance & disabled mode bounds |
| `tests/test_razorpay_normalizer.py` | 10 | Gateway payload mapping & webhook event normalization |
| `tests/test_razorpay_webhook.py` | 5 | Webhook signature verification & missing header handling |
| `tests/test_razorpay_webhook_processing.py` | 5 | End-to-end webhook processing & state reconciliation |
| `tests/test_reconciler.py` | 10 | Gateway capture reconciliation & order status updates |
| `tests/test_recovery_cases_api.py` | 4 | Cases explorer API, detail view snapshots & error handling |
| `tests/test_recovery_overview.py` | 5 | Portfolio aggregate calculations (*Revenue at Risk*, *Recovered*, *Capital Preserved*) |
| `tests/test_recovery_persistence.py` | 5 | Case persistence, state event appending & concurrency control |
| `tests/test_recovery_pipeline.py` | 8 | Pipeline orchestrator, context building & 2-step verification loop |
| `tests/test_revenue_truth.py` | 12 | Expected vs captured accounting, recoverable exposure & currency rules |
| `tests/test_sse_stream_api.py` | 3 | Real-time SSE streaming, cursor resuming & terminal event handling |
| `tests/test_verification.py` | 6 | Verification engine, `EXECUTED` vs `RECOVERED` state boundaries |
| `scripts/test_app_flows.py` | 6 | Full end-to-end FastAPI application state flow execution script |

---

*RECLAIM — Test Strategy & Verification Invariants.*
