"use client";

import { useState, useEffect } from "react";

const STAGES = [
  {
    step: "01 MONEY",
    title: "Payment Failure Detected",
    value: "$199.99 AT RISK",
    detail: "Provider State: authorization_expired | Order #8921",
    badge: "EXPOSURE",
    color: "bg-rose-50 text-rose-800 border-rose-200",
  },
  {
    step: "02 CONTEXT",
    title: "Contextual Logic Diagnosis",
    value: "AUTHORIZATION_STALE",
    detail: "High confidence (95%) | Provenance verified via webhook",
    badge: "DIAGNOSIS",
    color: "bg-slate-100 text-slate-800 border-slate-200",
  },
  {
    step: "03 DECISION",
    title: "Economic Action Competition",
    value: "75% PROBABILITY ➔ $149.49 NET",
    detail: "attempt_capture_retry selected over manual_review ($55.00)",
    badge: "EXPECTED NET",
    color: "bg-amber-50 text-amber-900 border-amber-200",
  },
  {
    step: "04 POLICY",
    title: "Bounded Autonomy Policy Gate",
    value: "POLICY APPROVED",
    detail: "Eligibility verified | Autonomous threshold check passed",
    badge: "POLICY GATE",
    color: "bg-blue-50 text-blue-800 border-blue-200",
  },
  {
    step: "05 OUTCOME",
    title: "Reconciled Verification",
    value: "$0.00 AT RISK ➔ RECOVERED",
    detail: "Authoritative revenue truth verified ($199.99 recovered)",
    badge: "VERIFIED RESULT",
    color: "bg-emerald-50 text-emerald-800 border-emerald-300",
  },
];

export function LandingHeroVisual() {
  const [activeIdx, setActiveIdx] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

  useEffect(() => {
    if (!isAutoPlaying) return;
    const interval = setInterval(() => {
      setActiveIdx((prev) => (prev + 1) % STAGES.length);
    }, 3200);
    return () => clearInterval(interval);
  }, [isAutoPlaying]);

  const current = STAGES[activeIdx];

  return (
    <div className="w-full bg-white rounded-2xl border border-stone-300/80 shadow-xl overflow-hidden p-6 sm:p-8 space-y-6">
      {/* Top Machine Status Bar */}
      <div className="flex items-center justify-between border-b border-stone-200 pb-4">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-500 animate-pulse" />
          <span className="font-mono text-xs font-bold tracking-wider text-stone-900 uppercase">
            RECLAIM DECISION ENGINE // INSTRUMENT #1081
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsAutoPlaying(!isAutoPlaying)}
            className="text-[11px] font-mono text-stone-500 hover:text-stone-900 bg-stone-100 px-2.5 py-1 rounded border border-stone-200 cursor-pointer"
          >
            {isAutoPlaying ? "pause animation" : "play animation"}
          </button>
        </div>
      </div>

      {/* Stepper Pipeline Bar */}
      <div className="grid grid-cols-5 gap-1.5 bg-stone-100 p-1.5 rounded-xl border border-stone-200">
        {STAGES.map((st, idx) => {
          const isActive = idx === activeIdx;
          const isPassed = idx < activeIdx;
          return (
            <button
              key={st.step}
              onClick={() => {
                setActiveIdx(idx);
                setIsAutoPlaying(false);
              }}
              className={`py-2 px-2 rounded-lg text-center transition-all cursor-pointer ${
                isActive
                  ? "bg-stone-900 text-white font-semibold shadow-xs"
                  : isPassed
                  ? "bg-stone-200/80 text-stone-800 font-medium"
                  : "text-stone-500 hover:bg-stone-200/40"
              }`}
            >
              <div className="text-[10px] font-mono leading-none tracking-tight">{st.step.split(" ")[0]}</div>
              <div className="text-[11px] font-sans font-bold mt-1 truncate">{st.step.split(" ")[1]}</div>
            </button>
          );
        })}
      </div>

      {/* Active Stage Display Panel */}
      <div className={`p-6 rounded-xl border transition-all duration-300 ${current.color}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase bg-white/80 border border-current/20">
                {current.badge}
              </span>
              <span className="text-xs font-mono font-semibold text-stone-600">{current.step}</span>
            </div>
            <h3 className="text-xl sm:text-2xl font-sans font-bold text-stone-900">{current.title}</h3>
          </div>
          <div className="text-right">
            <div className="text-xl sm:text-3xl font-mono font-black tracking-tight text-stone-900">
              {current.value}
            </div>
          </div>
        </div>
        <p className="text-xs font-mono text-stone-700 mt-3 pt-3 border-t border-current/10">
          {current.detail}
        </p>
      </div>

      {/* Decision Arithmetics Machine Callout */}
      <div className="bg-stone-900 text-white rounded-xl p-5 space-y-3 font-mono text-xs shadow-inner">
        <div className="flex items-center justify-between text-stone-400 border-b border-stone-800 pb-2">
          <span>ECONOMIC ARITHMETIC INSTRUMENT</span>
          <span className="text-emerald-400 font-semibold">FORMULA VERIFIED</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-1">
          <div>
            <span className="text-stone-500 block text-[10px]">RECOVERABLE</span>
            <span className="text-stone-200 font-bold text-sm">$199.99</span>
          </div>
          <div>
            <span className="text-stone-500 block text-[10px]">SUCCESS PROBABILITY</span>
            <span className="text-stone-200 font-bold text-sm">75.0%</span>
          </div>
          <div>
            <span className="text-stone-500 block text-[10px]">INTERVENTION FEE</span>
            <span className="text-stone-200 font-bold text-sm">-$0.50</span>
          </div>
          <div className="bg-stone-800/80 p-2 rounded border border-stone-700">
            <span className="text-rose-400 block text-[10px] font-bold">EXPECTED NET</span>
            <span className="text-emerald-400 font-extrabold text-base">$149.49</span>
          </div>
        </div>
      </div>
    </div>
  );
}
