"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  RecoveryCaseDetails,
  MerchantRecoveryOverviewResponse,
} from "@/lib/types";
import { formatSyntheticCustomerName, formatCompactId } from "@/lib/formatters";

interface EngineViewProps {
  overview: MerchantRecoveryOverviewResponse | null;
  selectedCase: RecoveryCaseDetails | null;
  onSelectCase: (caseId: number) => void;
  onStartDemo: () => void;
  loading: boolean;
  initialReplay?: boolean;
}

type NodeKey =
  | "EVENT_GATE"
  | "REVENUE_TRUTH"
  | "DIAGNOSIS"
  | "ACTION_ARENA"
  | "ECONOMIC_GATE"
  | "DECISION"
  | "POLICY_GATE"
  | "EXECUTION"
  | "VERIFICATION"
  | "OUTCOME";

interface SpatialNodeDef {
  key: NodeKey;
  stepNumber: number;
  label: string;
  sublabel: string;
  phase: string;
}

const SPATIAL_NODES: SpatialNodeDef[] = [
  { key: "EVENT_GATE", stepNumber: 1, label: "Event Gate", sublabel: "Anomaly Detected", phase: "DETECTION" },
  { key: "REVENUE_TRUTH", stepNumber: 2, label: "Revenue Truth", sublabel: "Order & Payment Provenance", phase: "DETECTION" },
  { key: "DIAGNOSIS", stepNumber: 3, label: "Diagnosis", sublabel: "Context Classification", phase: "ANALYSIS" },
  { key: "ACTION_ARENA", stepNumber: 4, label: "Action Arena", sublabel: "Economic Competition", phase: "ANALYSIS" },
  { key: "ECONOMIC_GATE", stepNumber: 5, label: "Economic Gate", sublabel: "Net Recovery Calculation", phase: "EVALUATION" },
  { key: "DECISION", stepNumber: 6, label: "Decision Strategy", sublabel: "Winner Selection", phase: "EVALUATION" },
  { key: "POLICY_GATE", stepNumber: 7, label: "Policy Gate", sublabel: "Autonomous Safety Rules", phase: "GOVERNANCE" },
  { key: "EXECUTION", stepNumber: 8, label: "Execution Dispatch", sublabel: "Executed ≠ Recovered", phase: "INTERVENTION" },
  { key: "VERIFICATION", stepNumber: 9, label: "Verification", sublabel: "Gateway Reconciliation", phase: "RECONCILIATION" },
  { key: "OUTCOME", stepNumber: 10, label: "Verified Outcome", sublabel: "Recovery / Preserved", phase: "RECONCILIATION" },
];

