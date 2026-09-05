"use client";

interface EmptyStateProps {
  onStartDemo: () => void;
  loading: boolean;
}

export function EmptyState({ onStartDemo, loading }: EmptyStateProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-xs max-w-xl mx-auto space-y-4">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-slate-900 text-white font-mono font-black text-lg">
        RC
      </div>
      <div>
        <h3 className="text-lg font-bold text-slate-900 font-sans">No Active Case Selected</h3>
        <p className="text-xs text-slate-500 mt-1 font-sans leading-relaxed">
          Initialize a demo scenario using the scenario controller toolbar above to trigger the autonomous decision engine, policy gate, and verification pipeline.
        </p>
      </div>
      <div className="pt-2">
        <button
          onClick={onStartDemo}
          disabled={loading}
          className="rounded-md bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white px-5 py-2.5 text-xs font-mono font-bold transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-xs"
        >
          {loading ? "Initializing Demo Scenario..." : "Start Recovery Scenario"}
        </button>
      </div>
    </div>
  );
}
