# Limitations & Production Evolution Roadmap

> **RECLAIM Honest Disclosure**: Implemented Prototype Capabilities vs. Scaled Production Architecture

---

## 1. Implemented Capabilities vs. Production Boundaries

RECLAIM clearly distinguishes what is **implemented and verified today** versus future production scale architecture:

```
IMPLEMENTED TODAY (VERIFIED PROTOTYPE)       PRODUCTION EVOLUTION (SCALE ARCHITECTURE)
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│ • LangGraph State Orchestration      │ ──► │ • Multi-Agent Policy Competition     │
│ • Deterministic Probabilities (v1)   │ ──► │ • Gradient Boosted ML Models (v2)    │
│ • Net Recovery Formula Calculator    │ ──► │ • Counterfactual LTV Baselines       │
│ • Bounded Policy Safety Gates        │ ──► │ • Multi-Gateway FX Rate Hedging      │
│ • Webhook HMAC SHA256 Verification   │ ──► │ • Distributed Celery / Redis Queues │
│ • Dual-State Reconciliation Engine   │ ──► │ • Production Razorpay Live Credentials│
│ • Visual Decision Machine & Replay   │ ──► │ • Distributed Rate Limit Breakers    │
└──────────────────────────────────────┘     └──────────────────────────────────────┘
```

---

## 2. Known Limitations & Technical Caveats

1. **Deterministic Probability Model v1**:
   * *Current State*: Success probabilities $P(\text{success} \mid \text{context}, a)$ use deterministic contextual heuristics ([`apps/api/app/domain/probability.py`](../apps/api/app/domain/probability.py)) to ensure 100% auditability and zero decision hallucination.
   * *Production Evolution*: v2 will train gradient-boosted decision trees (XGBoost/LightGBM) on historical gateway settlement datasets.

2. **Synchronous Request Processing**:
   * *Current State*: Webhook ingestion and recovery pipeline evaluation run synchronously within FastAPI request tasks.
   * *Production Evolution*: High-volume production deployments will offload webhook processing to Celery workers backed by Redis/RabbitMQ.

3. **Single Merchant Currency Aggregates**:
   * *Current State*: Portfolio aggregates render in the merchant's base currency without real-time multi-currency FX rate conversions.
   * *Production Evolution*: Production releases will integrate live forex conversion APIs.

---

## 3. Production Evolution Roadmap

### **Phase 1: Asynchronous Event Distribution (Scale)**
* Implement Redis stream buffers for webhook ingestion.
* Offload retry execution and customer outreach dispatch to Celery background workers.

### **Phase 2: Learned Probability & Counterfactual Engine (Intelligence)**
* Replace deterministic heuristics with a trained machine learning probability model estimating $P(\text{success} \mid \text{customer\_segment}, \text{failure\_type}, \text{action})$.
* Evaluate counterfactual baselines to estimate net incremental recovery lift over merchant default retry policies.

### **Phase 3: Multi-Gateway Adapter & Live Razorpay Credentials (Integration)**
* Connect live production Razorpay API keys (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`).
* Expand gateway adapters to support Stripe, Adyen, and PayPal settlement reconciliation APIs.

---

*RECLAIM — Limitations & Production Evolution Roadmap.*
