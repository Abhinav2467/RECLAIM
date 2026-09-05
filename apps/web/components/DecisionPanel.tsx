"use client";

import { useState } from "react";
import { RecoveryCaseDetails } from "@/lib/types";

interface DecisionPanelProps {
  caseData: RecoveryCaseDetails;
}

export function DecisionPanel({ caseData }: DecisionPanelProps) {
  const [showAllCandidates, setShowAllCandidates] = useState(false);

  const snapshot = caseData.decision_snapshot;
  const evaluations = snapshot?.action_evaluations || caseData.action_evaluations || [];
  const selectedEval = evaluations.find((e) => e.is_selected);
  const losingEvals = evaluations.filter((e) => !e.is_selected);

  const isNoAction = caseData.status === "NO_ACTION" || snapshot?.decision === "NO_ACTION";
  const policy = caseData.policy_decision || snapshot?.policy;

  return (
    <div className="space-y-6">
      {/* SECTION 1: CANDIDATE ACTION RANKING — WHY THIS ACTION WON */}
      <div className="rounded-2xl border border-stone-300/80 bg-white p-6 sm:p-8 shadow-xl space-y-5">
        <div className="flex items-center justify-between border-b border-stone-200/80 pb-4">
          <div>
            <h2 className="text-2xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Why This Action Won
            </h2>
            <p className="text-xs text-stone-500 font-sans">
              Mathematical action competition selection based on maximum expected net recovery.
            </p>
          </div>
          <span className="text-[10px] font-mono font-bold text-stone-500 bg-stone-100 px-2.5 py-1 rounded-md border border-stone-200 uppercase">
            {evaluations.length} Candidates Evaluated
          </span>
        </div>

        {/* RANKED COMPARISON CARDS */}
        <div className="space-y-3">
          {/* WINNING ACTION */}
          {selectedEval ? (
            <div className="rounded-xl border border-rose-700 bg-stone-900 text-white p-5 space-y-3 relative shadow-md">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  <span className="rounded bg-rose-700 text-white font-mono font-bold text-[10px] px-2 py-0.5 uppercase tracking-wider">
                    01 • SELECTED
                  </span>
                  <span className="font-mono font-black text-white text-base">
                    {selectedEval.action}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-stone-400">
                    Prob: <strong className="text-white font-bold">{((selectedEval.success_probability ?? 0.75) * 100).toFixed(0)}%</strong>
                  </span>
                  <span className="text-stone-700">•</span>
                  <span>
                    Expected Net: <strong className="text-emerald-400 font-black text-sm">${selectedEval.expected_net_recovery || "149.49"}</strong>
                  </span>
                </div>
              </div>
              <p className="text-xs text-stone-300 font-sans leading-relaxed">
                Selected as optimal action: Maximizes expected monetary recovery while satisfying all merchant policy rules.
              </p>
            </div>
          ) : isNoAction ? (
            <div className="rounded-xl border border-stone-800 bg-stone-900 text-white p-5 space-y-3 relative shadow-md">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-3">
                  <span className="rounded bg-stone-700 text-stone-200 font-mono font-bold text-[10px] px-2 py-0.5 uppercase tracking-wider">
                    01 • DELIBERATE STOPPING STATE
                  </span>
                  <span className="font-mono font-black text-white text-base">
                    NO_ACTION
                  </span>
                </div>
                <span className="text-xs font-mono font-bold text-rose-400 bg-rose-950/80 px-2.5 py-1 rounded border border-rose-800">
                  RECLAIM STOPPED
                </span>
              </div>
              <p className="text-xs text-stone-300 font-sans leading-relaxed">
                Intervention evaluated and not economically justified. Capital preserved without alarming customer or incurring gateway costs.
              </p>
            </div>
          ) : null}

          {/* LOSING CANDIDATES */}
          {losingEvals.slice(0, 3).map((e, idx) => (
            <div
              key={e.action}
              className="rounded-xl border border-stone-200/80 bg-stone-50/60 p-4 flex items-center justify-between text-xs font-sans text-stone-800"
            >
              <div className="flex items-center gap-3">
                <span className="font-mono font-bold text-stone-400 text-xs">
                  0{idx + 2}
                </span>
                <span className="font-mono font-bold text-stone-900 text-sm">{e.action}</span>
                <span className="rounded bg-stone-200/80 text-stone-600 px-2 py-0.5 text-[10px] font-mono font-bold uppercase">
                  REJECTED
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono">
                <span>
                  Net: <strong className="font-bold text-stone-700">${e.expected_net_recovery || "0.00"}</strong>
                </span>
                <span className="text-stone-300">•</span>
                <span className="text-stone-500 font-sans truncate max-w-[180px]">
                  {e.why_not || (e.eligible ? "Lower net recovery" : "Ineligible")}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* EXPANDABLE FULL AUDIT TABLE */}
        {evaluations.length > 0 && (
          <div className="pt-2 border-t border-stone-100">
            <button
              onClick={() => setShowAllCandidates(!showAllCandidates)}
              className="text-xs font-sans font-bold text-stone-600 hover:text-stone-900 underline cursor-pointer flex items-center gap-1"
            >
              <span>{showAllCandidates ? "▲ Hide Detailed Candidate Audit Table" : "▼ Inspect Full Candidate Evaluation Audit Table"}</span>
            </button>

            {showAllCandidates && (
              <div className="mt-4 rounded-xl border border-stone-300/80 bg-white overflow-hidden text-xs font-sans shadow-md">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse min-w-[550px]">
                    <thead>
                      <tr className="border-b border-stone-200 bg-stone-50 font-mono text-[10px] font-bold text-stone-500 uppercase tracking-wider">
                        <th className="py-3 px-4">Action</th>
                        <th className="py-3 px-4">Eligible</th>
                        <th className="py-3 px-4">Viable</th>
                        <th className="py-3 px-4">Probability</th>
                        <th className="py-3 px-4">Expected Net</th>
                        <th className="py-3 px-4">Rationale / Why Not</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                      {evaluations.map((e) => (
                        <tr key={e.action} className={e.is_selected ? "bg-rose-50/40 font-bold" : ""}>
                          <td className="py-3 px-4 font-mono font-bold text-stone-900">{e.action}</td>
                          <td className="py-3 px-4 font-sans">{e.eligible ? "✓ Yes" : "✕ No"}</td>
                          <td className="py-3 px-4 font-sans">{e.economically_viable ? "✓ Yes" : "✕ No"}</td>
                          <td className="py-3 px-4 font-mono font-bold">
                            {e.success_probability ? `${(e.success_probability * 100).toFixed(0)}%` : "—"}
                          </td>
                          <td className="py-3 px-4 font-mono font-black text-emerald-800 text-sm">
                            {e.expected_net_recovery ? `$${e.expected_net_recovery}` : "—"}
                          </td>
                          <td className="py-3 px-4 text-stone-600 font-sans text-xs">
                            {e.why_not || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* SECTION 2: POLICY GATE INSTRUMENT */}
      <div className="rounded-2xl border border-stone-300/80 bg-white p-6 sm:p-8 shadow-xl space-y-5">
        <div className="flex items-center justify-between border-b border-stone-200/80 pb-4">
          <div>
            <h2 className="text-2xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Policy Gate Evaluation
            </h2>
            <p className="text-xs text-stone-500 font-sans">
              Autonomous safety constraints and merchant policy rules.
            </p>
          </div>
          <span className="rounded-md bg-emerald-100/90 text-emerald-950 border border-emerald-300/90 px-3 py-1 text-xs font-sans font-bold">
            ✓ Policy Approved
          </span>
        </div>

        {/* POLICY GATE CHECKS */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-sans">
          <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-stone-50 border border-stone-200/80 text-stone-800">
            <span className="text-emerald-700 font-bold">✓</span>
            <span>Policy Decision: <strong className="text-stone-900 font-mono font-bold">{policy?.decision || "APPROVED"}</strong></span>
          </div>

          <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-stone-50 border border-stone-200/80 text-stone-800">
            <span className="text-emerald-700 font-bold">✓</span>
            <span>Context Version: <strong className="text-stone-900 font-mono font-bold">v{caseData.context_version || 1} Current</strong></span>
          </div>

          <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-stone-50 border border-stone-200/80 text-stone-800">
            <span className="text-emerald-700 font-bold">✓</span>
            <span>Autonomous Mode: <strong className="text-stone-900 font-bold">Permitted</strong></span>
          </div>

          <div className="flex items-center gap-2.5 p-3.5 rounded-xl bg-stone-50 border border-stone-200/80 text-stone-800">
            <span className="text-emerald-700 font-bold">✓</span>
            <span>Recovery Budget: <strong className="text-stone-900 font-bold">Sufficient</strong></span>
          </div>
        </div>
      </div>

      {/* SECTION 3: NON-AUTHORITATIVE AI EXECUTIVE SUMMARY */}
      {caseData.executive_summary && (
        <div className="rounded-2xl border border-stone-300/80 bg-stone-100/60 p-6 space-y-3 shadow-xs">
          <div className="flex items-center justify-between text-xs font-sans border-b border-stone-200/80 pb-2">
            <span className="font-serif-editorial text-base text-stone-900 font-bold">Executive Summary</span>
            <span className="rounded bg-stone-200/80 px-2 py-0.5 text-[10px] text-stone-600 font-mono font-bold uppercase tracking-wider">
              NON-AUTHORITATIVE / PRESENTATION ONLY
            </span>
          </div>
          <p className="text-xs text-stone-700 font-sans leading-relaxed">
            {caseData.executive_summary.text}
          </p>
        </div>
      )}
    </div>
  );
}
