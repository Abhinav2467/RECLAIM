# System Architecture & Technical Design

> **RECLAIM Architecture**: Event-Driven Revenue Reconciliation & Bounded Autonomous Decision Engine

---

## 1. System Overview & Component Responsibilities

RECLAIM is structured into decoupled domain layers ([`apps/api/app/domain`](../apps/api/app/domain)) and API services ([`apps/api/app/api`](../apps/api/app/api)).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER (Next.js 16)                    │
│   Operations Console  │  Authoritative Explorer  │  Visual Decision Engine  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │ HTTP / SSE
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                           API & INGESTION LAYER                             │
│   Auth Routes (/api/auth)  │  Webhooks Gate (/api/webhooks/razorpay)        │
│   Overview Read Model      │  Showcase Batch Runner (/api/demo/batch)       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                      REVENUE TRUTH & RECONCILIATION                         │
│   Raw Body Verification   │  Event Deduplication  │  Revenue Truth Engine   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                    BOUNDED AUTONOMOUS DECISION ENGINE                       │
│   Diagnosis Engine  │  Action Arena Competition  │  Net Economic Calculator │
│   LangGraph Agent   │  Policy Safety Gate       │  Execution Manager       │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                         PERSISTENCE & RECONCILIATION                        │
│   PostgreSQL Schema (SQLAlchemy 2.0)  │  Immutable Forensic Audit Ledger    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Inventory & Code References:
* **Secure Event Gate** ([`apps/api/app/api/webhooks.py`](../apps/api/app/api/webhooks.py)): Captures raw HTTP request body streams to verify Razorpay HMAC SHA256 signatures before JSON deserialization.
* **Event Reconciler** ([`apps/api/app/events/reconciler.py`](../apps/api/app/events/reconciler.py)): Reconciles out-of-order webhook events and enforces active case uniqueness per payment.
* **Revenue Truth Engine** ([`apps/api/app/domain/revenue_truth.py`](../apps/api/app/domain/revenue_truth.py)): Computes expected order intent, captured funds, and recoverable exposure.
* **Diagnosis Engine** ([`apps/api/app/domain/diagnosis.py`](../apps/api/app/domain/diagnosis.py)): Classifies contextual failures (`AUTHORIZATION_STALE`, `GATEWAY_TIMEOUT`, `CHECKOUT_ABANDONED`).
* **Action Arena & Candidates** ([`apps/api/app/domain/actions.py`](../apps/api/app/domain/actions.py)): Evaluates candidate strategies side-by-side.
* **Economic Engine** ([`apps/api/app/domain/economics.py`](../apps/api/app/domain/economics.py)): Computes Expected Net Recovery ($\text{Net} = A_{\text{recoverable}} \times P - C$).
* **Decision Agent** ([`apps/api/app/agents/decision_agent.py`](../apps/api/app/agents/decision_agent.py)): LangGraph state machine driving decision strategy selection.
* **Policy Engine** ([`apps/api/app/domain/policy.py`](../apps/api/app/domain/policy.py)): Validates decision safety against context freshness and budget caps.
* **Execution Manager** ([`apps/api/app/domain/execution.py`](../apps/api/app/domain/execution.py)): Dispatches provider interventions while maintaining `EXECUTED` state.
* **Verification Engine** ([`apps/api/app/domain/verification.py`](../apps/api/app/domain/verification.py)): Authoritatively confirms payment settlement before transitioning to `RECOVERED`.

---

## 2. Webhook Ingestion & Recovery Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Gateway as Razorpay / Webhook Sender
    participant Gate as Event Gate (API)
    participant DB as PostgreSQL DB
    participant Truth as Revenue Truth Engine
    participant Agent as LangGraph Decision Agent
    participant Policy as Policy Gate
    participant Exec as Execution Manager
    participant SSE as SSE Stream / Frontend

    Gateway->>Gate: POST /api/webhooks/razorpay (Signed Header + Body)
    Gate->>Gate: Verify HMAC SHA256 Signature (Raw Body)
    Gate->>DB: Store Raw Event & Check Deduplication (provider_event_id)
    
    alt Duplicate Event
        Gate-->>Gateway: HTTP 200 (Ignored Duplicate)
    else New Event
        Gate->>Truth: Reconcile Payment & Order State
        Truth->>DB: Update Payment & Order Records
        Truth->>Agent: Run Recovery Pipeline(payment_id)
        
        Agent->>Agent: 1. Diagnose Failure Context
        Agent->>Agent: 2. Evaluate Candidate Interventions
        Agent->>Agent: 3. Calculate Expected Net Recovery
        
        alt Net Recovery <= \$0.00
            Agent->>DB: Record NO_ACTION (Capital Preserved)
            Agent->>SSE: Emit Event (Case Status = NO_ACTION)
        else Net Recovery > \$0.00
            Agent->>Policy: Evaluate Policy Bounds
            alt Policy Approved
                Policy->>Exec: Dispatch Bounded Intervention
                Exec->>Gateway: Execute Capture Retry / Outreach
                Exec->>DB: Transition Status = EXECUTING / VERIFYING
                Exec->>SSE: Emit Event (Status = VERIFYING)
            else Policy Violation
                Policy->>DB: Transition Status = NEEDS_REVIEW
            end
        end
        Gate-->>Gateway: HTTP 200 ACK
    end
