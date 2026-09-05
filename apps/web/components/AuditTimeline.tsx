"use client";

import { AuditEvent } from "@/lib/types";

interface AuditTimelineProps {
  events: AuditEvent[];
}

export function AuditTimeline({ events }: AuditTimelineProps) {
  return (
    <div className="rounded-2xl border border-stone-300/80 bg-white p-6 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-stone-200/80 pb-4">
        <div>
          <h2 className="text-xl font-serif-editorial font-bold text-stone-900 tracking-tight">
            Forensic Audit Ledger
          </h2>
          <p className="text-xs text-stone-500 font-sans">
            Immutable operational audit event trail.
          </p>
        </div>
        <span className="text-[10px] font-mono font-bold text-stone-500 bg-stone-100 px-2.5 py-1 rounded-md border border-stone-200 uppercase">
          {events.length} Events Logged
        </span>
      </div>

      <div className="relative pl-5 space-y-5 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-stone-200">
        {events.map((ev) => (
          <div key={ev.id} className="relative space-y-1">
            <span className="absolute -left-[22px] top-1.5 h-3 w-3 rounded-full bg-stone-900 ring-4 ring-white" />
            <div className="flex items-center justify-between text-xs font-sans">
              <span className="font-mono font-bold text-stone-900">{ev.event_type}</span>
              <span className="text-stone-400 font-mono text-[10px]">
                {ev.occurred_at ? new Date(ev.occurred_at).toLocaleTimeString() : "Just now"}
              </span>
            </div>
            {ev.message && (
              <p className="text-xs text-stone-700 font-sans leading-relaxed">
                {ev.message}
              </p>
            )}
            <div className="text-[10px] font-mono text-stone-500 flex items-center gap-2 pt-0.5">
              <span>Actor: <strong className="text-stone-800 font-sans font-semibold">{ev.actor || "system"}</strong></span>
              <span className="text-stone-300">•</span>
              <span>Status: <strong className="text-stone-900 uppercase font-bold">{ev.status || "COMPLETED"}</strong></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
