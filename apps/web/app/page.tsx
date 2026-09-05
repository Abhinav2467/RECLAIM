import Link from "next/link";
import { Header } from "@/components/Header";
import { LandingHeroVisual } from "@/components/LandingHeroVisual";
import { EconomicTestCalculator } from "@/components/EconomicTestCalculator";
import {
  NarrativeProblemSection,
  NarrativeQuestionSection,
  NarrativeEngineSection,
  ActionCompetitionSection,
  EnginePreviewSection,
  StoppingRuleSection,
  VerificationSection,
  EngineeringCredibilitySection,
  DifferentiationSection,
  FinalCTASection,
} from "@/components/LandingSections";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#FAF9F5] text-stone-900 flex flex-col font-sans antialiased">
      {/* Global Public Header */}
      <Header mode="public" />

      <main className="flex-1">
        {/* HERO SECTION */}
        <section className="py-16 sm:py-24 border-b border-stone-200">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 space-y-12">
            <div className="max-w-4xl mx-auto text-center space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 border border-stone-200 text-stone-700 text-xs font-mono font-semibold">
                <span className="h-2 w-2 rounded-full bg-rose-600 animate-pulse" />
                REVENUE EVALUATION, CONTEXTUAL LOGIC & INTELLIGENT MONETARY RECOVERY
              </div>

              <h1 className="text-4xl sm:text-6xl lg:text-7xl font-serif-editorial font-bold text-stone-900 tracking-tight leading-[1.1]">
                REVENUE SHOULD BE RECOVERED. <br className="hidden sm:inline" />
                <span className="italic text-rose-800">NOT CHASED.</span>
              </h1>

              <p className="text-lg sm:text-xl text-stone-600 max-w-3xl mx-auto leading-relaxed font-sans font-normal">
                RECLAIM is a merchant revenue-recovery decision engine. It evaluates recoverable revenue economically, applies policy constraints, executes bounded actions, and verifies financial outcomes — and knows when <strong className="text-stone-900 font-semibold">NOT to act</strong>.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
                <Link
                  href="/signup"
                  className="w-full sm:w-auto px-8 py-3.5 text-sm font-semibold text-white bg-stone-900 hover:bg-rose-700 rounded-lg shadow-md hover:shadow-lg transition-all"
                >
                  ENTER RECLAIM
                </Link>
                <a
                  href="#how-it-works"
                  className="w-full sm:w-auto px-8 py-3.5 text-sm font-semibold text-stone-700 hover:text-stone-900 bg-white hover:bg-stone-100 rounded-lg border border-stone-300/80 transition-all"
                >
                  EXPLORE THE ENGINE
                </a>
              </div>
            </div>

            {/* Interactive Hero Visual */}
            <div className="max-w-5xl mx-auto">
              <LandingHeroVisual />
            </div>
          </div>
        </section>

        {/* NARRATIVE SCROLL STORYTELLING SECTIONS */}
        <NarrativeProblemSection />
        <NarrativeQuestionSection />
        <NarrativeEngineSection />

        <section id="economic-test" className="py-16 sm:py-24 border-b border-stone-200">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <EconomicTestCalculator />
          </div>
        </section>

        <ActionCompetitionSection />
        <EnginePreviewSection />
        <StoppingRuleSection />
        <VerificationSection />
        <EngineeringCredibilitySection />
        <DifferentiationSection />
        <FinalCTASection />
      </main>

      {/* FOOTER */}
      <footer className="bg-stone-950 text-stone-400 py-12 border-t border-stone-800 text-xs font-sans">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-white text-sm">RECLAIM</span>
            <span>// Merchant Revenue Recovery Decision System</span>
          </div>
          <div className="flex items-center gap-6 font-mono text-[11px]">
            <span>POSTGRESQL</span>
            <span>LANGGRAPH</span>
            <span>RAZORPAY ADAPTER</span>
            <span>SSE</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
