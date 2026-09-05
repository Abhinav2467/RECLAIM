"use client";

interface StatusPipelineProps {
  status: string;
}

const NORMAL_STAGES = [
  { key: "DETECTED", label: "DETECTED" },
  { key: "DIAGNOSED", label: "ANALYZING" },
  { key: "RECOMMENDATION_READY", label: "DECISION" },
  { key: "APPROVED", label: "APPROVED" },
  { key: "EXECUTING", label: "EXECUTING" },
  { key: "VERIFYING", label: "VERIFYING" },
  { key: "RECOVERED", label: "RECOVERED" },
];

const NO_ACTION_STAGES = [
  { key: "DETECTED", label: "DETECTED" },
  { key: "DIAGNOSED", label: "ANALYZING" },
  { key: "RECOMMENDATION_READY", label: "DECISION" },
  { key: "NO_ACTION", label: "NO_ACTION" },
];

function getStageIndex(statusStr: string, isNoAction: boolean): number {
  const upper = statusStr.toUpperCase();
  if (isNoAction) {
    if (upper === "DETECTED") return 0;
    if (upper === "DIAGNOSED") return 1;
    if (upper === "RECOMMENDATION_READY") return 2;
    if (upper === "NO_ACTION") return 3;
    return 3;
  }
  if (upper === "DETECTED") return 0;
  if (upper === "DIAGNOSED") return 1;
  if (upper === "RECOMMENDATION_READY") return 2;
  if (upper === "APPROVED") return 3;
  if (upper === "EXECUTING") return 4;
  if (upper === "VERIFYING") return 5;
  if (upper === "RECOVERED") return 6;
  if (upper === "ABORTED" || upper === "FAILED") return -1;
  return 0;
}

export function StatusPipeline({ status }: StatusPipelineProps) {
  const isNoAction = status.toUpperCase() === "NO_ACTION";
  const stages = isNoAction ? NO_ACTION_STAGES : NORMAL_STAGES;
  const currentIndex = getStageIndex(status, isNoAction);
  const isAbortedOrFailed = status === "ABORTED" || status === "FAILED";

  return (
    <div className="rounded-2xl border border-stone-300/80 bg-white p-6 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-stone-200/80 pb-4 text-xs font-sans">
        <h2 className="text-xl font-serif-editorial font-bold text-stone-900 tracking-tight">
          Lifecycle Progression Index
        </h2>
        <span
          className={`font-mono text-[10px] font-bold px-2.5 py-1 rounded-md border uppercase ${
            status === "RECOVERED"
              ? "bg-emerald-100/90 text-emerald-950 border-emerald-300/90"
              : status === "VERIFYING"
              ? "bg-amber-100/90 text-amber-950 border-amber-300/90"
              : isNoAction
              ? "bg-stone-900 text-white border-stone-900"
              : "bg-stone-100 text-stone-800 border-stone-300/80"
          }`}
        >
          {status}
        </span>
      </div>

      {/* COMPACT VERTICAL PROGRESS MAP — SYNCHRONIZED WITH LEFT DECISION SPINE */}
      <div className="relative pl-6 space-y-4.5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-stone-200">
        {stages.map((stage, idx) => {
          const isPassed = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const isRecovered = stage.key === "RECOVERED" && status === "RECOVERED";
          const isTerminalNoAction = stage.key === "NO_ACTION" && isNoAction;

          let dotClass = "bg-stone-300 ring-4 ring-white";
          let labelColor = "text-stone-400 font-medium";
          let badgeText = "";

          if (isRecovered) {
            dotClass = "bg-emerald-600 ring-4 ring-emerald-100";
            labelColor = "text-emerald-950 font-bold";
            badgeText = "✓ VERIFIED RECOVERED";
          } else if (isTerminalNoAction) {
            dotClass = "bg-stone-900 ring-4 ring-stone-200";
            labelColor = "text-stone-900 font-bold";
            badgeText = "🛑 RECLAIM STOPPED";
          } else if (isCurrent) {
            dotClass = "bg-amber-500 ring-4 ring-amber-100 animate-pulse";
            labelColor = "text-stone-900 font-bold";
            badgeText = status === "VERIFYING" ? "⏳ ACTIVE VERIFICATION" : "● CURRENT STAGE";
          } else if (isPassed) {
            dotClass = "bg-stone-900 ring-4 ring-white";
            labelColor = "text-stone-700 font-semibold";
            badgeText = "✓ PASSED";
          }

          if (isAbortedOrFailed && isCurrent) {
            dotClass = "bg-rose-700 ring-4 ring-rose-100";
            labelColor = "text-rose-900 font-bold";
            badgeText = "✕ FAILED";
          }

          return (
            <div key={stage.key} className="relative flex items-center justify-between text-xs font-sans">
              <span className={`absolute -left-[22px] h-3 w-3 rounded-full transition-all ${dotClass}`} />
              <span className={`font-mono text-[11px] uppercase tracking-wide ${labelColor}`}>
                {stage.label}
              </span>
              {badgeText && (
                <span className="font-mono text-[10px] font-bold text-stone-500">
                  {badgeText}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
