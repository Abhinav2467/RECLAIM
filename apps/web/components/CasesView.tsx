"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { MerchantRecoveryOverviewResponse, MerchantOverviewCaseItem } from "@/lib/types";
import { formatSyntheticCustomerName, formatCompactId } from "@/lib/formatters";

interface CasesViewProps {
  overview: MerchantRecoveryOverviewResponse | null;
  onSelectCase: (caseId: number) => void;
  onStartDemo: () => void;
  loading: boolean;
}

type StatusFilter = "ALL" | "AT_RISK" | "VERIFYING" | "RECOVERED" | "NO_ACTION" | "FAILED";
type SortOption = "NEWEST" | "AMOUNT_DESC" | "NEEDS_ATTENTION";

export function CasesView({
  overview,
  onSelectCase,
  onStartDemo,
  loading,
}: CasesViewProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("NEWEST");

  const counts = overview?.counts;
  const rawCases = overview?.cases || [];

  // Filter and Sort Logic
  const filteredCases = useMemo(() => {
    let result = [...rawCases];

    // 1. Status Filter
    if (statusFilter === "AT_RISK") {
      result = result.filter((c) =>
        ["DETECTED", "DIAGNOSED", "RECOMMENDATION_READY", "APPROVED", "EXECUTING", "VERIFYING"].includes(c.status)
      );
    } else if (statusFilter === "VERIFYING") {
      result = result.filter((c) => c.status === "VERIFYING");
    } else if (statusFilter === "RECOVERED") {
      result = result.filter((c) => c.status === "RECOVERED");
    } else if (statusFilter === "NO_ACTION") {
      result = result.filter((c) => c.status === "NO_ACTION");
    } else if (statusFilter === "FAILED") {
      result = result.filter((c) => ["FAILED", "ABORTED"].includes(c.status));
    }

    // 2. Search Query (customer, order, payment, case ID)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter((c) => {
        const caseIdStr = `#${c.case_id} ${c.case_id}`;
        const custName = (c.customer_display || formatSyntheticCustomerName(null, c.case_id)).toLowerCase();
        const orderId = (c.order_external_id || "").toLowerCase();
        const paymentId = (c.provider_payment_id || "").toLowerCase();
        const diag = (c.diagnosis || "").toLowerCase();
        return (
          caseIdStr.includes(q) ||
          custName.includes(q) ||
          orderId.includes(q) ||
          paymentId.includes(q) ||
          diag.includes(q)
        );
      });
    }

    // 3. Sorting
    result.sort((a, b) => {
      if (sortBy === "AMOUNT_DESC") {
        const amtA = parseFloat(a.current_at_risk_amount || a.recoverable_amount || "0");
        const amtB = parseFloat(b.current_at_risk_amount || b.recoverable_amount || "0");
        return amtB - amtA;
      }
      if (sortBy === "NEEDS_ATTENTION") {
        const priorityScore = (status: string) => {
          if (status === "VERIFYING") return 3;
          if (status === "FAILED") return 2;
          if (["DETECTED", "DIAGNOSED", "RECOMMENDATION_READY", "APPROVED", "EXECUTING"].includes(status)) return 1;
          return 0;
        };
        const scoreA = priorityScore(a.status);
        const scoreB = priorityScore(b.status);
        if (scoreA !== scoreB) return scoreB - scoreA;
        return b.case_id - a.case_id;
      }
      // Default: NEWEST (case_id desc)
      return b.case_id - a.case_id;
    });

    return result;
  }, [rawCases, statusFilter, searchQuery, sortBy]);

  return (
    <div className="space-y-8 animate-fade-in-up">
      {/* SECTION 1: HEADER & STATS */}
      <section className="space-y-6 border-b border-stone-200/80 pb-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-[10px] font-mono font-bold tracking-widest text-stone-500 uppercase">
              <span className="h-1.5 w-1.5 rounded-full bg-stone-900" />
              AUTHORITATIVE RECOVERY CASE EXPLORER
            </div>
            <h1 className="text-3xl sm:text-5xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Recovery Cases
            </h1>
            <p className="text-xs text-stone-600 font-sans max-w-xl leading-relaxed">
              Every monetary recovery decision, from initial detection through economic evaluation to verified resolution.
            </p>
          </div>

          {/* COUNTS BAR */}
          {counts && (
            <div className="flex items-center gap-3 text-xs font-mono text-stone-600 bg-white px-4 py-2.5 rounded-xl border border-stone-300/80 shadow-2xs flex-wrap">
              <span>TOTAL: <strong className="text-stone-900 font-bold">{counts.total_cases}</strong></span>
              <span className="text-stone-300">•</span>
              <span>ACTIVE: <strong className="text-amber-800 font-bold">{counts.active_cases}</strong></span>
              <span className="text-stone-300">•</span>
              <span>VERIFYING: <strong className="text-amber-900 font-bold">{counts.verifying_cases}</strong></span>
              <span className="text-stone-300">•</span>
              <span>RECOVERED: <strong className="text-emerald-800 font-bold">{counts.recovered_cases}</strong></span>
              <span className="text-stone-300">•</span>
              <span>NO ACTION: <strong className="text-stone-900 font-bold">{counts.no_action_cases}</strong></span>
            </div>
          )}
        </div>

        {/* CONTROLS STRIP: FILTERS, SEARCH, SORT */}
        <div className="bg-white rounded-2xl border border-stone-300/80 p-4 sm:p-5 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
          {/* STATUS FILTERS */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 text-xs font-sans">
            {[
              { id: "ALL", label: "All Cases" },
              { id: "AT_RISK", label: "At Risk" },
              { id: "VERIFYING", label: "Verifying" },
              { id: "RECOVERED", label: "Recovered" },
              { id: "NO_ACTION", label: "No Action" },
              { id: "FAILED", label: "Failed" },
            ].map((f) => {
              const active = statusFilter === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => setStatusFilter(f.id as StatusFilter)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition cursor-pointer ${
                    active
                      ? "bg-stone-900 text-white shadow-xs"
                      : "text-stone-600 hover:text-stone-900 hover:bg-stone-100/80"
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>

          {/* SEARCH & SORT */}
          <div className="flex items-center gap-3 flex-col sm:flex-row">
            <div className="relative w-full sm:w-64">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search customer, order, case ID..."
                className="w-full pl-3.5 pr-8 py-1.5 rounded-lg border border-stone-300 text-xs font-sans focus:outline-none focus:ring-2 focus:ring-stone-900 focus:border-stone-900 transition bg-stone-50/50"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1.5 text-xs text-stone-400 hover:text-stone-900 font-bold"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0 text-xs font-sans">
              <span className="text-stone-400 font-mono text-[10px] uppercase font-bold">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-3 py-1.5 rounded-lg border border-stone-300 text-xs font-sans font-semibold bg-white text-stone-800 focus:outline-none focus:ring-2 focus:ring-stone-900 transition cursor-pointer"
              >
                <option value="NEWEST">Newest First</option>
                <option value="AMOUNT_DESC">Highest Amount at Risk</option>
                <option value="NEEDS_ATTENTION">Needs Attention First</option>
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2: CASE REGISTER TABLE OR EMPTY STATE */}
      <section className="space-y-4">
        <div className="flex items-center justify-between text-xs font-sans text-stone-500 px-1">
          <span>
            Showing <strong className="text-stone-900 font-bold">{filteredCases.length}</strong> of{" "}
            <strong className="text-stone-900 font-bold">{rawCases.length}</strong> cases
          </span>
        </div>

        {rawCases.length === 0 ? (
          <div className="rounded-2xl border border-stone-300/80 bg-white p-12 sm:p-16 text-center space-y-5 shadow-xl">
            <div className="max-w-md mx-auto space-y-3">
              <span className="inline-block px-3 py-1 rounded bg-stone-100 font-mono text-[10px] font-bold text-stone-600 uppercase tracking-widest border border-stone-200">
                NO RECOVERY CASES
              </span>
              <h3 className="text-2xl font-serif-editorial font-bold text-stone-900">
                Operational Ledger Empty
              </h3>
              <p className="text-xs text-stone-600 font-sans leading-relaxed">
                No recovery decisions have been recorded yet for your merchant identity. Initialize a synthetic recovery scenario to trigger decision logic.
              </p>
            </div>
            <button
              onClick={onStartDemo}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-stone-900 px-6 py-3 text-xs font-sans font-bold text-white shadow-md hover:bg-rose-700 transition cursor-pointer disabled:opacity-50"
            >
              {loading ? "Executing Engine..." : "Run Demo Recovery Scenario"}
            </button>
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="rounded-2xl border border-stone-300/80 bg-white p-12 text-center space-y-3 shadow-md">
            <h3 className="text-lg font-serif-editorial font-bold text-stone-900">
              No cases match criteria
            </h3>
            <p className="text-xs text-stone-500 font-sans">
              Try adjusting your search query or status filters.
            </p>
            <button
              onClick={() => {
                setStatusFilter("ALL");
                setSearchQuery("");
              }}
              className="text-xs font-sans font-bold text-rose-700 hover:underline cursor-pointer pt-2 inline-block"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="rounded-2xl border border-stone-300/80 bg-white overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-sans border-collapse min-w-[750px]">
                <thead>
                  <tr className="border-b border-stone-200/80 text-stone-500 bg-stone-50/80 font-mono text-[10px] font-bold uppercase tracking-widest">
                    <th className="py-4 px-6">Case</th>
                    <th className="py-4 px-6">Customer / Order</th>
                    <th className="py-4 px-6">Money at Risk</th>
                    <th className="py-4 px-6">Diagnosis</th>
                    <th className="py-4 px-6">Recommended Action</th>
                    <th className="py-4 px-6">Status</th>
                    <th className="py-4 px-6 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {filteredCases.map((c) => {
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
                        {/* CASE ID */}
                        <td className="py-4 px-6 font-mono font-bold text-stone-900 text-sm">
                          #{c.case_id}
                        </td>

                        {/* CUSTOMER & ORDER */}
                        <td className="py-4 px-6 font-sans">
                          <div className="font-bold text-stone-900 text-sm group-hover:text-rose-700 transition-colors">
                            {customerName}
                          </div>
                          <div className="text-[11px] text-stone-400 font-mono mt-0.5">{orderCompact}</div>
                        </td>

                        {/* MONEY AT RISK */}
                        <td className="py-4 px-6 font-mono">
                          <div className="font-black text-stone-900 text-base">
                            ${parseFloat(c.current_at_risk_amount).toFixed(2)}
                          </div>
                          {isRec && (
                            <div className="text-[10px] text-emerald-800 font-sans font-bold mt-0.5">
                              Verified Rec: ${parseFloat(c.recoverable_amount).toFixed(2)}
                            </div>
                          )}
                          {isNoAct && (
                            <div className="text-[10px] text-stone-500 font-sans font-medium mt-0.5">
                              Preserved: ${parseFloat(c.recoverable_amount).toFixed(2)}
                            </div>
                          )}
                        </td>

                        {/* DIAGNOSIS */}
                        <td className="py-4 px-6 font-mono text-stone-800 text-[11px]">
                          {c.diagnosis || "—"}
                        </td>

                        {/* RECOMMENDED ACTION */}
                        <td className="py-4 px-6 font-mono text-stone-700 font-bold">
                          {c.recommended_action || (isNoAct ? "NO_ACTION" : "—")}
                        </td>

                        {/* STATUS */}
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

                        {/* ROW ACTION AFFORDANCE */}
                        <td className="py-4 px-6 text-right">
                          <div className="flex items-center justify-end gap-3" onClick={(e) => e.stopPropagation()}>
                            <Link
                              href={`/engine?case_id=${c.case_id}&replay=true`}
                              className="text-xs font-mono font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-2.5 py-1 rounded transition"
                            >
                              Engine ⚡
                            </Link>
                            <button
                              onClick={() => onSelectCase(c.case_id)}
                              className="text-xs font-sans font-bold text-stone-600 hover:text-stone-900 group-hover:text-rose-700 transition-colors flex items-center gap-1 cursor-pointer"
                            >
                              Inspect →
                            </button>
                          </div>
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
    </div>
  );
}
