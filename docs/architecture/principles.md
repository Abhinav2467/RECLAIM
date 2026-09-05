# Architecture Principles

1. PostgreSQL is the source of truth for internal financial state.
2. Provider payloads are retained and normalized into internal domain events.
3. Webhook processing is lightweight: verify, persist, deduplicate, enqueue/process.
4. Payment state is reconciled before any recovery action.
5. Financial arithmetic is deterministic.
6. Recovery probability is action-specific: P(success | context, action).
7. The LLM may recommend from a constrained action set; it never gets direct financial authority.
8. Policy validation is deterministic and occurs immediately before execution.
9. State-changing actions are idempotent.
10. An action being accepted by an API is not equivalent to revenue being recovered; verification is required.
