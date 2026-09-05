"use client";

import { useState } from "react";

export function EconomicTestCalculator() {
  const [amount, setAmount] = useState<number>(199.99);
  const [probability, setProbability] = useState<number>(75);
  const [cost, setCost] = useState<number>(0.50);

  const gross = (amount * (probability / 100));
  const net = gross - cost;
  const isViable = net > 0;

  return (
    <div className="bg-white rounded-2xl border border-stone-300/80 p-6 sm:p-8 shadow-lg space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-stone-200 pb-4">
        <div>
          <span className="text-[11px] font-mono font-bold tracking-widest text-stone-500 uppercase">
            NARRATIVE 04 // THE ECONOMIC TEST
          </span>
          <h3 className="text-xl sm:text-2xl font-sans font-bold text-stone-900 mt-1">
            Interactive Economic Evaluation Instrument
          </h3>
        </div>
        <div className={`px-3 py-1.5 rounded-lg border font-mono text-xs font-bold ${
          isViable ? "bg-emerald-50 text-emerald-800 border-emerald-300" : "bg-rose-50 text-rose-800 border-rose-300"
        }`}>
          {isViable ? "DECISION: EXECUTE RECOVERY" : "DECISION: NO_ACTION (CAPITAL PRESERVED)"}
        </div>
      </div>

      {/* Input Sliders */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
          <div className="flex justify-between text-xs font-sans font-semibold text-stone-700">
            <span>Recoverable Amount</span>
            <span className="font-mono text-stone-900 font-bold">${amount.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="10"
            max="1000"
            step="5"
            value={amount}
            onChange={(e) => setAmount(parseFloat(e.target.value))}
            className="w-full accent-stone-900 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] font-mono text-stone-400">
            <span>$10.00</span>
            <span>$1,000.00</span>
          </div>
        </div>

        <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
          <div className="flex justify-between text-xs font-sans font-semibold text-stone-700">
            <span>Success Probability</span>
            <span className="font-mono text-stone-900 font-bold">{probability}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={probability}
            onChange={(e) => setProbability(parseInt(e.target.value))}
            className="w-full accent-stone-900 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] font-mono text-stone-400">
            <span>0%</span>
            <span>100%</span>
          </div>
        </div>

        <div className="space-y-2 bg-stone-50 p-4 rounded-xl border border-stone-200">
          <div className="flex justify-between text-xs font-sans font-semibold text-stone-700">
            <span>Intervention Fee</span>
            <span className="font-mono text-stone-900 font-bold">${cost.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="60"
            step="0.50"
            value={cost}
            onChange={(e) => setCost(parseFloat(e.target.value))}
            className="w-full accent-stone-900 cursor-pointer"
          />
          <div className="flex justify-between text-[10px] font-mono text-stone-400">
            <span>$0.00</span>
            <span>$60.00</span>
          </div>
        </div>
      </div>

      {/* Arithmetic Resolution Stream */}
      <div className="bg-stone-900 text-white rounded-xl p-6 font-mono space-y-4 shadow-inner">
        <div className="text-xs font-bold text-stone-400 uppercase tracking-wider border-b border-stone-800 pb-2">
          MATHEMATICAL PROOF & RESOLUTION
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs">
          <div className="bg-stone-800/60 p-3 rounded border border-stone-700">
            <span className="text-stone-400 text-[10px] block">01 RECOVERABLE AMOUNT</span>
            <span className="text-stone-100 text-base font-bold">${amount.toFixed(2)}</span>
          </div>
          <div className="bg-stone-800/60 p-3 rounded border border-stone-700">
            <span className="text-stone-400 text-[10px] block">02 EXPECTED GROSS</span>
            <span className="text-stone-100 text-base font-bold">${gross.toFixed(2)}</span>
            <span className="text-[10px] text-stone-400 block mt-0.5">(${amount.toFixed(2)} × {probability}%)</span>
          </div>
          <div className="bg-stone-800/60 p-3 rounded border border-stone-700">
            <span className="text-stone-400 text-[10px] block">03 INTERVENTION COST</span>
            <span className="text-rose-400 text-base font-bold">-${cost.toFixed(2)}</span>
          </div>
          <div className={`p-3 rounded border ${
            isViable ? "bg-emerald-950/80 border-emerald-500 text-emerald-300" : "bg-rose-950/80 border-rose-500 text-rose-300"
          }`}>
            <span className="text-[10px] block font-bold uppercase tracking-wider">04 EXPECTED NET</span>
            <span className="text-lg font-black">${net.toFixed(2)}</span>
          </div>
        </div>

        <div className="text-[11px] text-stone-400 pt-2 border-t border-stone-800 flex items-center justify-between">
          <span>{isViable ? "Positive expected net recovery exceeds cost floor." : "Expected net recovery is non-positive. Stopping rule enforced."}</span>
          <span className="font-bold text-stone-200">{isViable ? "ACTION APPROVED" : "NO_ACTION EXECUTED"}</span>
        </div>
      </div>
    </div>
  );
}
