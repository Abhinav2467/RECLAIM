"use client";

import Link from "next/link";

export function NarrativeProblemSection() {
  return (
    <section id="problem" className="py-16 sm:py-24 border-b border-stone-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          <div className="lg:col-span-5 space-y-4">
            <span className="text-xs font-mono font-bold tracking-widest text-rose-700 uppercase">
              01 // REVENUE IS SLIPPING
            </span>
            <h2 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900 leading-tight">
              Payment loss rarely arrives as one clean, obvious failure.
            </h2>
            <p className="text-stone-600 text-base leading-relaxed">
              Card expiration, authorization staleness, temporary gateway timeouts, and checkout friction cause payments to silent slip. Traditional recovery systems fire blind retries that incur heavy transaction fees, damage customer trust, or fail entirely.
            </p>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-xl border border-stone-300/80 shadow-xs space-y-3">
              <div className="text-xs font-mono font-bold text-rose-700">01 STALE AUTHORIZATION</div>
              <h4 className="text-base font-sans font-bold text-stone-900">Expired Holds</h4>
              <p className="text-xs text-stone-500 leading-relaxed">
                Card authorizations left uncaptured past 7 days expire silently. Blind captures fail with authorization errors.
              </p>
            </div>

            <div className="bg-white p-6 rounded-xl border border-stone-300/80 shadow-xs space-y-3">
              <div className="text-xs font-mono font-bold text-rose-700">02 GATEWAY TIMEOUT</div>
              <h4 className="text-base font-sans font-bold text-stone-900">Payment Failure</h4>
              <p className="text-xs text-stone-500 leading-relaxed">
                Bank network glitches reject valid customer charges. Indiscriminate retries cause chargebacks and fees.
              </p>
            </div>

            <div className="bg-white p-6 rounded-xl border border-stone-300/80 shadow-xs space-y-3">
              <div className="text-xs font-mono font-bold text-rose-700">03 CHECKOUT DROP</div>
              <h4 className="text-base font-sans font-bold text-stone-900">Checkout Abandonment</h4>
              <p className="text-xs text-stone-500 leading-relaxed">
                Orders created with authorized intent left uncompleted. Recovery must weigh outreach cost against customer lifetime value.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function NarrativeQuestionSection() {
  return (
    <section className="py-16 sm:py-24 bg-stone-900 text-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
        <div className="max-w-3xl space-y-4">
          <span className="text-xs font-mono font-bold tracking-widest text-rose-400 uppercase">
            02 // THE FUNDAMENTAL QUESTION
          </span>
          <h2 className="text-3xl sm:text-5xl font-serif-editorial font-bold leading-tight">
            The Dunning Paradox
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-stone-800/80 p-8 rounded-2xl border border-stone-700 space-y-4">
            <span className="text-xs font-mono font-bold text-stone-400 uppercase">TRADITIONAL DUNNING ASK:</span>
            <h3 className="text-2xl font-sans font-bold text-stone-200">“Can we recover this payment?”</h3>
            <p className="text-stone-400 text-sm leading-relaxed">
              Every recoverable payment is aggressively retried, regardless of manual review cost, customer friction, or probability. Often spends $50 in support effort to chase a $15 payment.
            </p>
          </div>

          <div className="bg-stone-800/80 p-8 rounded-2xl border border-rose-900/60 space-y-4 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 rounded-full blur-2xl" />
            <span className="text-xs font-mono font-bold text-rose-400 uppercase">RECLAIM ASKS:</span>
            <h3 className="text-2xl font-sans font-bold text-white">“Is it worth recovering?”</h3>
            <p className="text-stone-300 text-sm leading-relaxed">
              RECLAIM evaluates expected net recovery before taking action. If intervention costs exceed expected gross return, RECLAIM stops intentionally — preserving merchant capital.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function NarrativeEngineSection() {
  const steps = [
    { num: "01", name: "DETECT", desc: "Monitors payment events & webhooks for revenue at risk." },
    { num: "02", name: "DIAGNOSE", desc: "Determines root failure reason with confidence scores." },
    { num: "03", name: "ESTIMATE", desc: "Computes success probabilities for candidate actions." },
    { num: "04", name: "COMPARE", desc: "Ranks candidate interventions by expected net recovery." },
    { num: "05", name: "DECIDE", desc: "Selects optimal action or triggers NO_ACTION." },
    { num: "06", name: "POLICY", desc: "Enforces merchant policy gates & autonomous limits." },
    { num: "07", name: "EXECUTE", desc: "Dispatches idempotent bounded provider actions." },
    { num: "08", name: "VERIFY", desc: "Reconciles provider state & confirms financial truth." },
  ];

  return (
    <section id="how-it-works" className="py-16 sm:py-24 border-b border-stone-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
        <div className="max-w-3xl space-y-3">
          <span className="text-xs font-mono font-bold tracking-widest text-stone-500 uppercase">
            03 // THE 8-STAGE ENGINE
          </span>
          <h2 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900">
            The Decision Pipeline Spine
          </h2>
          <p className="text-stone-600 text-base">
            Every payment at risk travels through an 8-stage deterministic decision pipeline.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {steps.map((st) => (
            <div key={st.num} className="bg-white p-5 rounded-xl border border-stone-300/80 shadow-2xs space-y-2 hover:border-stone-400 transition-colors">
              <span className="text-xs font-mono font-bold text-rose-700">{st.num}</span>
              <h4 className="text-sm font-sans font-bold text-stone-900">{st.name}</h4>
              <p className="text-xs text-stone-500 leading-relaxed">{st.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function ActionCompetitionSection() {
  return (
    <section className="py-16 sm:py-24 border-b border-stone-200 bg-stone-50/50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
        <div className="max-w-3xl space-y-3">
          <span className="text-xs font-mono font-bold tracking-widest text-stone-500 uppercase">
            05 // ECONOMIC COMPETITION
          </span>
          <h2 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900">
            Why This Action Won
          </h2>
          <p className="text-stone-600 text-base">
            Instead of executing fixed hardcoded scripts, RECLAIM evaluates competing actions and selects the candidate with the highest expected net return.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-stone-300/80 p-6 sm:p-8 shadow-md space-y-4">
          <div className="text-xs font-mono font-bold text-stone-500 uppercase border-b border-stone-200 pb-3 flex justify-between">
            <span>CANDIDATE INTERVENTIONS RANKING</span>
            <span>CASE #1081 ($199.99 AT RISK)</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            {/* Rank 1 - Winner */}
            <div className="p-4 rounded-xl border border-emerald-300 bg-emerald-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="px-2 py-1 rounded bg-emerald-600 text-white font-bold text-[10px]">RANK 1 // SELECTED</span>
                <div>
                  <div className="font-bold text-stone-900 text-sm">attempt_capture_retry</div>
                  <div className="text-[11px] text-stone-600 font-sans">Probability: 75.0% | Intervention Fee: -$0.50</div>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-stone-500 block">EXPECTED NET RECOVERY</span>
                <span className="text-emerald-800 font-black text-lg">$149.49</span>
              </div>
            </div>

            {/* Rank 2 - Rejected */}
            <div className="p-4 rounded-xl border border-stone-200 bg-stone-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4 opacity-75">
              <div className="flex items-center gap-3">
                <span className="px-2 py-1 rounded bg-stone-300 text-stone-800 font-bold text-[10px]">RANK 2 // REJECTED</span>
                <div>
                  <div className="font-bold text-stone-700 text-sm">manual_review</div>
                  <div className="text-[11px] text-stone-500 font-sans">Probability: 80.0% | Support Operator Cost: -$104.99</div>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-stone-400 block">EXPECTED NET RECOVERY</span>
                <span className="text-stone-700 font-bold text-base">$55.00</span>
              </div>
            </div>

            {/* Rank 3 - Rejected */}
            <div className="p-4 rounded-xl border border-stone-200 bg-stone-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4 opacity-75">
              <div className="flex items-center gap-3">
                <span className="px-2 py-1 rounded bg-stone-300 text-stone-800 font-bold text-[10px]">RANK 3 // REJECTED</span>
                <div>
                  <div className="font-bold text-stone-700 text-sm">collect_more_evidence</div>
                  <div className="text-[11px] text-stone-500 font-sans">Probability: 60.0% | Outreach Overhead: -$69.99</div>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-stone-400 block">EXPECTED NET RECOVERY</span>
                <span className="text-stone-700 font-bold text-base">$50.00</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function StoppingRuleSection() {
  return (
    <section className="py-16 sm:py-24 border-b border-stone-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-4">
            <span className="text-xs font-mono font-bold tracking-widest text-rose-700 uppercase">
              06 // THE STOPPING RULE
            </span>
            <h2 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900 leading-tight">
              Knowing when NOT to act is RECLAIM’s strongest differentiator.
            </h2>
            <p className="text-stone-600 text-base leading-relaxed">
              When a payment is technically recoverable but intervention costs exceed expected gross return, RECLAIM intentionally stops. Capital is preserved rather than spent chasing unviable recovery.
            </p>
          </div>

          <div className="lg:col-span-6 bg-stone-900 text-white rounded-2xl p-6 sm:p-8 space-y-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-stone-800 pb-3">
              <span className="text-xs font-mono font-bold text-stone-400">UNJUSTIFIED CASE EVALUATION</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40 uppercase">
                NO_ACTION EXECUTED
              </span>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex justify-between">
                <span className="text-stone-400">Revenue at Risk:</span>
                <span className="text-stone-200 font-bold">$45.00</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-400">Success Probability:</span>
                <span className="text-stone-200 font-bold">10.0%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-stone-400">Intervention Cost:</span>
                <span className="text-rose-400 font-bold">-$50.00</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-stone-800">
                <span className="text-stone-300 font-bold">Expected Net Recovery:</span>
                <span className="text-rose-400 font-extrabold text-sm">-$45.50</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-stone-800 border border-stone-700 text-xs font-mono text-stone-300">
              <span className="text-rose-400 font-bold block mb-1">CAPITAL PRESERVED // $45.00</span>
              RECLAIM evaluated intervention costs against expected net return and intentionally halted execution. Zero support hours wasted.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function VerificationSection() {
  return (
    <section className="py-16 sm:py-24 border-b border-stone-200 bg-stone-50/50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
        <div className="max-w-3xl space-y-3">
          <span className="text-xs font-mono font-bold tracking-widest text-emerald-800 uppercase">
            07 // VERIFIED OUTCOME
          </span>
          <h2 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900">
            Execution is Not Recovery. Verification Is.
          </h2>
          <p className="text-stone-600 text-base">
            RECLAIM does not mark a case as recovered merely because an API request was sent. Financial state transitions are authoritatively verified against gateway reconciliation.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 font-mono">
          <div className="bg-white p-6 rounded-xl border border-stone-300/80 space-y-2">
            <span className="text-[10px] text-stone-400 font-bold">STAGE 1</span>
            <div className="text-base font-bold text-stone-900">EXECUTING</div>
            <p className="text-xs text-stone-500 font-sans leading-relaxed">
              Idempotent payment capture request dispatched to Razorpay adapter.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-amber-300 bg-amber-50/30 space-y-2">
            <span className="text-[10px] text-amber-700 font-bold">STAGE 2</span>
            <div className="text-base font-bold text-amber-900">VERIFYING</div>
            <p className="text-xs text-stone-600 font-sans leading-relaxed">
              Real-time SSE stream waits for webhook reconciliation event from payment provider.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-emerald-400 bg-emerald-50/50 space-y-2">
            <span className="text-[10px] text-emerald-700 font-bold">STAGE 3</span>
            <div className="text-base font-bold text-emerald-900">$0.00 AT RISK // RECOVERED</div>
            <p className="text-xs text-emerald-800 font-sans leading-relaxed">
              Provider state confirmed captured. Exposure transitions from $199.99 to $0.00.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export function EngineeringCredibilitySection() {
  const capabilities = [
    { title: "PostgreSQL Schema", detail: "Alembic migrations 0001–0006 with partial unique indexes on active cases." },
    { title: "LangGraph Pipeline", detail: "Orchestrated multi-step decision state machine with context versioning." },
    { title: "Webhook Verification", detail: "HMAC-SHA256 signature verification & deduplication on raw webhook payloads." },
    { title: "Bounded Autonomy", detail: "Policy gate rules restricting actions based on merchant risk limits." },
    { title: "Forensic Audit Trail", detail: "Immutable event ledger tracking every state change, actor, and rationale." },
    { title: "Real-Time SSE", detail: "Server-Sent Events stream with client disconnect handling & cursor resume." },
  ];

  return (
    <section id="engineering" className="py-16 sm:py-24 border-b border-stone-200">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
        <div className="max-w-3xl space-y-3">
          <span className="text-xs font-mono font-bold tracking-widest text-stone-500 uppercase">
            08 // ENGINEERING CREDIBILITY
          </span>
          <h2 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900">
            Architected for Financial Systems
          </h2>
          <p className="text-stone-600 text-base">
            No fake claims. Only capabilities fully backed by the repository implementation.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {capabilities.map((c) => (
            <div key={c.title} className="bg-white p-6 rounded-xl border border-stone-300/80 shadow-2xs space-y-2">
              <h4 className="text-base font-sans font-bold text-stone-900">{c.title}</h4>
              <p className="text-xs text-stone-500 font-mono leading-relaxed">{c.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function DifferentiationSection() {
  return (
    <section id="differentiation" className="py-16 sm:py-24 border-b border-stone-200 bg-stone-50/50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
        <div className="max-w-3xl space-y-3">
          <span className="text-xs font-mono font-bold tracking-widest text-stone-500 uppercase">
            09 // DIFFERENTIATION
          </span>
          <h2 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900">
            RECLAIM vs Traditional Dunning
          </h2>
        </div>

        <div className="bg-white rounded-2xl border border-stone-300/80 overflow-hidden shadow-md">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-sans">
              <thead className="bg-stone-900 text-white font-mono uppercase text-[11px]">
                <tr>
                  <th className="p-4">CAPABILITY</th>
                  <th className="p-4">TRADITIONAL DUNNING</th>
                  <th className="p-4 text-rose-400">RECLAIM DECISION ENGINE</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200">
                <tr>
                  <td className="p-4 font-bold text-stone-900">Decision Logic</td>
                  <td className="p-4 text-stone-500">Blind scheduled retries</td>
                  <td className="p-4 font-semibold text-stone-900">Economic action competition</td>
                </tr>
                <tr>
                  <td className="p-4 font-bold text-stone-900">Stopping Rule</td>
                  <td className="p-4 text-stone-500">Chases every payment until limit</td>
                  <td className="p-4 font-semibold text-rose-700">Intentionally triggers NO_ACTION if net &le; 0</td>
                </tr>
                <tr>
                  <td className="p-4 font-bold text-stone-900">Revenue Truth</td>
                  <td className="p-4 text-stone-500">Assumes retry success</td>
                  <td className="p-4 font-semibold text-stone-900">Reconciled provider webhook state</td>
                </tr>
                <tr>
                  <td className="p-4 font-bold text-stone-900">Auditability</td>
                  <td className="p-4 text-stone-500">Basic error logs</td>
                  <td className="p-4 font-semibold text-stone-900">Forensic audit timeline with decision snapshot</td>
                </tr>
                <tr>
                  <td className="p-4 font-bold text-stone-900">Autonomy</td>
                  <td className="p-4 text-stone-500">Unbounded retry loops</td>
                  <td className="p-4 font-semibold text-stone-900">Bounded autonomy policy gates</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}

export function EnginePreviewSection() {
  return (
    <section id="how-it-works" className="py-20 sm:py-28 bg-stone-900 text-white border-b border-stone-800">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
        <div className="max-w-3xl space-y-4">
          <span className="text-xs font-mono font-bold tracking-widest text-rose-400 uppercase">
            THE MACHINE BEHIND THE DECISION
          </span>
          <h2 className="text-3xl sm:text-5xl font-serif-editorial font-bold text-white tracking-tight">
            Watch the Recovery System Operating Live.
          </h2>
          <p className="text-stone-400 text-base leading-relaxed">
            RECLAIM isn't a passive dashboard. It's a live financial decision engine that evaluates competing actions, applies policy gates, executes bounded interventions, and verifies money.
          </p>
        </div>

        {/* System Pipeline Node Map Visual */}
        <div className="bg-stone-950 rounded-2xl border border-stone-800 p-6 sm:p-8 space-y-8 shadow-2xl">
          <div className="grid grid-cols-2 sm:grid-cols-5 lg:grid-cols-10 gap-3">
            {[
              { num: "01", name: "Event Gate" },
              { num: "02", name: "Revenue Truth" },
              { num: "03", name: "Diagnosis" },
              { num: "04", name: "Action Arena" },
              { num: "05", name: "Economic Gate" },
              { num: "06", name: "Decision" },
              { num: "07", name: "Policy Gate" },
              { num: "08", name: "Execution" },
              { num: "09", name: "Verification" },
              { num: "10", name: "Outcome" },
            ].map((node, i) => (
              <div
                key={i}
                className="bg-stone-900 border border-stone-800 rounded-xl p-3 space-y-2 flex flex-col justify-between h-24"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold text-rose-400 bg-rose-950/80 px-1.5 py-0.5 rounded border border-rose-900">
                    {node.num}
                  </span>
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                </div>
                <div className="font-mono text-xs font-bold text-stone-200 leading-tight">
                  {node.name}
                </div>
              </div>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-stone-800/80">
            <div className="text-xs font-mono text-stone-400 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              Interactive node inspection, economic action competition & decision replay enabled.
            </div>
            <Link
              href="/signup"
              className="px-6 py-2.5 bg-white text-stone-900 font-mono text-xs font-bold rounded-lg hover:bg-stone-200 transition shadow-md"
            >
              LAUNCH ENGINE DEMO →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

export function FinalCTASection() {
  return (
    <section className="py-20 sm:py-28 bg-stone-900 text-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 text-center space-y-8">
        <div className="max-w-2xl mx-auto space-y-4">
          <span className="text-xs font-mono font-bold tracking-widest text-rose-400 uppercase">
            10 // ENTER RECLAIM
          </span>
          <h2 className="text-4xl sm:text-5xl font-serif-editorial font-bold leading-tight">
            Revenue should be recovered. Not chased.
          </h2>
          <p className="text-stone-400 text-base leading-relaxed">
            Operate merchant revenue recovery with mathematical economic clarity.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/signup"
            className="w-full sm:w-auto px-8 py-3.5 text-sm font-semibold text-stone-900 bg-white hover:bg-stone-100 rounded-lg shadow-lg transition"
          >
            ENTER RECLAIM
          </Link>
          <a
            href="#how-it-works"
            className="w-full sm:w-auto px-8 py-3.5 text-sm font-semibold text-stone-300 hover:text-white bg-stone-800 hover:bg-stone-700/80 rounded-lg border border-stone-700 transition"
          >
            VIEW HOW IT WORKS
          </a>
        </div>
      </div>
    </section>
  );
}