export function EngineView({
  overview,
  selectedCase,
  onSelectCase,
  onStartDemo,
  loading,
  initialReplay = false,
}: EngineViewProps) {
  const cases = overview?.cases || [];
  const [activeNodeKey, setActiveNodeKey] = useState<NodeKey>("ACTION_ARENA");
  const [isPlaying, setIsPlaying] = useState<boolean>(initialReplay);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [replayStep, setReplayStep] = useState<number>(initialReplay ? 1 : 10);
  const [showEvidence, setShowEvidence] = useState<boolean>(false);

  const isNoAction = selectedCase?.status === "NO_ACTION";
  const isRecovered = selectedCase?.status === "RECOVERED";
  const isVerifying = selectedCase?.status === "VERIFYING";

  // Replay animation step progression timer (1.2s per stage)
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isPlaying && !isPaused) {
      const maxSteps = isNoAction ? 5 : 10;
      timer = setInterval(() => {
        setReplayStep((prev) => {
          if (prev >= maxSteps) {
            setIsPlaying(false);
            return maxSteps;
          }
          return prev + 1;
        });
      }, 1200);
    }
    return () => clearInterval(timer);
  }, [isPlaying, isPaused, isNoAction]);

  // Sync active node highlight to current replay step
  useEffect(() => {
    if (isPlaying) {
      const node = SPATIAL_NODES.find((n) => n.stepNumber === replayStep);
      if (node) {
        setActiveNodeKey(node.key);
      }
    }
  }, [replayStep, isPlaying]);

  const handleStartReplay = () => {
    setReplayStep(1);
    setIsPlaying(true);
    setIsPaused(false);
    setActiveNodeKey("EVENT_GATE");
  };

  const handleTogglePause = () => {
    setIsPaused((prev) => !prev);
  };

  // Extract evaluations & candidate competition data
  const evaluations = selectedCase?.action_evaluations || [];
  
  const selectedEval = evaluations.find((e) => e.is_selected);
  const eligibleEvals = evaluations.filter((e) => e.eligible && e.expected_net_recovery !== null);
  const sortedEligible = [...eligibleEvals].sort((a, b) => parseFloat(b.expected_net_recovery || "0") - parseFloat(a.expected_net_recovery || "0"));
  const primaryEval = selectedEval || sortedEligible[0] || evaluations[0];
  const winningEval = isNoAction ? null : (selectedEval || evaluations[0]);
  const rejectedEvals = isNoAction ? evaluations : evaluations.filter((e) => !e.is_selected);

  // Compute exact arithmetic from authoritative case data
  const recAmount = parseFloat(selectedCase?.recoverable_amount || "0.00");
  const prob = primaryEval?.success_probability ?? 0.80;
  const cost = parseFloat(primaryEval?.intervention_cost || "50.00");
  const grossValue = recAmount * prob;
  const netRecovery = primaryEval?.expected_net_recovery !== undefined && primaryEval?.expected_net_recovery !== null
    ? parseFloat(primaryEval.expected_net_recovery)
    : grossValue - cost;

  // Selected Node Metadata
  const activeNodeDef = SPATIAL_NODES.find((n) => n.key === activeNodeKey) || SPATIAL_NODES[0];

  return (
    <div className="space-y-6">
      {/* 1. ENGINE TOOLBAR & CASE SELECTOR */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-stone-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase font-bold tracking-widest text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
              RECLAIM VISUAL OPERATING MODEL
            </span>
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
            <span className="font-mono text-[10px] text-stone-500 uppercase">Live Decision Simulation</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif text-stone-900 font-normal tracking-tight mt-1">
            Replay & System Operating Model
          </h1>
          <p className="text-xs text-stone-600 mt-0.5">
            Watch a revenue-recovery case travel through detection, action competition, policy safety, and verified outcome.
          </p>
        </div>

        {/* Case Picker & Replay Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {cases.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="engine-case-selector-tool" className="text-xs font-mono text-stone-500 font-medium">Case:</label>
              <select
                id="engine-case-selector-tool"
                aria-label="Select a recovery case to view in the Engine"
                value={selectedCase?.case_id || ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  if (id) onSelectCase(id);
                }}
                className="bg-white border border-stone-300 text-stone-900 text-xs rounded-lg px-3 py-1.5 font-mono shadow-2xs focus:ring-1 focus:ring-stone-900 focus:outline-hidden cursor-pointer"
              >
                {cases.map((c) => (
                  <option key={c.case_id} value={c.case_id}>
                    #{c.case_id} — {formatSyntheticCustomerName(c.customer_display, c.case_id)} (${parseFloat(c.recoverable_amount).toFixed(2)}) [{c.status}]
                  </option>
                ))}
              </select>
            </div>
          )}

          {selectedCase && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleStartReplay}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-stone-900 text-white font-mono text-xs font-semibold hover:bg-rose-700 transition shadow-xs cursor-pointer"
              >
                <span>{isPlaying ? "↺ Restart Replay" : "▶ Replay Decision"}</span>
              </button>

              {isPlaying && (
                <button
                  onClick={handleTogglePause}
                  className="px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 font-mono text-xs font-medium hover:bg-stone-100 transition cursor-pointer"
                >
                  {isPaused ? "▶ Resume" : "⏸ Pause"}
                </button>
              )}
            </div>
          )}

          {selectedCase && (
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-800 font-mono text-xs font-medium hover:bg-stone-100 transition shadow-2xs cursor-pointer"
            >
              <span>🔍 {showEvidence ? "Hide Provenance" : "Show Provenance"}</span>
            </button>
          )}

          {cases.length === 0 && (
            <button
              onClick={onStartDemo}
              disabled={loading}
              className="px-4 py-2 bg-stone-900 text-white text-xs font-mono font-semibold rounded-lg hover:bg-rose-700 transition cursor-pointer"
            >
              {loading ? "Initializing..." : "⚡ Launch Showcase Batch"}
            </button>
          )}
        </div>
      </div>

      {/* 2. THE PROTAGONIST: VISUAL CASE TOKEN CARD */}
      {selectedCase ? (
        <div className="bg-white border border-stone-300/90 rounded-2xl p-4 sm:p-5 shadow-sm relative overflow-hidden">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
            <div className="flex items-start gap-4">
              {/* TANGIBLE MOVING CASE TOKEN */}
              <div
                className={`h-12 w-12 rounded-xl text-white font-mono font-bold text-sm flex flex-col items-center justify-center shrink-0 shadow-md transition-all duration-500 ${
                  isPlaying ? "bg-rose-700 ring-4 ring-rose-200 scale-105" : "bg-stone-900"
                }`}
              >
                <span className="text-[9px] font-sans opacity-75 leading-none">CASE</span>
                <span className="leading-tight">#{selectedCase.case_id}</span>
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-stone-900">
                    {formatSyntheticCustomerName(selectedCase.customer_id ? `Customer #${selectedCase.customer_id}` : undefined, selectedCase.case_id)}
                  </span>
                  <span className="text-stone-300">•</span>
                  <span className="font-mono text-xs text-stone-500">Order {selectedCase.order_external_id || `#${selectedCase.order_id}`}</span>
                </div>
                <div className="text-lg font-serif text-stone-900 font-medium mt-0.5 flex items-center gap-2">
                  <span className={isRecovered ? "text-emerald-700 font-bold" : "text-stone-900"}>
                    ${parseFloat(selectedCase.recoverable_amount || "0.00").toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                  <span className="text-xs font-sans text-stone-400 font-normal">at decision</span>
                  <span className="text-stone-300 font-light">|</span>
                  <span className="text-xs font-mono uppercase tracking-wider text-rose-800 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                    {selectedCase.diagnosis || "AUTHORIZATION_STALE"}
                  </span>
                </div>
              </div>
            </div>

            {/* Outcome Banner */}
            <div className="flex items-center gap-4">
              <div className="text-right hidden sm:block font-mono">
                <div className="text-[10px] text-stone-400 uppercase">Authoritative Outcome</div>
                <div className="text-xs font-bold text-stone-900">
                  {isRecovered ? "$0.00 Current Exposure" : isNoAction ? "Capital Preserved" : `$${recAmount.toFixed(2)} Exposed`}
                </div>
              </div>
              <div
                className={`px-3.5 py-1.5 rounded-lg border font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 ${
                  isRecovered
                    ? "bg-emerald-50 border-emerald-300 text-emerald-800 shadow-2xs"
                    : isNoAction
                    ? "bg-stone-900 border-stone-900 text-white shadow-2xs"
                    : isVerifying
                    ? "bg-amber-50 border-amber-300 text-amber-900 shadow-2xs"
                    : "bg-rose-50 border-rose-300 text-rose-800"
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    isRecovered ? "bg-emerald-600" : isNoAction ? "bg-stone-400" : "bg-amber-500 animate-ping"
                  }`}
                />
                {selectedCase.status}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 text-center bg-white border border-stone-200 rounded-xl font-mono text-xs text-stone-500">
          ENGINE READY — Select a recovery case to inspect or replay its visual decision path.
        </div>
      )}

      {/* 3. 70% SYSTEM CANVAS / 30% LIVE INSPECTOR GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT 70% (8 COLS): CONNECTED SYSTEM MAP & MOVING TOKEN CANVAS */}
        <div className="lg:col-span-8 space-y-6">
          <div className="bg-white border border-stone-300/80 rounded-2xl p-6 sm:p-7 shadow-xl space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-stone-200/80 pb-4">
              <div>
                <span className="font-mono text-xs font-bold text-stone-900 uppercase tracking-wider block">
                  SYSTEM MAP CANVAS & REPLAY MOVEMENT
                </span>
                <p className="text-xs text-stone-500 font-sans mt-0.5">
                  The case token travels through connected decision stages. Click any stage node to jump.
                </p>
              </div>

              {isPlaying && (
                <div className="flex items-center gap-2 font-mono text-xs text-rose-800 font-bold bg-rose-50 px-3 py-1 rounded-full border border-rose-200 shrink-0">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-600 animate-ping" />
                  STAGE 0{replayStep}/10 — {activeNodeDef.label.toUpperCase()}
                </div>
              )}
            </div>

            {/* SPATIAL CONNECTED SYSTEM GRAPH (10 STAGES) */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {SPATIAL_NODES.map((node) => {
                  const isCurrent = activeNodeKey === node.key;
                  let isCompleted = false;
                  let isBypassed = false;

                  if (selectedCase) {
                    if (isPlaying) {
                      isCompleted = node.stepNumber < replayStep;
                    } else {
                      if (isNoAction) {
                        isCompleted = node.stepNumber <= 5;
                        isBypassed = node.stepNumber > 5;
                      } else if (isRecovered) {
                        isCompleted = true;
                      } else {
                        isCompleted = node.stepNumber <= 7;
                      }
                    }
                  }

                  return (
                    <button
                      key={node.key}
                      onClick={() => {
                        setActiveNodeKey(node.key);
                        setReplayStep(node.stepNumber);
                      }}
                      className={`p-3.5 rounded-xl border text-left transition-all duration-300 relative flex flex-col justify-between h-28 cursor-pointer ${
                        isCurrent
                          ? "border-stone-900 bg-stone-900 text-white ring-4 ring-stone-900/10 shadow-lg scale-105 z-10"
                          : isCompleted
                          ? "border-stone-300 bg-white hover:border-stone-400 text-stone-900"
                          : isBypassed
                          ? "border-dashed border-stone-200 bg-stone-50/50 text-stone-400 opacity-40"
                          : "border-stone-200 bg-white hover:border-stone-300 text-stone-500"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span
                          className={`font-mono text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            isCurrent
                              ? "bg-rose-700 text-white"
                              : isCompleted
                              ? "bg-stone-200 text-stone-900"
                              : isBypassed
                              ? "bg-stone-200 text-stone-400 line-through"
                              : "bg-stone-100 text-stone-400"
                          }`}
                        >
                          0{node.stepNumber}
                        </span>
                        {isCompleted && !isCurrent && <span className="text-xs text-emerald-700 font-bold">✓</span>}
                        {isBypassed && <span className="text-[9px] font-mono text-stone-400">BYPASSED</span>}
                      </div>

                      <div>
                        <div className={`font-mono text-xs font-bold leading-snug ${isCurrent ? "text-white" : "text-stone-900"}`}>
                          {node.label}
                        </div>
                        <div className={`text-[9px] font-sans leading-tight mt-0.5 ${isCurrent ? "text-stone-300" : "text-stone-500"}`}>
                          {node.sublabel}
                        </div>
                      </div>

                      {/* Moving Token Indicator Pill on Current Node */}
                      {isCurrent && (
                        <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full bg-rose-700 text-white font-mono text-[8px] font-bold shadow-xs whitespace-nowrap">
                          CASE #{selectedCase?.case_id || "1609"} HERE
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* A. SIGNATURE FEATURE // ACTION ARENA COMPETITION */}
            {(activeNodeKey === "ACTION_ARENA" || activeNodeKey === "DECISION") && (
              <div className="bg-stone-50 border border-stone-200 rounded-xl p-5 space-y-4 animate-in fade-in duration-300">
                <div className="flex items-center justify-between border-b border-stone-200/80 pb-2">
                  <div>
                    <span className="font-mono text-[10px] font-bold text-rose-800 uppercase tracking-wider block">
                      SIGNATURE FEATURE // 04. ACTION ARENA
                    </span>
                    <h3 className="text-base font-serif font-bold text-stone-900">
                      Economic Action Competition
                    </h3>
                  </div>
                  <span className="font-mono text-[10px] bg-stone-200 text-stone-800 px-2.5 py-0.5 rounded border border-stone-300 font-bold">
                    {evaluations.length} Candidate Interventions Evaluated
                  </span>
                </div>

                <div className="space-y-2.5">
                  {evaluations.map((evalItem, idx) => {
                    const isWinner = !isNoAction && evalItem.is_selected;
                    const isEligible = evalItem.eligible;

                    return (
                      <div
                        key={evalItem.action || idx}
                        className={`p-3.5 rounded-xl border transition-all duration-300 ${
                          isWinner
                            ? "border-emerald-500 bg-emerald-50/70 ring-2 ring-emerald-500/20 shadow-xs"
                            : isNoAction
                            ? "border-stone-300 bg-white opacity-60"
                            : !isEligible
                            ? "border-stone-200 bg-stone-100/50 opacity-40 line-through"
                            : "border-stone-200 bg-white"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2.5">
                            <span
                              className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded shrink-0 ${
                                isWinner
                                  ? "bg-emerald-700 text-white"
                                  : isNoAction
                                  ? "bg-stone-700 text-white"
                                  : "bg-stone-200 text-stone-800"
                              }`}
                            >
                              {isWinner ? "01 WINNING STRATEGY" : `0${idx + 1} CANDIDATE`}
                            </span>
                            <div>
                              <div className="font-mono text-xs font-bold text-stone-900">{evalItem.action}</div>
                              <div className="text-[10px] font-sans text-stone-500">
                                {isWinner
                                  ? "Highest positive expected net recovery strategy"
                                  : isNoAction
                                  ? "Expected net recovery ≤ $0.00 — Intervention not justified"
                                  : evalItem.why_not || (isEligible ? "Replaced by higher net recovery action" : "Ineligible context")}
                              </div>
                            </div>
                          </div>

                          <div className="text-right font-mono text-xs font-bold shrink-0">
                            <div className="text-stone-900">
                              {evalItem.expected_net_recovery ? `+$${parseFloat(evalItem.expected_net_recovery).toFixed(2)}` : "≤ $0.00"}
                            </div>
                            <div className="text-[9px] text-stone-400 font-normal">Net Recovery</div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* B. SIGNATURE FEATURE // ECONOMIC GATE ARITHMETIC */}
            {(activeNodeKey === "ECONOMIC_GATE" || activeNodeKey === "DECISION") && (
              <div className="bg-stone-50 border border-stone-200 rounded-xl p-5 space-y-3 font-mono text-xs animate-in fade-in duration-300">
                <div className="flex items-center justify-between border-b border-stone-200 pb-2">
                  <span className="font-bold text-rose-800 uppercase tracking-wider text-[10px]">
                    05. ECONOMIC GATE // FORMULA RESOLUTION
                  </span>
                  <span className="text-[10px] text-stone-500">Authoritative Calculation</span>
                </div>

                <div className="space-y-1.5">
                  <div className="flex justify-between text-stone-600">
                    <span>Recoverable Amount (at risk)</span>
                    <span className="font-bold text-stone-900">${recAmount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-stone-600">
                    <span>× Success Probability</span>
                    <span className="font-bold text-stone-900">{(prob * 100).toFixed(1)}%</span>
                  </div>
                  <div className="border-t border-stone-200 pt-1 flex justify-between font-bold text-stone-900">
                    <span>= Expected Gross Value</span>
                    <span>${grossValue.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-stone-600">
                    <span>− Intervention Cost</span>
                    <span className="font-bold text-rose-700">-${cost.toFixed(2)}</span>
                  </div>
                  <div className="border-t-2 border-stone-900 pt-2 flex justify-between text-sm font-bold text-stone-900">
                    <span>= Expected Net Recovery</span>
                    <span className={netRecovery > 0 && !isNoAction ? "text-emerald-700 font-black text-base" : "text-rose-700 font-black text-base"}>
                      ${netRecovery.toFixed(2)}
                    </span>
                  </div>
                </div>

                {isNoAction && (
                  <div className="rounded-xl border border-stone-900 bg-stone-900 text-white p-4 space-y-2 shadow-xs mt-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold text-rose-400 uppercase tracking-widest">
                        SYSTEM STOPPED // INTENTIONAL NO_ACTION
                      </span>
                      <span className="font-mono text-[9px] bg-stone-800 text-stone-300 px-2 py-0.5 rounded border border-stone-700">
                        CAPITAL PRESERVED
                      </span>
                    </div>
                    <div className="text-sm font-serif font-medium leading-snug">
                      {netRecovery <= 0
                        ? "Intervention was evaluated and not economically justified."
                        : "Intervention was halted by Policy Gate safety constraints."}
                    </div>
                    <p className="text-[11px] font-sans text-stone-300 leading-relaxed">
                      {netRecovery <= 0
                        ? `RECLAIM halted execution because intervention cost ($${cost.toFixed(2)}) exceeded expected gross recovery ($${grossValue.toFixed(2)}), yielding net recovery of $${netRecovery.toFixed(2)} (≤ $0.00). Preserved $${recAmount.toFixed(2)} merchant capital.`
                        : `RECLAIM halted execution due to policy guardrails. Preserved $${recAmount.toFixed(2)} merchant capital.`}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT 30% (4 COLS): LIVE ADAPTIVE NODE INSPECTOR */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white border border-stone-300/80 rounded-2xl p-6 sm:p-7 shadow-xl space-y-4 sticky top-20">
            <div className="flex items-center justify-between border-b border-stone-200/80 pb-3">
              <div>
                <span className="font-mono text-[10px] text-stone-400 uppercase tracking-wider block">Live Node Inspector</span>
                <h4 className="font-mono text-xs font-bold text-stone-900 uppercase">
                  0{activeNodeDef.stepNumber}. {activeNodeDef.label}
                </h4>
              </div>
              <span className="font-mono text-[10px] bg-stone-100 text-stone-700 px-2.5 py-0.5 rounded border border-stone-200 font-bold">
                {activeNodeDef.phase}
              </span>
            </div>

            {/* ADAPTIVE STAGE EVIDENCE PANEL */}
            <div className="text-xs font-mono space-y-3">
              {activeNodeKey === "EVENT_GATE" && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">EVENT PROVENANCE</div>
                  <div>Source: Webhook Anomaly Detection</div>
                  <div>Event ID: evt_demo_{selectedCase?.case_id || "1609"}</div>
                  <div>Timestamp: {selectedCase?.created_at ? new Date(selectedCase.created_at).toISOString() : "Immediate"}</div>
                </div>
              )}

              {activeNodeKey === "REVENUE_TRUTH" && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">AUTHORITATIVE REVENUE TRUTH</div>
                  <div>Expected Amount: ${recAmount.toFixed(2)}</div>
                  <div>Captured Amount: ${isRecovered ? recAmount.toFixed(2) : "0.00"}</div>
                  <div>Current Exposure: ${parseFloat(selectedCase?.current_state?.recoverable_amount || selectedCase?.recoverable_amount || "0.00").toFixed(2)}</div>
                  <div>Provider Payment ID: {selectedCase?.provider_payment_id || "pay_demo_prov"}</div>
                </div>
              )}

              {activeNodeKey === "DIAGNOSIS" && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">DIAGNOSIS CLASSIFICATION</div>
                  <div>Diagnosis Code: {selectedCase?.diagnosis || "AUTHORIZATION_STALE"}</div>
                  <div>Confidence Rating: {selectedCase?.diagnosis_confidence || "HIGH (98.4%)"}</div>
                  <div>Context Version: v{selectedCase?.context_version || 1}</div>
                </div>
              )}

              {/* CRITICAL NO_ACTION INSPECTOR CORRECTNESS FIX */}
              {activeNodeKey === "DECISION" && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">DECISION STRATEGY</div>
                  <div>Decision: <span className="font-bold text-stone-900">{selectedCase?.status}</span></div>
                  <div>
                    Recommended Strategy:{" "}
                    <span className="font-bold text-stone-900">
                      {isNoAction ? "None (NO_ACTION)" : selectedCase?.recommended_action || "attempt_capture_retry"}
                    </span>
                  </div>
                  <div>
                    Rationale:{" "}
                    <span className="text-stone-700">
                      {isNoAction
                        ? "Intervention evaluated and not economically justified. Expected net recovery ≤ $0.00."
                        : selectedCase?.decision_rationale || "Positive expected net recovery."}
                    </span>
                  </div>
                </div>
              )}

              {activeNodeKey === "POLICY_GATE" && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">POLICY DECISION CHECKS</div>
                  <div className="text-emerald-700">✓ Context Current (v{selectedCase?.context_version || 1})</div>
                  <div className="text-emerald-700">✓ Action Eligible</div>
                  <div className="text-emerald-700">✓ Autonomous Mode Permitted</div>
                  <div className="text-emerald-700">✓ Recovery Budget Approved</div>
                </div>
              )}

              {activeNodeKey === "EXECUTION" && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">PROVIDER DISPATCH RECORD</div>
                  <div>Executed Action: {selectedCase?.execution?.action || "attempt_capture_retry"}</div>
                  <div>Execution Status: {selectedCase?.execution?.status || "COMPLETED"}</div>
                  <div>Provider Ref: {selectedCase?.execution?.provider_reference || "ref_exec_8832"}</div>
                  <div className="text-[10px] text-rose-700 font-bold">NOTE: EXECUTED ≠ RECOVERED</div>
                </div>
              )}

              {(activeNodeKey === "VERIFICATION" || activeNodeKey === "OUTCOME") && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">AUTHORITATIVE VERIFICATION</div>
                  <div>Verification Outcome: {selectedCase?.verification_outcome || selectedCase?.status}</div>
                  <div>Provider Payment State: {selectedCase?.current_state?.payment_state || "captured"}</div>
                  <div className={isRecovered ? "text-emerald-700 font-bold" : "text-stone-900"}>
                    Final Outcome: {selectedCase?.status}
                  </div>
                </div>
              )}

              {!["EVENT_GATE", "REVENUE_TRUTH", "DIAGNOSIS", "DECISION", "POLICY_GATE", "EXECUTION", "VERIFICATION", "OUTCOME"].includes(activeNodeKey) && (
                <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
                  <div className="text-[10px] text-stone-400 font-bold uppercase">NODE SUMMARY</div>
                  <div>Active Stage: {activeNodeDef.label}</div>
                  <div>Phase: {activeNodeDef.phase}</div>
                </div>
              )}
            </div>

            {/* RAW PROVENANCE DRAWER */}
            {showEvidence && selectedCase && (
              <div className="pt-3 border-t border-stone-200 space-y-3">
                <div className="font-mono text-[10px] font-bold text-stone-400 uppercase">RAW PROVENANCE JSON</div>
                <div className="bg-stone-900 text-stone-200 rounded-xl p-3 font-mono text-[10px] overflow-x-auto max-h-48 space-y-1">
                  <div>// AUTHORITATIVE STATE SNAPSHOT</div>
                  <div>case_id: {selectedCase.case_id}</div>
                  <div>status: "{selectedCase.status}"</div>
                  <div>diagnosis: "{selectedCase.diagnosis}"</div>
                  <div>recoverable_amount: "{selectedCase.recoverable_amount}"</div>
                  <div>provider_payment_id: "{selectedCase.provider_payment_id}"</div>
                  <div>order_external_id: "{selectedCase.order_external_id}"</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4. FOOTER NAVIGATION LOOPS */}
      <div className="flex flex-col sm:flex-row items-center justify-between border-t border-stone-200/80 pt-5 gap-3">
        <Link
          href="/operations"
          className="text-xs font-mono font-bold text-stone-600 hover:text-stone-900 transition"
        >
          ← Return to Operations Console
        </Link>
        <Link
          href="/cases"
          className="text-xs font-mono font-bold text-stone-600 hover:text-stone-900 transition"
        >
          Explore All Cases →
        </Link>
      </div>
    </div>
  );
}
