"use client";

import { useState } from "react";
import { DemoScenarioResponse } from "@/lib/types";

interface DemoControlsProps {
  currentStatus: string | null;
  currentCaseId: number | null;
  onScenarioUpdate: (caseId: number) => void;
  onError: (msg: string) => void;
}

export function DemoControls({
  currentStatus,
  currentCaseId,
  onScenarioUpdate,
  onError,
}: DemoControlsProps) {
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);

  async function handleTriggerRecoveryScenario() {
    setLoading(true);
    setActiveAction("recovery");
    try {
      const demoRunId = crypto.randomUUID();
      const res = await fetch("/api/demo/recovery-scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ demo_run_id: demoRunId }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: "Scenario execution failed" }));
        throw new Error(errJson.detail || `Server error (${res.status})`);
      }
      const data: DemoScenarioResponse = await res.json();
      if (data.case_id) {
        onScenarioUpdate(data.case_id);
      }
    } catch (e: any) {
      onError(e.message || "Failed to trigger recovery scenario");
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  }

  async function handleTriggerNoActionScenario() {
    setLoading(true);
    setActiveAction("no_action");
    try {
      const demoRunId = crypto.randomUUID();
      const res = await fetch("/api/demo/no-action-scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ demo_run_id: demoRunId }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: "NO_ACTION scenario failed" }));
        throw new Error(errJson.detail || `Server error (${res.status})`);
      }
      const data: DemoScenarioResponse = await res.json();
      if (data.case_id) {
        onScenarioUpdate(data.case_id);
      }
    } catch (e: any) {
      onError(e.message || "Failed to trigger NO_ACTION scenario");
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  }

  async function handleSimulateCapture() {
    if (!currentCaseId) return;
    setLoading(true);
    setActiveAction("capture");
    try {
      const res = await fetch("/api/demo/recovery-scenario/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: currentCaseId }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: "Capture simulation failed" }));
        throw new Error(errJson.detail || `Server error (${res.status})`);
      }
      const data: DemoScenarioResponse = await res.json();
      if (data.case_id) {
        onScenarioUpdate(data.case_id);
      }
    } catch (e: any) {
      onError(e.message || "Failed to simulate payment capture");
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  }

  const isVerifying = currentStatus === "VERIFYING";

  return (
    <div className="rounded-xl border border-stone-200/90 bg-stone-100/60 px-4 py-2.5 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-sans">
      {/* LEFT: DEMO UTILITY LABEL */}
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-stone-400" />
        <span className="font-mono font-bold text-[10px] text-stone-500 uppercase tracking-widest">
          DEMO CONTROLS
        </span>
        <span className="text-[10px] text-stone-400 hidden lg:inline">| Synthetic event generator</span>
      </div>

      {/* RIGHT: COMPACT UTILITY BUTTON STRIP */}
      <div className="flex items-center gap-2.5 flex-wrap">
        <button
          onClick={handleTriggerRecoveryScenario}
          disabled={loading}
          className="rounded-md bg-stone-900 hover:bg-rose-700 text-white px-3 py-1.5 font-sans font-medium text-[11px] transition cursor-pointer disabled:opacity-50"
        >
          {loading && activeAction === "recovery" ? "Executing..." : "ACT — Recover Revenue"}
        </button>

        <button
          onClick={handleTriggerNoActionScenario}
          disabled={loading}
          className="rounded-md bg-stone-800 hover:bg-stone-900 text-white px-3 py-1.5 font-sans font-medium text-[11px] transition cursor-pointer disabled:opacity-50"
        >
          {loading && activeAction === "no_action" ? "Executing..." : "DON'T ACT — Preserved Capital"}
        </button>

        <button
          onClick={handleSimulateCapture}
          disabled={loading || !isVerifying || !currentCaseId}
          className={`rounded-md border px-3 py-1.5 font-sans font-medium text-[11px] transition ${
            isVerifying && currentCaseId
              ? "bg-emerald-700 hover:bg-emerald-800 text-white border-emerald-700 cursor-pointer shadow-2xs"
              : "bg-stone-200/60 text-stone-400 border-stone-300/60 cursor-not-allowed"
          }`}
        >
          {loading && activeAction === "capture" ? "Reconciling..." : "Simulate Payment Capture"}
        </button>
      </div>
    </div>
  );
}
