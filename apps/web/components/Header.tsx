"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

interface HeaderProps {
  mode?: "public" | "authenticated";
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  userEmail?: string | null;
  merchantName?: string | null;
}

export function Header({
  mode = "public",
  activeTab = "operations",
  onTabChange,
  userEmail,
  merchantName = "Demo Merchant Inc.",
}: HeaderProps) {
  const router = useRouter();

  async function handleLogout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // ignore
    }
    router.push("/");
    router.refresh();
  }

  return (
    <header className="border-b border-stone-200/80 bg-[#FAF9F5]/90 backdrop-blur-md px-4 sm:px-8 py-3.5 sticky top-0 z-50 transition-all">
      <div className="mx-auto flex items-center justify-between gap-6 max-w-7xl">
        {/* LEFT: Brand & Primary Navigation */}
        <div className="flex items-center gap-8">
          <Link href={mode === "authenticated" ? "/operations" : "/"} className="flex items-center gap-2.5 group">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-stone-900 text-white font-mono font-bold text-[11px] group-hover:bg-rose-700 transition-colors">
              RC
            </div>
            <div className="flex flex-col">
              <span className="font-mono font-black tracking-wider text-stone-900 text-sm leading-none">
                RECLAIM
              </span>
              <span className="text-[9px] font-sans font-semibold text-stone-400 tracking-wider hidden sm:inline uppercase mt-0.5">
                REVENUE ENGINE
              </span>
            </div>
          </Link>

          {mode === "authenticated" ? (
            <nav className="flex items-center gap-6 text-xs font-sans">
              <Link
                href="/operations"
                onClick={() => onTabChange && onTabChange("operations")}
                className={`py-1 transition-colors relative ${
                  activeTab === "operations"
                    ? "text-stone-900 font-semibold border-b-2 border-stone-900"
                    : "text-stone-600 hover:text-stone-900"
                }`}
              >
                Operations
              </Link>
              <Link
                href="/cases"
                onClick={() => onTabChange && onTabChange("cases")}
                className={`py-1 transition-colors relative ${
                  activeTab === "cases" || activeTab === "case_detail"
                    ? "text-stone-900 font-semibold border-b-2 border-stone-900"
                    : "text-stone-600 hover:text-stone-900"
                }`}
              >
                Cases
              </Link>
              <Link
                href="/engine"
                onClick={() => onTabChange && onTabChange("engine")}
                className={`py-1 transition-colors relative ${
                  activeTab === "engine"
                    ? "text-stone-900 font-semibold border-b-2 border-stone-900"
                    : "text-stone-600 hover:text-stone-900"
                }`}
              >
                Engine
              </Link>
              <Link
                href="/account"
                onClick={() => onTabChange && onTabChange("account")}
                className={`py-1 transition-colors relative ${
                  activeTab === "account"
                    ? "text-stone-900 font-semibold border-b-2 border-stone-900"
                    : "text-stone-600 hover:text-stone-900"
                }`}
              >
                Account
              </Link>
            </nav>
          ) : (
            <nav className="hidden md:flex items-center gap-6 text-xs font-sans font-medium text-stone-600">
              <a href="/#how-it-works" className="hover:text-stone-900 transition-colors">
                How It Works
              </a>
              <a href="/#economic-test" className="hover:text-stone-900 transition-colors">
                The Economic Test
              </a>
              <a href="/#engineering" className="hover:text-stone-900 transition-colors">
                Architecture
              </a>
              <a href="/#differentiation" className="hover:text-stone-900 transition-colors">
                Why RECLAIM
              </a>
            </nav>
          )}
        </div>

        {/* RIGHT: Status / Actions */}
        <div className="flex items-center gap-4 shrink-0 text-xs font-sans">
          {mode === "authenticated" ? (
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-stone-100 border border-stone-200 text-stone-700 font-mono text-[10px]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
                <span className="font-bold tracking-tight">ENGINE ONLINE</span>
              </div>
              <div className="hidden lg:flex flex-col text-right">
                <span className="text-[11px] font-mono font-bold text-stone-900 leading-tight">
                  {userEmail || "operator@reclaim.local"}
                </span>
                <span className="text-[10px] text-stone-400 font-sans leading-none mt-0.5">{merchantName}</span>
              </div>
              <button
                onClick={handleLogout}
                className="text-xs font-sans font-medium text-stone-600 hover:text-stone-900 underline-offset-4 hover:underline transition cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 sm:gap-3">
              <Link
                href="/signin"
                className="px-3.5 py-1.5 text-xs font-semibold text-stone-700 hover:text-stone-900 hover:bg-stone-100 rounded-md transition"
              >
                Sign In
              </Link>
              <Link
                href="/signup"
                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-stone-900 hover:bg-rose-700 rounded-md shadow-xs transition"
              >
                Enter RECLAIM
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
