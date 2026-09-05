"use client";

import Link from "next/link";
import { MerchantRecoveryOverviewResponse, MerchantOverviewCaseItem } from "@/lib/types";
import { formatSyntheticCustomerName, formatCompactId } from "@/lib/formatters";

interface OperationsViewProps {
  overview: MerchantRecoveryOverviewResponse | null;
  onSelectCase: (caseId: number) => void;
  onStartDemo: () => void;
  loading: boolean;
}

export function OperationsView({
  overview,
  onSelectCase,
  onStartDemo,
  loading,
}: OperationsViewProps) {
  const aggregates = overview?.aggregates;
  const counts = overview?.counts;
  const cases = overview?.cases || [];

  const revAtRisk = aggregates?.revenue_at_risk || "0.00";
  const expRecovery = aggregates?.expected_recovery || "0.00";
  const recAmount = aggregates?.recovered_amount || "0.00";
  const capPreserved = aggregates?.capital_preserved || "0.00";
  const currency = aggregates?.currency || "USD";

  const hasRecovered = parseFloat(recAmount) > 0;
  const hasPreserved = parseFloat(capPreserved) > 0;

  // Filter cases that need operational attention (VERIFYING, FAILED, or active)
  const attentionCases = cases.filter((c) =>
    ["VERIFYING", "FAILED", "ABORTED", "DETECTED", "DIAGNOSED", "RECOMMENDATION_READY", "APPROVED", "EXECUTING"].includes(c.status)
  );

  // Top 5 recent cases
  const recentCases = cases.slice(0, 5);

  return (
    <div className="space-y-10 animate-fade-in-up">
      {/* SECTION 1: HEADER & FINANCIAL POSITION */}
      <section className="space-y-6 border-b border-stone-200/80 pb-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-[10px] font-mono font-bold tracking-widest text-stone-500 uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-700" />
              EXECUTIVE REVENUE CONTROL ROOM
            </div>
            <h1 className="text-3xl sm:text-5xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Revenue Recovery Operations
            </h1>
            <p className="text-xs text-stone-600 font-sans max-w-xl leading-relaxed">
              Autonomous monetary evaluation, policy-constrained intervention, and authoritative financial verification for merchant transactions.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/cases"
              className="px-4 py-2 text-xs font-sans font-bold text-stone-800 bg-white hover:bg-stone-100 rounded-lg border border-stone-300 shadow-2xs transition"
            >
              Explore Cases Explorer →
            </Link>
          </div>
        </div>

        {/* A. FINANCIAL POSITION (EDITORIAL FINANCIAL STATEMENT) */}
        <div className="bg-white rounded-2xl border border-stone-300/80 p-6 sm:p-8 shadow-xl space-y-6">
          <div className="text-[10px] font-mono font-bold text-stone-400 uppercase tracking-widest border-b border-stone-200 pb-3">
            FINANCIAL POSITION STATEMENT
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* 1. REVENUE AT RISK */}
            <div className="space-y-2 border-l-2 border-rose-700 pl-4">
              <span className="text-xs font-sans font-bold text-stone-500 uppercase tracking-wider block">
                Revenue at Risk
              </span>
              <div className="text-3xl sm:text-4xl font-mono font-black text-stone-900 tracking-tight">
                ${parseFloat(revAtRisk).toFixed(2)}{" "}
                <span className="text-xs font-sans font-medium text-stone-400">{currency}</span>
              </div>
              <p className="text-[11px] text-stone-500 font-sans">Current unrecovered exposure</p>
            </div>

            {/* 2. EXPECTED NET RECOVERY */}
            <div className="space-y-2 border-l-2 border-stone-400 pl-4">
              <span className="text-xs font-sans font-bold text-stone-500 uppercase tracking-wider block">
                Expected Net Recovery
              </span>
              <div className="text-3xl sm:text-4xl font-mono font-black text-stone-800 tracking-tight">
                ${parseFloat(expRecovery).toFixed(2)}{" "}
                <span className="text-xs font-sans font-medium text-stone-400">{currency}</span>
              </div>
              <p className="text-[11px] text-stone-500 font-sans">Decision-time net estimate</p>
            </div>

            {/* 3. VERIFIED RECOVERED */}
            <div
              className={`space-y-2 border-l-2 pl-4 transition ${
                hasRecovered ? "border-emerald-600 bg-emerald-50/50 p-3.5 rounded-r-xl" : "border-stone-400"
              }`}
            >
              <span
                className={`text-xs font-sans font-bold uppercase tracking-wider block ${
                  hasRecovered ? "text-emerald-950" : "text-stone-500"
                }`}
              >
                Verified Recovered
              </span>
              <div
                className={`text-3xl sm:text-4xl font-mono font-black tracking-tight ${
                  hasRecovered ? "text-emerald-800" : "text-stone-400"
                }`}
              >
                ${parseFloat(recAmount).toFixed(2)}{" "}
                <span className="text-xs font-sans font-medium text-stone-400">{currency}</span>
              </div>
              <p className={`text-[11px] font-sans ${hasRecovered ? "text-emerald-900 font-semibold" : "text-stone-500"}`}>
                {hasRecovered ? "✓ Authoritatively verified" : "Verified financial recovery"}
              </p>
            </div>

            {/* 4. CAPITAL PRESERVED */}
            <div
              className={`space-y-2 border-l-2 pl-4 transition ${
                hasPreserved ? "border-stone-900 bg-stone-100/80 p-3.5 rounded-r-xl" : "border-stone-400"
              }`}
            >
              <span
                className={`text-xs font-sans font-bold uppercase tracking-wider block ${
                  hasPreserved ? "text-stone-900" : "text-stone-500"
                }`}
              >
                Capital Preserved
              </span>
              <div
                className={`text-3xl sm:text-4xl font-mono font-black tracking-tight ${
                  hasPreserved ? "text-stone-900" : "text-stone-400"
                }`}
              >
                ${parseFloat(capPreserved).toFixed(2)}{" "}
                <span className="text-xs font-sans font-medium text-stone-400">{currency}</span>
              </div>
              <p className="text-[11px] text-stone-500 font-sans">
                {hasPreserved ? "Deliberate non-intervention" : "Non-intervention decisions"}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2: DECISION MIX & RECOVERY OUTCOMES (2-COLUMN GRID) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* B. DECISION MIX (7 COLS) */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-stone-300/80 p-6 sm:p-8 shadow-xl space-y-5 flex flex-col justify-between">
          <div className="space-y-1">
            <span className="text-[10px] font-mono font-bold text-stone-400 uppercase tracking-widest block">
              DECISION MIX COUNTS
            </span>
            <h2 className="text-2xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Operational Case Mix
            </h2>
            <p className="text-xs text-stone-500 font-sans">
              Authoritative population distribution across decision and resolution states.
            </p>
          </div>

          {counts ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
              <div className="bg-stone-50 p-3.5 rounded-xl border border-stone-200/80">
                <span className="text-[10px] font-mono text-stone-400 font-bold uppercase block">TOTAL CASES</span>
                <div className="text-2xl font-mono font-black text-stone-900 mt-1">{counts.total_cases}</div>
              </div>
              <div className="bg-amber-50/60 p-3.5 rounded-xl border border-amber-200/80">
                <span className="text-[10px] font-mono text-amber-800 font-bold uppercase block">VERIFYING</span>
                <div className="text-2xl font-mono font-black text-amber-900 mt-1">{counts.verifying_cases}</div>
              </div>
              <div className="bg-emerald-50/60 p-3.5 rounded-xl border border-emerald-200/80">
                <span className="text-[10px] font-mono text-emerald-800 font-bold uppercase block">RECOVERED</span>
                <div className="text-2xl font-mono font-black text-emerald-900 mt-1">{counts.recovered_cases}</div>
              </div>
              <div className="bg-stone-100 p-3.5 rounded-xl border border-stone-300/80">
                <span className="text-[10px] font-mono text-stone-700 font-bold uppercase block">NO ACTION</span>
                <div className="text-2xl font-mono font-black text-stone-900 mt-1">{counts.no_action_cases}</div>
              </div>
              <div className="bg-rose-50/60 p-3.5 rounded-xl border border-rose-200/80">
                <span className="text-[10px] font-mono text-rose-700 font-bold uppercase block">FAILED</span>
                <div className="text-2xl font-mono font-black text-rose-900 mt-1">{counts.failed_cases}</div>
              </div>
              <div className="bg-stone-50 p-3.5 rounded-xl border border-stone-200/80">
                <span className="text-[10px] font-mono text-stone-500 font-bold uppercase block">ACTIVE</span>
                <div className="text-2xl font-mono font-black text-stone-800 mt-1">{counts.active_cases}</div>
              </div>
            </div>
          ) : (
            <div className="text-xs font-mono text-stone-400">Loading decision mix...</div>
          )}
        </div>

        {/* D. RECOVERY OUTCOMES (5 COLS) */}
        <div className="lg:col-span-5 bg-stone-900 text-white rounded-2xl border border-stone-800 p-6 sm:p-8 shadow-xl space-y-5 flex flex-col justify-between">
          <div className="space-y-1">
            <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-widest block">
              AUTHORITATIVE RECOVERY OUTCOMES
            </span>
            <h2 className="text-2xl font-serif-editorial font-bold text-white tracking-tight">
              Outcome Summary
            </h2>
            <p className="text-xs text-stone-400 font-sans">
              Measured financial recovery vs deliberate capital preservation.
            </p>
          </div>

          <div className="space-y-3.5 pt-1">
            <div className="bg-stone-950 p-4 rounded-xl border border-stone-800 flex items-center justify-between text-xs font-sans">
              <div>
                <span className="font-mono font-bold text-emerald-400 block text-xs">
                  {counts?.recovered_cases || 0} Recovered Case{(counts?.recovered_cases || 0) === 1 ? "" : "s"}
                </span>
                <span className="text-stone-400 text-[11px]">Authoritatively verified</span>
              </div>
              <div className="text-right font-mono font-black text-emerald-400 text-lg">
                ${parseFloat(recAmount).toFixed(2)}
              </div>
            </div>

            <div className="bg-stone-950 p-4 rounded-xl border border-stone-800 flex items-center justify-between text-xs font-sans">
              <div>
                <span className="font-mono font-bold text-stone-300 block text-xs">
                  {counts?.no_action_cases || 0} Deliberate NO_ACTION
                </span>
                <span className="text-stone-400 text-[11px]">Merchant capital preserved</span>
              </div>
              <div className="text-right font-mono font-black text-stone-200 text-lg">
                ${parseFloat(capPreserved).toFixed(2)}
              </div>
            </div>

            <div className="bg-stone-950 p-4 rounded-xl border border-stone-800 flex items-center justify-between text-xs font-sans">
              <div>
                <span className="font-mono font-bold text-amber-400 block text-xs">
                  {counts?.verifying_cases || 0} Currently Verifying
                </span>
                <span className="text-stone-400 text-[11px]">Active gateway reconciliation</span>
              </div>
              <div className="text-right font-mono font-black text-amber-400 text-lg">
                ${parseFloat(revAtRisk).toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 3: C. NEEDS ATTENTION QUEUE */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-stone-200/80 pb-3">
          <div>
            <h2 className="text-2xl font-serif-editorial font-bold text-stone-900 tracking-tight flex items-center gap-2">
              <span>Needs Attention</span>
              {attentionCases.length > 0 && (
                <span className="rounded-full bg-rose-100 text-rose-800 text-xs font-mono font-bold px-2.5 py-0.5 border border-rose-200">
                  {attentionCases.length}
                </span>
              )}
            </h2>
            <p className="text-xs text-stone-500 font-sans">
              Unresolved recovery cases requiring operational monitoring or active verification.
            </p>
          </div>
        </div>

        {attentionCases.length === 0 ? (
          <div className="rounded-2xl border border-stone-300/80 bg-white p-8 text-center space-y-2 shadow-sm">
            <span className="font-mono font-bold text-xs text-stone-400 uppercase tracking-widest block">
              NO ACTIVE INTERVENTIONS
            </span>
            <p className="text-xs text-stone-600 font-sans">
              All evaluated cases are authoritatively reconciled (`RECOVERED`) or gracefully stopped (`NO_ACTION`).
            </p>
          </div>
        ) : (
          <div className="rounded-2xl border border-stone-300/80 bg-white overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-sans border-collapse min-w-[650px]">
                <thead>
                  <tr className="border-b border-stone-200/80 text-stone-500 bg-stone-50/80 font-mono text-[10px] font-bold uppercase tracking-widest">
                    <th className="py-3.5 px-6">Case</th>
                    <th className="py-3.5 px-6">Customer / Order</th>
                    <th className="py-3.5 px-6">Money at Risk</th>
                    <th className="py-3.5 px-6">Diagnosis</th>
                    <th className="py-3.5 px-6">Status</th>
                    <th className="py-3.5 px-6 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {attentionCases.map((c) => {
                    const isVerifying = c.status === "VERIFYING";
                    const isFailed = c.status === "FAILED" || c.status === "ABORTED";

                    const customerName = formatSyntheticCustomerName(c.customer_display, c.case_id);
                    const orderCompact = formatCompactId(c.order_external_id, "ORD");

                    return (
                      <tr
                        key={c.case_id}
                        onClick={() => onSelectCase(c.case_id)}
                        className="hover:bg-stone-50/90 transition-colors cursor-pointer group"
                      >
                        <td className="py-3.5 px-6 font-mono font-bold text-stone-900 text-sm">
                          #{c.case_id}
                        </td>
                        <td className="py-3.5 px-6 font-sans">
                          <div className="font-bold text-stone-900 text-sm group-hover:text-rose-700 transition-colors">
                            {customerName}
                          </div>
                          <div className="text-[11px] text-stone-400 font-mono mt-0.5">{orderCompact}</div>
                        </td>
                        <td className="py-3.5 px-6 font-mono font-black text-stone-900 text-base">
                          ${parseFloat(c.current_at_risk_amount || c.recoverable_amount).toFixed(2)}
                        </td>
                        <td className="py-3.5 px-6 font-mono text-stone-800 text-[11px]">
                          {c.diagnosis || "—"}
                        </td>
                        <td className="py-3.5 px-6">
                          <span
                            className={`rounded-md px-2.5 py-1 text-[11px] font-sans font-bold inline-flex items-center gap-1.5 ${
                              isVerifying
                                ? "bg-amber-100/90 text-amber-950 border border-amber-300/90"
                                : isFailed
                                ? "bg-rose-100/90 text-rose-950 border border-rose-300/90"
                                : "bg-stone-100 text-stone-800 border border-stone-300/80"
                            }`}
                          >
                            {isVerifying && <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />}
                            {c.status}
                          </span>
                        </td>
                        <td className="py-3.5 px-6 text-right">
                          <span className="text-xs font-sans font-bold text-rose-700 group-hover:underline flex items-center justify-end gap-1">
                            Inspect →
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* SECTION 4: E. RECENT CASES (LIMITED SUBSET 5 CASES MAX) */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-stone-200/80 pb-3">
          <div>
            <h2 className="text-2xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Recent Recovery Decisions
            </h2>
            <p className="text-xs text-stone-500 font-sans">
              Latest 5 recovery decisions. Use Cases Explorer for full search and filtering.
            </p>
          </div>

          <Link
            href="/cases"
            className="text-xs font-sans font-bold text-rose-700 hover:text-rose-900 hover:underline flex items-center gap-1 cursor-pointer"
          >
            VIEW ALL CASES →
          </Link>
        </div>

        {cases.length === 0 ? (
          <div className="rounded-2xl border border-stone-300/80 bg-white p-8 text-center space-y-3 shadow-sm">
            <p className="text-xs text-stone-600 font-sans">
              No recent recovery cases exist yet. Trigger a demo scenario below to run decision logic.
            </p>
            <button
              onClick={onStartDemo}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-stone-900 px-5 py-2 text-xs font-sans font-bold text-white shadow-md hover:bg-rose-700 transition cursor-pointer disabled:opacity-50"
            >
              {loading ? "Executing..." : "Run Demo Scenario"}
            </button>
          </div>
        ) : (
          <div className="rounded-2xl border border-stone-300/80 bg-white overflow-hidden shadow-xl space-y-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-sans border-collapse min-w-[650px]">
                <thead>
                  <tr className="border-b border-stone-200/80 text-stone-500 bg-stone-50/80 font-mono text-[10px] font-bold uppercase tracking-widest">
                    <th className="py-4 px-6">Case</th>
                    <th className="py-4 px-6">Customer / Order</th>
                    <th className="py-4 px-6">Money at Risk</th>
                    <th className="py-4 px-6">Diagnosis</th>
                    <th className="py-4 px-6">Status</th>
                    <th className="py-4 px-6 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {recentCases.map((c) => {
                    const isRec = c.status === "RECOVERED";
                    const isNoAct = c.status === "NO_ACTION";
                    const isVerifying = c.status === "VERIFYING";

                    const customerName = formatSyntheticCustomerName(c.customer_display, c.case_id);
                    const orderCompact = formatCompactId(c.order_external_id, "ORD");

                    return (
                      <tr
                        key={c.case_id}
                        onClick={() => onSelectCase(c.case_id)}
                        className="hover:bg-stone-50/90 transition-colors cursor-pointer group"
                      >
                        <td className="py-4 px-6 font-mono font-bold text-stone-900 text-sm">
                          #{c.case_id}
                        </td>
                        <td className="py-4 px-6 font-sans">
                          <div className="font-bold text-stone-900 text-sm group-hover:text-rose-700 transition-colors">
                            {customerName}
                          </div>
                          <div className="text-[11px] text-stone-400 font-mono mt-0.5">{orderCompact}</div>
                        </td>
                        <td className="py-4 px-6 font-mono">
                          <div className="font-black text-stone-900 text-base">
                            ${parseFloat(c.current_at_risk_amount).toFixed(2)}
                          </div>
                        </td>
                        <td className="py-4 px-6 font-mono text-stone-800 text-[11px]">
                          {c.diagnosis || "—"}
                        </td>
                        <td className="py-4 px-6">
                          <span
                            className={`rounded-md px-2.5 py-1 text-[11px] font-sans font-bold inline-flex items-center gap-1.5 ${
                              isRec
                                ? "bg-emerald-100/80 text-emerald-950 border border-emerald-300/80"
                                : isVerifying
                                ? "bg-amber-100/80 text-amber-950 border border-amber-300/80"
                                : isNoAct
                                ? "bg-stone-900 text-white"
                                : "bg-stone-100 text-stone-800 border border-stone-300/80"
                            }`}
                          >
                            {isRec && <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />}
                            {isVerifying && <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />}
                            {c.status}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <span className="text-xs font-sans font-bold text-stone-500 group-hover:text-rose-700 transition-colors flex items-center justify-end gap-1">
                            Inspect →
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="p-4 bg-stone-50/80 border-t border-stone-200/80 text-center">
              <Link
                href="/cases"
                className="text-xs font-sans font-bold text-rose-700 hover:text-rose-900 hover:underline cursor-pointer"
              >
                VIEW ALL CASES ({cases.length} Total) →
              </Link>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
