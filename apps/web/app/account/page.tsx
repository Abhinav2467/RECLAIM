"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ id: number; email: string; merchant_name: string; merchant_id: number; created_at?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAccount() {
      try {
        const res = await fetch("/api/auth/me");
        if (!res.ok) {
          router.push("/signin");
          return;
        }
        const data = await res.json();
        if (data.authenticated && data.user) {
          setUser(data.user);
        } else {
          router.push("/signin");
        }
      } catch {
        setError("Failed to load account details");
      } finally {
        setLoading(false);
      }
    }
    loadAccount();
  }, [router]);

  async function handleLogout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // ignore
    }
    router.push("/");
    router.refresh();
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF9F5] flex items-center justify-center font-mono text-xs text-stone-500">
        Loading account details...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F5] text-stone-900 flex flex-col font-sans antialiased">
      <Header mode="authenticated" activeTab="account" userEmail={user?.email} merchantName={user?.merchant_name} />

      <main className="flex-1 mx-auto max-w-3xl w-full px-4 sm:px-6 py-12 space-y-6 animate-fade-in-up">
        <div className="bg-white rounded-2xl border border-stone-300/80 p-6 sm:p-10 shadow-xl space-y-8">
          <div className="space-y-2 border-b border-stone-200/80 pb-5">
            <span className="text-[10px] font-mono font-bold tracking-widest text-stone-500 uppercase flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-700" />
              AUTHENTICATED OPERATOR IDENTITY
            </span>
            <h1 className="text-3xl sm:text-4xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Account & Security Context
            </h1>
            <p className="text-xs text-stone-600 font-sans">
              Authoritative merchant session assurance, operator identity, and platform isolation details.
            </p>
          </div>

          {error && (
            <div className="rounded-lg border border-rose-300 bg-rose-50 p-4 text-xs font-mono text-rose-800 flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {user && (
            <div className="space-y-6 font-sans text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-stone-50/80 p-5 rounded-xl border border-stone-200/80 space-y-1.5">
                  <span className="text-[10px] font-mono text-stone-400 font-bold uppercase tracking-wider">OPERATOR EMAIL</span>
                  <div className="font-mono text-base font-bold text-stone-900">{user.email}</div>
                  <div className="text-[10px] text-stone-500 font-sans">Authenticated Operator Session</div>
                </div>

                <div className="bg-stone-50/80 p-5 rounded-xl border border-stone-200/80 space-y-1.5">
                  <span className="text-[10px] font-mono text-stone-400 font-bold uppercase tracking-wider">ASSOCIATED MERCHANT</span>
                  <div className="font-mono text-base font-bold text-stone-900">{user.merchant_name}</div>
                  <div className="text-[10px] font-mono text-stone-500">Merchant ID: <strong className="text-stone-800">#{user.merchant_id}</strong></div>
                </div>
              </div>

              <div className="bg-stone-900 text-white p-6 rounded-xl border border-stone-800 space-y-3 shadow-md">
                <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-widest block border-b border-stone-800 pb-2">
                  SECURITY ASSURANCE & PLATFORM ISOLATION
                </span>
                <ul className="space-y-2 font-mono text-[11px] text-stone-300 pt-1">
                  <li className="flex items-center gap-2">
                    <span className="text-emerald-400 font-bold">✓</span> HTTP-only secure cookie session token (`reclaim_session`)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-emerald-400 font-bold">✓</span> Passwords hashed via PBKDF2-HMAC-SHA256 (100k iterations)
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-emerald-400 font-bold">✓</span> Operational API endpoints strictly scoped to Merchant #{user.merchant_id}
                  </li>
                </ul>
              </div>

              <div className="pt-4 flex justify-between items-center border-t border-stone-200">
                <button
                  onClick={() => router.push("/operations")}
                  className="px-4 py-2 text-xs font-sans font-bold text-stone-700 bg-stone-100 hover:bg-stone-200 rounded-lg border border-stone-300 transition cursor-pointer"
                >
                  ← Return to Operations Console
                </button>

                <button
                  onClick={handleLogout}
                  className="px-4 py-2 text-xs font-sans font-bold text-white bg-stone-900 hover:bg-rose-700 rounded-lg shadow-xs transition cursor-pointer"
                >
                  Sign Out of Session
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