```

---

## 3. Database Entity-Relationship Model

```mermaid
erDiagram
    MERCHANTS ||--o{ USERS : owns
    MERCHANTS ||--o{ CUSTOMERS : tracks
    MERCHANTS ||--o{ ORDERS : receives
    MERCHANTS ||--o{ PAYMENTS : processes
    MERCHANTS ||--o{ RECOVERY_CASES : manages

    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--o{ PAYMENTS : generates
    PAYMENTS ||--o{ RECOVERY_CASES : triggers

    RECOVERY_CASES ||--o{ CASE_AUDIT_EVENTS : logs

    MERCHANTS {
        bigint id PK
        string name
        jsonb metadata_json
        timestamp created_at
    }

    USERS {
        bigint id PK
        bigint merchant_id FK
        string email
        string password_hash
        timestamp created_at
    }

    ORDERS {
        bigint id PK
        bigint merchant_id FK
        bigint customer_id FK
        string external_id
        numeric amount_total
        string currency
        string status
    }

    PAYMENTS {
        bigint id PK
        bigint merchant_id FK
        bigint order_id FK
        string provider_payment_id
        numeric amount
        string status
        string provider_state
        string provider_failure_code
    }

    RECOVERY_CASES {
        bigint id PK
        bigint merchant_id FK
        bigint payment_id FK
        bigint order_id FK
        string status
        string diagnosis
        numeric recoverable_amount
        numeric current_at_risk_amount
        string recommended_action
        string decision_rationale
        integer version
    }

    CASE_AUDIT_EVENTS {
        bigint id PK
        bigint case_id FK
        string event_type
        string actor
        string message
        timestamp occurred_at
    }
```

---

## 4. Lifecycle State Machine Transitions

```mermaid
stateDiagram-v2
    [*] --> DETECTED: Anomaly Event Received
    DETECTED --> CONTEXT_BUILDING: Load Revenue Provenance
    CONTEXT_BUILDING --> DIAGNOSED: Classify Failure
    DIAGNOSED --> ECONOMICALLY_EVALUATED: Action Arena & Net Calc

    ECONOMICALLY_EVALUATED --> NO_ACTION: Net <= \$0.00 (Capital Preserved)
    ECONOMICALLY_EVALUATED --> RECOMMENDATION_READY: Net > \$0.00

    RECOMMENDATION_READY --> APPROVED: Policy Gate Passed
    RECOMMENDATION_READY --> NEEDS_REVIEW: Policy Cap Exceeded

    APPROVED --> EXECUTING: Bounded Action Dispatched
    EXECUTING --> VERIFYING: Executed != Recovered

    VERIFYING --> RECOVERED: Gateway Confirms Capture
    VERIFYING --> FAILED: Gateway Rejection / Timeout

    NO_ACTION --> [*]
    RECOVERED --> [*]
    FAILED --> [*]
```

---

## 5. System Consistency Principles

1. **Active Case Uniqueness**: A payment can have at most one active (non-terminal) recovery case. Concurrency checks lock rows using `FOR UPDATE` or DB unique partial indexes on active states (`VERIFYING`, `EXECUTING`, `APPROVED`).
2. **Optimistic Concurrency Control**: `RecoveryCase` rows include an integer `version` field. Policy evaluations verify that `context_version` matches the case version before execution dispatch.
3. **Immutable Forensic Audit Ledger**: Every decision phase, policy check, state transition, and provider response appends an immutable record to `case_audit_events`.
4. **Merchant Scoping Isolation**: Every API endpoint filters queries strictly by `merchant_id` extracted from the authenticated user's session cookie.

---

## 6. Security Boundaries

* **Webhook Authentication**: Razorpay signature header `X-Razorpay-Signature` checked against HMAC SHA256 digest of raw request bytes.
* **User Authentication**: HTTP-only `reclaim_session` cookie containing encrypted, signed session metadata. Passwords hashed using bcrypt.
* **Zero Secret Exposure**: Tokens and API keys are never rendered in JSON responses or frontend state.

---

*RECLAIM — System Architecture & Technical Design Document.*
