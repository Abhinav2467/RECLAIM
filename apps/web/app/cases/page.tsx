"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { CasesView } from "@/components/CasesView";
import { RecoveryCasePanel } from "@/components/RecoveryCasePanel";
import { DecisionPanel } from "@/components/DecisionPanel";
import { AuditTimeline } from "@/components/AuditTimeline";
import { StatusPipeline } from "@/components/StatusPipeline";
import { DemoControls } from "@/components/DemoControls";
import { RecoveryCaseDetails, MerchantRecoveryOverviewResponse } from "@/lib/types";
import { useRecoveryCaseStream } from "@/lib/useRecoveryCaseStream";

function CasesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [user, setUser] = useState<{ email: string; merchant_name: string; merchant_id: number } | null>(null);
  const [overview, setOverview] = useState<MerchantRecoveryOverviewResponse | null>(null);
  const [caseId, setCaseId] = useState<number | null>(null);
  const [caseData, setCaseData] = useState<RecoveryCaseDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDetail, setViewingDetail] = useState(false);

  // 1. Verify user identity
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

  // 2. Load case detail
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

  // 3. Overview read model
  const loadOverview = useCallback(async () => {
    try {
      const res = await fetch("/api/recovery/overview");
      if (!res.ok) return;
      const data: MerchantRecoveryOverviewResponse = await res.json();
      setOverview(data);

      // Handle search parameter ?case_id=X
      const paramCaseId = searchParams.get("case_id");
      if (paramCaseId && !isNaN(Number(paramCaseId))) {
        const targetId = Number(paramCaseId);
        await loadCase(targetId);
        setViewingDetail(true);
      }
    } catch {
      // Ignore sync error
    }
  }, [searchParams, loadCase]);

  // 4. SSE Subscription
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
        setViewingDetail(true);
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
        Loading Recovery Cases...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F5] text-stone-900 flex flex-col font-sans antialiased">
      <Header
        mode="authenticated"
        activeTab="cases"
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

        {/* Subordinate Demo Utility Toolbar */}
        <DemoControls
          currentStatus={caseData?.status || null}
          currentCaseId={caseData?.case_id || null}
          onScenarioUpdate={async (id) => {
            await loadCase(id);
            await loadOverview();
          }}
          onError={(msg) => setError(msg)}
        />

        {/* View Switch: Cases List vs Case Detail Experience */}
        {viewingDetail && caseData ? (
          <div className="space-y-6 animate-in fade-in duration-200">
            <div className="flex items-center justify-between border-b border-stone-200/80 pb-3">
              <button
                onClick={() => {
                  setViewingDetail(false);
                  router.push("/cases");
                }}
                className="inline-flex items-center gap-1.5 text-xs font-sans font-bold text-stone-600 hover:text-stone-900 px-3 py-1 rounded-lg hover:bg-stone-200/60 transition cursor-pointer"
              >
                ← Back to Cases List
              </button>
              <div className="text-xs font-mono text-stone-500">
                Case #{caseData.case_id} // {caseData.status}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <div className="lg:col-span-7 space-y-6">
                <RecoveryCasePanel caseData={caseData} />
                <DecisionPanel caseData={caseData} />
              </div>
              <div className="lg:col-span-5 space-y-6">
                <StatusPipeline status={caseData.status} />
                <AuditTimeline events={caseData.audit_events || []} />
              </div>
            </div>
          </div>
        ) : (
          <CasesView
            overview={overview}
            onSelectCase={async (id) => {
              await loadCase(id);
              setViewingDetail(true);
            }}
            onStartDemo={handleStartDemo}
            loading={loading}
          />
        )}
      </main>
    </div>
  );
}

export default function CasesPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[#FAF9F5] flex items-center justify-center font-mono text-xs text-stone-500">
        Loading Recovery Cases...
      </div>
    }>
      <CasesContent />
    </Suspense>
  );
}
