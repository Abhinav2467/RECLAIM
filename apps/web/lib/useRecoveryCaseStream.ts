"use client";

import { useEffect, useRef } from "react";

interface UseRecoveryCaseStreamOptions {
  caseId: number | null;
  onEvent?: () => void;
  enabled?: boolean;
}

export function useRecoveryCaseStream({ caseId, onEvent, enabled = true }: UseRecoveryCaseStreamOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!caseId || !enabled) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    // Prevent duplicate subscriptions to the same active stream
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const url = `/api/recovery-cases/${caseId}/stream`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.addEventListener("audit_event", () => {
      if (onEvent) {
        onEvent();
      }
    });

    es.addEventListener("terminal", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (data.terminal) {
          if (onEvent) {
            onEvent();
          }
          es.close();
          eventSourceRef.current = null;
        }
      } catch {
        es.close();
        eventSourceRef.current = null;
      }
    });

    es.onerror = () => {
      // Close EventSource on error to avoid uncontrolled infinite reconnect loops
      es.close();
      eventSourceRef.current = null;
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [caseId, enabled, onEvent]);
}
