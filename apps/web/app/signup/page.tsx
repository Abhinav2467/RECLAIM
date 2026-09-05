"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";

export default function SignUpPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [merchantName, setMerchantName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please fill in all required fields");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters long");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          password: password.trim(),
          merchant_name: merchantName.trim() || "Demo Merchant Inc.",
        }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        let msg = "";
        if (data && data.detail) {
          if (typeof data.detail === "string") {
            msg = data.detail;
          } else if (Array.isArray(data.detail) && data.detail.length > 0) {
            const first = data.detail[0];
            msg = typeof first === "string" ? first : first?.msg || "Invalid registration input";
          } else if (typeof data.detail === "object") {
            msg = data.detail.msg || JSON.stringify(data.detail);
          }
        } else if (data && data.message) {
          msg = data.message;
        }

        if (!msg) {
          if (res.status === 502 || res.status === 503) {
            msg = "RECLAIM engine is unavailable. Please ensure the FastAPI server is running on port 8000.";
          } else if (res.status === 400) {
            msg = "An account with this email already exists or registration details are invalid.";
          } else if (res.status === 500) {
            msg = "Internal server error occurred. Please try again or check backend logs.";
          } else {
            msg = "Failed to create account. Please verify your details.";
          }
        }
        throw new Error(msg);
      }

      // Successful registration -> Redirect to Operations Console
      router.push("/operations");
      router.refresh();
    } catch (err: any) {
      setError(err.message || "Failed to create account");
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
              REGISTRATION // NEW MERCHANT OPERATOR
            </div>
            <h1 className="text-3xl font-serif-editorial font-bold text-stone-900 tracking-tight">
              Create RECLAIM Account
            </h1>
            <p className="text-xs text-stone-600 leading-relaxed">
              Register a merchant operator identity to initialize your autonomous decision engine.
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
                Merchant / Business Name
              </label>
              <input
                type="text"
                value={merchantName}
                onChange={(e) => setMerchantName(e.target.value)}
                placeholder="Acme Payments Corp"
                className="w-full px-3.5 py-2.5 rounded-lg border border-stone-300 text-sm focus:outline-none focus:ring-2 focus:ring-stone-900 focus:border-stone-900 transition"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-sans font-semibold text-stone-700 block">
                Operator Email Address *
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
                  Password (min 6 chars) *
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
                minLength={6}
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
              {loading ? "Registering..." : "Create Account & Enter RECLAIM"}
            </button>
          </form>

          <div className="pt-4 border-t border-stone-200/80 text-center text-xs text-stone-500">
            Already registered?{" "}
            <Link href="/signin" className="font-bold text-stone-900 hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
