"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";

export default function SignInPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please enter both email and password");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password: password.trim() }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        let msg = "Invalid email or password";
        if (data && data.detail) {
          if (typeof data.detail === "string") {
            msg = data.detail;
          } else if (Array.isArray(data.detail) && data.detail.length > 0) {
            msg = data.detail[0]?.msg || "Invalid input";
          } else if (typeof data.detail === "object") {
            msg = JSON.stringify(data.detail);
          }
        } else if (data && data.message) {
          msg = data.message;
        } else if (res.status === 502 || res.status === 503) {
          msg = "Backend server is offline. Please ensure FastAPI server is running on port 8000.";
        }
        throw new Error(msg);
      }

      // Successful login -> Redirect to Operations Console
      router.push("/operations");
      router.refresh();
    } catch (err: any) {
      setError(err.message || "Failed to sign in");
      setLoading(false);
    }

  }

  return (
    <div className="min-h-screen bg-[#FAF9F5] text-stone-900 flex flex-col font-sans antialiased">
      <Header mode="public" />

      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 my-12 animate-fade-in-up">
        <div className="w-full max-w-md bg-white rounded-2xl border border-stone-300/80 p-8 sm:p-10 shadow-xl space-y-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded bg-stone-100 border border-stone-200 text-[10px] font-mono font-bold text-stone-700 uppercase tracking-wider">
              AUTHENTICATION // OPERATOR ACCESS
            </div>
            <h1 className="text-3xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Sign In to RECLAIM
            </h1>
            <p className="text-xs text-stone-600 leading-relaxed">
              Enter your merchant operator credentials to access revenue operations control.
            </p>
          </div>

          {error && (
            <div className="rounded-lg border border-rose-300 bg-rose-50 p-3.5 text-xs font-mono text-rose-800 flex items-start gap-2">
              <span className="shrink-0">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-sans font-semibold text-stone-700 block">
                Operator Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@merchant.com"
                className="w-full px-3.5 py-2.5 rounded-lg border border-stone-300 text-sm focus:outline-none focus:ring-2 focus:ring-stone-900 focus:border-stone-900 transition"
              />
            </div>

            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <label className="text-xs font-sans font-semibold text-stone-700 block">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-[11px] font-mono text-stone-500 hover:text-stone-900 cursor-pointer"
                >
                  {showPassword ? "hide" : "show"}
                </button>
              </div>
              <input
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-3.5 py-2.5 rounded-lg border border-stone-300 text-sm focus:outline-none focus:ring-2 focus:ring-stone-900 focus:border-stone-900 transition"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg bg-stone-900 hover:bg-rose-700 text-white font-bold text-xs uppercase tracking-wider shadow-md transition-all cursor-pointer disabled:opacity-50"
            >
              {loading ? "Authenticating..." : "Sign In to Console"}
            </button>
          </form>

          <div className="pt-4 border-t border-stone-200/80 text-center text-xs text-stone-500">
            Don't have an operator account?{" "}
            <Link href="/signup" className="font-bold text-stone-900 hover:underline">
              Create Account
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
