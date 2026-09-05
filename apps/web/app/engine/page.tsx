"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { EngineView } from "@/components/EngineView";
import { DemoControls } from "@/components/DemoControls";
import { RecoveryCaseDetails, MerchantRecoveryOverviewResponse } from "@/lib/types";
import { useRecoveryCaseStream } from "@/lib/useRecoveryCaseStream";

function EngineContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [user, setUser] = useState<{ email: string; merchant_name: string; merchant_id: number } | null>(null);
  const [overview, setOverview] = useState<MerchantRecoveryOverviewResponse | null>(null);
  const [caseId, setCaseId] = useState<number | null>(null);
  const [caseData, setCaseData] = useState<RecoveryCaseDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [initialReplay, setInitialReplay] = useState<boolean>(false);

  // 1. Verify authenticated user identity via /api/auth/me
  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch("/api/auth/me");
        if (!res.ok) {
          setUser(null);
        } else {
          const data = await res.json();
          if (data.authenticated && data.user) {
            setUser({
              email: data.user.email,
              merchant_name: data.user.merchant_name,
              merchant_id: data.user.merchant_id,
            });
          }
        }
      } catch {
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    }
    checkAuth();
  }, []);

  // 2. Load specific case details when requested
  const loadCase = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/recovery-cases/${id}`);
      if (!res.ok) {
        if (res.status === 404) {
          setCaseData(null);
          return;
        }
        const errJson = await res.json().catch(() => ({ detail: "Failed to load recovery case" }));
        throw new Error(errJson.detail || `Server error (${res.status})`);
      }
      const data: RecoveryCaseDetails = await res.json();
      setCaseData(data);
      setCaseId(data.case_id);
    } catch (e: any) {
      setError(e.message || "Failed to load recovery case details");
    } finally {
      setLoading(false);
    }
  }, []);

  // 3. Fetch authoritative merchant recovery overview read model
  const loadOverview = useCallback(async () => {
    try {
      const res = await fetch("/api/recovery/overview");
      if (!res.ok) return;
      const data: MerchantRecoveryOverviewResponse = await res.json();
      setOverview(data);

      const paramCaseId = searchParams.get("case_id");
      const paramReplay = searchParams.get("replay");

      if (paramReplay === "true") {
        setInitialReplay(true);
      }

      if (paramCaseId && !isNaN(Number(paramCaseId))) {
        const targetId = Number(paramCaseId);
        await loadCase(targetId);
      } else if (data.cases && data.cases.length > 0) {
        // Default to first case if none specified in URL
        await loadCase(data.cases[0].case_id);
      }
    } catch {
      // Ignore background sync error
    }
  }, [searchParams, loadCase]);

  // 4. Live SSE stream subscription for active case audit events
  useRecoveryCaseStream({
    caseId,
    onEvent: () => {
      if (caseId) {
        loadCase(caseId);
      }
      loadOverview();
    },
    enabled: !!caseId,
  });

  async function handleStartDemo() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/demo/recovery-scenario", { method: "POST" });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: "Demo setup failed" }));
        throw new Error(errJson.detail || "Demo endpoint returned an error");
      }
      const data = await res.json();
      if (data.case_id) {
        await loadCase(data.case_id);
        await loadOverview();
      }
    } catch (e: any) {
      setError(e.message || "Failed to initialize demo scenario");
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#FAF9F5] flex items-center justify-center font-mono text-xs text-stone-500">
        Initializing RECLAIM Decision Engine...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F5] text-stone-900 flex flex-col font-sans antialiased">
      <Header
        mode="authenticated"
        activeTab="engine"
        userEmail={user?.email}
        merchantName={user?.merchant_name}
      />

      <main className="flex-1 mx-auto max-w-7xl w-full px-4 sm:px-6 py-6 space-y-6">
        {/* Error Banner */}
        {error && (
          <div className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-xs font-mono text-rose-800 flex items-center justify-between shadow-2xs">
            <div className="flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-rose-600 hover:text-rose-900 font-bold ml-4 px-2 py-1 rounded hover:bg-rose-100 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Demo Controls Utility Bar */}
        <DemoControls
          currentStatus={caseData?.status || null}
          currentCaseId={caseData?.case_id || null}
          onScenarioUpdate={async (id) => {
            await loadCase(id);
            await loadOverview();
          }}
          onError={(msg) => setError(msg)}
        />

        {/* Live Engine Visual Operating Model View */}
        <EngineView
          overview={overview}
          selectedCase={caseData}
          onSelectCase={(id) => {
            loadCase(id);
            router.push(`/engine?case_id=${id}`);
          }}
          onStartDemo={handleStartDemo}
          loading={loading}
          initialReplay={initialReplay}
        />
      </main>
    </div>
  );
}

export default function EnginePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#FAF9F5] flex items-center justify-center font-mono text-xs text-stone-500">
        Initializing RECLAIM Decision Engine...
      </div>
    }>
      <EngineContent />
    </Suspense>
  );
}
