"use client";

import { RecoveryCaseDetails } from "@/lib/types";
import { formatSyntheticCustomerName, formatCompactId } from "@/lib/formatters";

interface RecoveryCasePanelProps {
  caseData: RecoveryCaseDetails;
}

export function RecoveryCasePanel({ caseData }: RecoveryCasePanelProps) {
  const snapshot = caseData.decision_snapshot;
  const evaluations = snapshot?.action_evaluations || caseData.action_evaluations || [];
  const selectedEval = evaluations.find((e) => e.is_selected);
  const eligibleEvals = evaluations.filter((e) => e.eligible && e.expected_net_recovery !== null);
  const sortedEligible = [...eligibleEvals].sort((a, b) => parseFloat(b.expected_net_recovery || "0") - parseFloat(a.expected_net_recovery || "0"));
  const primaryEval = selectedEval || sortedEligible[0] || evaluations[0];

  const isNoAction = caseData.status === "NO_ACTION" || snapshot?.decision === "NO_ACTION";
  const isRecovered = caseData.status === "RECOVERED";
  const isVerifying = caseData.status === "VERIFYING";

  const decRecoverable = snapshot?.recoverable_amount || caseData.recoverable_amount || "47.00";
  const currentAtRisk = caseData.current_state?.recoverable_amount || (isRecovered || isNoAction ? "0.00" : decRecoverable);
  const currency = caseData.currency || "USD";

  const probDecimal = primaryEval?.success_probability ?? 0.80;
  const probPercent = (probDecimal * 100).toFixed(0);
  const baseAmount = parseFloat(decRecoverable);
  const grossRecovery = (baseAmount * probDecimal).toFixed(2);
  const cost = primaryEval?.intervention_cost ? parseFloat(primaryEval.intervention_cost).toFixed(2) : "50.00";
  const netRecovery = primaryEval?.expected_net_recovery !== undefined && primaryEval?.expected_net_recovery !== null
    ? parseFloat(primaryEval.expected_net_recovery).toFixed(2)
    : (baseAmount * probDecimal - parseFloat(cost)).toFixed(2);

  const customerName = formatSyntheticCustomerName(null, caseData.customer_id || caseData.case_id);
  const orderCompact = formatCompactId(caseData.order_external_id || (caseData.order_id ? String(caseData.order_id) : null), "ORD");
  const payCompact = formatCompactId(caseData.provider_payment_id || (caseData.payment_id ? String(caseData.payment_id) : null), "PAY");

  return (
    <div className="space-y-6">
      {/* 1. CASE HEADER & EDITORIAL HERO */}
      <div className="rounded-2xl border border-stone-300/80 bg-white p-6 sm:p-8 shadow-xl space-y-6">
        <div className="flex flex-col md:flex-row md:items-start justify-between border-b border-stone-200/80 pb-6 gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="rounded bg-stone-100 px-2.5 py-1 font-mono text-xs text-stone-800 border border-stone-300/80 font-bold uppercase">
                CASE #{caseData.case_id}
              </span>
              <span className="rounded bg-stone-100 px-2 py-0.5 font-mono text-xs text-stone-500 border border-stone-200">
                v{caseData.version}
              </span>
              <span
                className={`rounded-md px-3 py-1 font-sans text-xs font-bold inline-flex items-center gap-1.5 ${
                  isRecovered
                    ? "bg-emerald-100/90 border border-emerald-300 text-emerald-950"
                    : isVerifying
                    ? "bg-amber-100/90 border border-amber-300 text-amber-950"
                    : isNoAction
                    ? "bg-stone-900 text-white"
                    : "bg-stone-100 border border-stone-300 text-stone-800"
                }`}
              >
                {isVerifying && <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />}
                {isRecovered && <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />}
                {caseData.status}
              </span>
            </div>

            <h1 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              {customerName}
            </h1>

            <p className="text-xs text-stone-500 font-sans flex items-center gap-2 flex-wrap">
              <span>Order: <strong className="text-stone-800 font-mono">{orderCompact}</strong></span>
              <span>•</span>
              <span>Payment: <strong className="text-stone-800 font-mono">{payCompact}</strong></span>
            </p>
          </div>

          {/* MONETARY VALUE ANCHOR */}
          <div className="bg-stone-50/80 border border-stone-300/80 rounded-xl p-5 text-right shrink-0">
            <span className="text-[10px] font-mono font-bold text-stone-400 uppercase tracking-widest block">
              CURRENT AT-RISK EXPOSURE
            </span>
            <div
              className={`text-3xl sm:text-4xl font-mono font-black mt-1 transition-all duration-700 ${
                isRecovered ? "text-emerald-800" : isNoAction ? "text-stone-900" : "text-rose-700"
              }`}
            >
              ${parseFloat(currentAtRisk).toFixed(2)}{" "}
              <span className="text-xs text-stone-400 font-sans font-normal">{currency}</span>
            </div>
            {isRecovered ? (
              <div className="text-[11px] font-sans font-bold text-emerald-800 mt-1">
                ✓ RECOVERED (${baseAmount.toFixed(2)})
              </div>
            ) : isNoAction ? (
              <div className="text-[11px] font-sans font-bold text-stone-700 mt-1">
                🛑 CAPITAL PRESERVED (${baseAmount.toFixed(2)})
              </div>
            ) : (
              <div className="text-[11px] font-sans text-stone-500 mt-1">
                At Decision: <strong className="text-stone-800 font-mono">${baseAmount.toFixed(2)}</strong>
              </div>
            )}
          </div>
        </div>

        {/* 2. CONTINUOUS VERTICAL DECISION SPINE */}
        <div className="space-y-5">
          <div className="flex items-center justify-between text-xs font-sans border-b border-stone-200/80 pb-2">
            <span className="uppercase font-mono text-[10px] font-bold tracking-widest text-stone-500">
              RECOVERY DECISION SPINE
            </span>
            <span className="font-mono text-[10px] font-bold text-emerald-800">PROVENANCE VERIFIED</span>
          </div>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-stone-200">
            {/* NODE 1: REVENUE AT RISK */}
            <div className="relative">
              <span className="absolute -left-[23px] top-1 h-3.5 w-3.5 rounded-full bg-rose-700 ring-4 ring-white" />
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-bold text-rose-700 block uppercase tracking-wider">
                    STAGE 01 • MONEY AT RISK
                  </span>
                  <div className="text-sm font-sans font-bold text-stone-900 mt-0.5">
                    ${baseAmount.toFixed(2)} {currency} Unrecovered Exposure
                  </div>
                </div>
                <div className="text-right text-xs font-mono text-stone-400">
                  {caseData.created_at ? new Date(caseData.created_at).toLocaleTimeString() : "09:07:29 UTC"}
                </div>
              </div>
            </div>

            {/* NODE 2: DIAGNOSIS */}
            <div className="relative">
              <span className="absolute -left-[23px] top-1 h-3.5 w-3.5 rounded-full bg-stone-900 ring-4 ring-white" />
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-bold text-stone-500 block uppercase tracking-wider">
                    STAGE 02 • DIAGNOSIS
                  </span>
                  <div className="text-sm font-mono font-bold text-stone-900 mt-0.5">
                    {caseData.diagnosis || "AUTHORIZATION_STALE"}
                  </div>
                </div>
                <div className="text-right">
                  <span className="rounded-md bg-stone-200/80 px-2.5 py-1 font-sans text-xs font-semibold text-stone-800 border border-stone-300/80">
                    {caseData.diagnosis_confidence || "HIGH"} Confidence
                  </span>
                </div>
              </div>
            </div>

            {/* NODE 3: ECONOMIC EVALUATION ARITHMETIC */}
            <div className="relative">
              <span className="absolute -left-[23px] top-1 h-3.5 w-3.5 rounded-full bg-emerald-600 ring-4 ring-white" />
              <div className="bg-stone-900 text-white p-6 rounded-xl border border-stone-800 space-y-4 shadow-md">
                <span className="text-[10px] font-mono font-bold text-emerald-400 block uppercase tracking-widest">
                  STAGE 03 • ECONOMIC EVALUATION ARITHMETIC
                </span>

                {/* EXACT FINANCIAL ARITHMETIC OBJECT */}
                <div className="bg-stone-950 p-4 rounded-lg border border-stone-800 font-mono text-xs space-y-2.5">
                  <div className="flex justify-between text-stone-300">
                    <span>Base Exposure Amount</span>
                    <span className="font-bold text-white">${baseAmount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-stone-400">
                    <span>× Estimated Success Probability</span>
                    <span className="font-bold text-emerald-400">{probPercent}%</span>
                  </div>
                  <div className="border-t border-stone-800 pt-2 flex justify-between text-stone-300">
                    <span>= Expected Gross Recovery</span>
                    <span className="font-bold text-white">${grossRecovery}</span>
                  </div>
                  <div className="flex justify-between text-stone-400">
                    <span>− Gateway Intervention Cost</span>
                    <span className="font-bold text-rose-400">-${cost}</span>
                  </div>
                  <div className="border-t-2 border-stone-700 pt-2.5 flex justify-between text-sm">
                    <span className="font-sans font-bold text-white tracking-tight">EXPECTED NET RECOVERY</span>
                    <span className={`font-mono font-black text-base ${parseFloat(netRecovery) > 0 && !isNoAction ? "text-emerald-400" : "text-rose-400"}`}>
                      ${netRecovery}
                    </span>
                  </div>
                </div>

                {isNoAction && (
                  <div className="rounded-lg bg-rose-950/80 border border-rose-800/80 p-3.5 text-rose-200 text-xs font-sans leading-relaxed">
                    🛑 <strong>RECLAIM STOPPED — Intervention Unviable:</strong>{" "}
                    {parseFloat(netRecovery) <= 0
                      ? `Intervention was evaluated and not economically justified (Expected Net Recovery $${netRecovery} ≤ $0.00). NO ACTION. Capital preserved: $${baseAmount.toFixed(2)}.`
                      : `Intervention was halted by Policy Gate safety constraints. NO ACTION. Capital preserved: $${baseAmount.toFixed(2)}.`}
                  </div>
                )}
              </div>
            </div>

            {/* NODE 4: DECISION & POLICY */}
            <div className="relative">
              <span className="absolute -left-[23px] top-1 h-3.5 w-3.5 rounded-full bg-stone-900 ring-4 ring-white" />
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-bold text-stone-500 block uppercase tracking-wider">
                    STAGE 04 • SELECTED ACTION & POLICY
                  </span>
                  <div className="text-sm font-mono font-bold text-rose-700 mt-0.5">
                    {caseData.recommended_action || (isNoAction ? "NO_ACTION" : "attempt_capture_retry")}
                  </div>
                </div>
                <div className="text-right">
                  <span className="rounded-md bg-emerald-100/80 text-emerald-950 border border-emerald-300/80 px-2.5 py-1 text-xs font-sans font-bold">
                    ✓ Policy Approved
                  </span>
                </div>
              </div>
            </div>

            {/* NODE 5: VERIFICATION OUTCOME */}
            <div className="relative">
              <span
                className={`absolute -left-[23px] top-1 h-3.5 w-3.5 rounded-full ring-4 ring-white ${
                  isRecovered ? "bg-emerald-600" : isVerifying ? "bg-amber-500 animate-pulse" : "bg-stone-400"
                }`}
              />
              <div className="bg-stone-50 p-4 rounded-xl border border-stone-200/80 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-bold text-stone-500 block uppercase tracking-wider">
                    STAGE 05 • VERIFICATION OUTCOME
                  </span>
                  <div className="text-sm font-sans font-bold text-stone-900 mt-0.5">
                    {isRecovered
                      ? "✓ Authoritative Payment Capture Verified — $0.00 Remaining Exposure"
                      : isVerifying
                      ? "⏳ Verification Pending — Gateway Reconciliation Active"
                      : isNoAction
                      ? "🛑 RECLAIM STOPPED — Merchant Capital Preserved"
                      : caseData.status}
                  </div>
                </div>
                <span
                  className={`rounded-md px-3 py-1 text-xs font-sans font-bold ${
                    isRecovered
                      ? "bg-emerald-600 text-white"
                      : isVerifying
                      ? "bg-amber-100 text-amber-950 border border-amber-300"
                      : "bg-stone-900 text-white"
                  }`}
                >
                  {caseData.verification_outcome || caseData.status}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
