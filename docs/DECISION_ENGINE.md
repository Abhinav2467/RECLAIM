# Bounded Autonomous Decision Engine

> **RECLAIM Decision Engine**: Contextual Logic, Action Competition & Economic Net Recovery Computation

---

## 1. Decision Pipeline Pipeline Architecture

The RECLAIM decision pipeline ([`apps/api/app/domain`](../apps/api/app/domain)) evaluates payment anomalies through seven sequential processing stages:

```
[Context Builder] ──► [Diagnosis Engine] ──► [Action Arena] ──► [Economic Engine]
                                                                        │
[Verification]   ◄── [Execution Dispatch] ◄── [Policy Gate]   ◄── [Decision Agent]
```

---

## 2. Decision Stage Deep-Dive

### **Stage 1: Context Builder** ([`context_builder.py`](../apps/api/app/domain/context_builder.py))
Extracts order intent, payment history, provider failure codes, customer profiles, and contextual state versioning.
* Input: `payment_id: int`
* Output: `DecisionContext` containing `recoverable_amount`, `currency`, `failure_code`, `provider_state`, `context_version`.

### **Stage 2: Contextual Diagnosis Engine** ([`diagnosis.py`](../apps/api/app/domain/diagnosis.py))
Classifies payment anomaly context into standardized categories:
* `AUTHORIZATION_STALE`: Hold uncaptured past provider deadline (e.g., > 7 days).
* `GATEWAY_TIMEOUT`: Temporary bank/network routing failure.
* `CHECKOUT_ABANDONED`: Order created with intent, payment left incomplete.
* Output: `DiagnosisResult(code="AUTHORIZATION_STALE", confidence="HIGH", confidence_score=0.984)`

### **Stage 3: Action Arena Competition** ([`actions.py`](../apps/api/app/domain/actions.py))
Generates candidate recovery strategies for the diagnosed context:
* `attempt_capture_retry`: Re-authorize and capture payment hold via gateway API.
* `manual_review`: Queue case for human merchant operator inspection.
* `collect_evidence`: Request updated payment method or dispute documentation.
* `notify_customer`: Send failure notification and payment retry link.
* Output: Array of `ActionEvaluationCandidate` objects with contextual eligibility status (`eligible: bool`, `why_not: str`).

### **Stage 4: Economic Engine Computation** ([`economics.py`](../apps/api/app/domain/economics.py))
Calculates expected financial net return for each candidate action $a$:

$$\text{Gross Recovery}(a) = A_{\text{recoverable}} \times P(\text{success} \mid \text{context}, a)$$

$$\text{Expected Net Recovery}(a) = \text{Gross Recovery}(a) - C(\text{cost}, a)$$

Where:
* $A_{\text{recoverable}}$: Recoverable amount at risk.
* $P(\text{success})$: Estimated probability of recovery for context and action.
* $C(\text{cost})$: Total intervention friction cost (gateway retry fees, SMS/email charges, operational overhead).

### **Stage 5: Decision Agent Strategy Selection** ([`decision.py`](../apps/api/app/domain/decision.py))
Evaluates the candidate pool:
* Finds action $a^*$ maximizing Expected Net Recovery among eligible actions.
* If Expected Net Recovery $(a^*) > 0$, selects $a^*$ as `RECOMMENDATION_READY`.
* If all candidates yield $\le 0.00$ or are ineligible, selects **`NO_ACTION`**.

### **Stage 6: Bounded Policy Safety Gate** ([`policy.py`](../apps/api/app/domain/policy.py))
Verifies decision safety:
1. `context_version` matches current case version (Stale Context Protection).
2. Action is eligible for current failure code.
3. Autonomous recovery budget is unexhausted.
4. Contact fatigue limits respected (< 1 attempt / 24h).

### **Stage 7: Execution Dispatch & Verification** ([`execution.py`](../apps/api/app/domain/execution.py) & [`verification.py`](../apps/api/app/domain/verification.py))
Dispatches bounded action to gateway adapter (`status = EXECUTING / VERIFYING`). Enforces `EXECUTED` $\neq$ `RECOVERED`. Transitions current risk exposure to **`\$0.00`** in emerald (`RECOVERED`) **only** when gateway webhook reconciliation confirms payment capture.

---

## 3. Walkthrough 1: \$249.00 Stale Authorization Recovery

### **Context & Inputs**:
* Order: `ord_demo_testrun1`, Payment: `pay_demo_testrun1`
* Expected Amount: `\$249.00`, Captured: `\$0.00`, Recoverable: `\$249.00`
* Provider State: `authorized` (7 days old)

### **Action Arena Evaluations**:

| Candidate Action | Eligible | Success Prob ($P$) | Cost ($C$) | Gross Expected | Expected Net Recovery | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`attempt_capture_retry`** | **Yes** | **75.0%** | **\$0.50** | **\$186.75** | **+\$186.25** | **SELECTED WINNER** |
| `manual_review` | Yes | 40.0% | \$15.00 | \$99.60 | +\$84.60 | Replaced (Lower Net) |
| `collect_evidence` | Yes | 30.0% | \$25.00 | \$74.70 | +\$49.70 | Replaced (Lower Net) |
| `notify_customer` | No | N/A | \$0.10 | \$0.00 | $\le 0.00$ | Ineligible Context |

### **Execution & Outcome**:
1. Net Recovery = **`+\$186.25`** > \$0.00 → Decision: `attempt_capture_retry`.
2. Policy Gate checks: Context v1 current, Autonomous budget approved → Status: `APPROVED`.
3. Execution Dispatch: Calls Razorpay capture adapter → Status: `VERIFYING` (Risk remains `\$249.00`).
4. Gateway Reconciliation: Webhook arrives with `payment_state = captured` → Status: **`RECOVERED`**, Current Risk = **`\$0.00`**.

---

## 4. Walkthrough 2: \$47.00 Unviable Recovery (`NO_ACTION`)

### **Context & Inputs**:
* Order: `ord_demo_no_action`, Payment: `pay_demo_no_action`
* Expected Amount: `\$47.00`, Captured: `\$0.00`, Recoverable: `\$47.00`
* Failure Code: Small-value unviable recovery context

### **Action Arena Evaluations**:

| Candidate Action | Eligible | Success Prob ($P$) | Cost ($C$) | Gross Expected | Expected Net Recovery | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `attempt_capture_retry` | No | 65.0% | \$50.00 | \$30.55 | -\$19.45 | Ineligible / Net $\le 0.00$ |
| `manual_review` | Yes | 40.0% | \$25.00 | \$18.80 | -\$6.20 | Net $\le 0.00$ |
| `notify_customer` | Yes | 5.0% | \$1.00 | \$2.35 | +\$1.35 | Below Threshold |

### **Execution & Outcome**:
1. All candidates yield $\le 0.00$ expected net return or fall below policy thresholds.
2. Decision Agent selects **`NO_ACTION`**.
3. Policy & Execution nodes are **bypassed**.
4. Node Inspector displays: `Decision: NO_ACTION`, `Recommended Strategy: None (NO_ACTION)`, `Rationale: Intervention evaluated and not economically justified.`
5. RECLAIM displays: **`SYSTEM STOPPED // CAPITAL PRESERVED: \$47.00`**.

---

*RECLAIM — Bounded Autonomous Decision Engine.*
