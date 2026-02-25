import SiteHeader from "@/components/layout/SiteHeader";
import Link from "next/link";

export default function MethodologyPage() {
  return (
    <main className="min-h-screen bg-[#070A0F] text-[#E9EEF5]">
      <SiteHeader />
      <section className="mx-auto max-w-4xl px-6 pt-10 pb-20">
        <h1 className="text-4xl font-extrabold">
          Methodology: <span className="text-[#F5B942]">Process Over Noise</span>
        </h1>

        <p className="mt-4 text-white/70">
          Built on Data. Driven by Edge.
        </p>
        <p className="mt-2 text-white/70">
          We don&apos;t sell picks. We build models.
        </p>
        <p className="mt-4 text-white/70">
          Every projection, prop, and edge on this platform comes from a structured data pipeline designed to identify mispriced numbers in the betting market.
        </p>
        <p className="mt-2 text-white/70">
          Sportsbooks price games. We price them too. Where there&apos;s separation — there&apos;s opportunity.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">1. Model vs. Market</h2>
        <p className="mt-3 text-white/70">
          At the core of our process is one principle: Expected Value (EV) over Emotion.
        </p>
        <p className="mt-2 text-white/70">
          For every game, prop, or total:
        </p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Our model generates a projection</li>
          <li>We compare it to the sportsbook line</li>
          <li>We calculate the implied probability</li>
          <li>We determine whether the edge clears a defined threshold</li>
        </ul>
        <p className="mt-3 text-white/70">
          If it doesn&apos;t meet the threshold — it doesn&apos;t make the board.
        </p>
        <p className="mt-2 text-white/70">
          No &quot;locks.&quot; No vibes. No chasing. Just math.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">2. Data Inputs</h2>
        <p className="mt-3 text-white/70">
          Our models integrate:
        </p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Historical performance data</li>
          <li>Advanced metrics (xStats, wOBA, ISO, K%, etc.)</li>
          <li>Matchup splits (handedness, home/away, situational)</li>
          <li>Park factors and environmental adjustments</li>
          <li>Line movement tracking</li>
          <li>Opening vs closing line comparisons</li>
        </ul>
        <p className="mt-4 text-white/70">
          For MLB specifically, we build from the plate appearance level upward — projecting:
        </p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Strikeout probability</li>
          <li>Walk probability</li>
          <li>Hit distribution</li>
          <li>Total bases</li>
          <li>Run expectancy</li>
        </ul>
        <p className="mt-3 text-white/70">
          These simulations aggregate into: Player props, team totals, run lines, moneyline projections.
        </p>
        <p className="mt-2 text-white/70">
          The model does the heavy lifting — the board shows the edge.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">3. Edge Thresholds</h2>
        <p className="mt-3 text-white/70">
          Not every difference between our projection and the sportsbook number is actionable.
        </p>
        <p className="mt-2 text-white/70">We apply:</p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Minimum EV thresholds</li>
          <li>Volatility adjustments</li>
          <li>Market liquidity considerations</li>
          <li>Contextual filters</li>
        </ul>
        <p className="mt-3 text-white/70">
          The goal isn&apos;t to bet more. The goal is to bet better.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">4. Tracking & Accountability</h2>
        <p className="mt-3 text-white/70">Transparency matters.</p>
        <p className="mt-2 text-white/70">We track:</p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Model projection vs sportsbook open</li>
          <li>Model projection vs closing line</li>
          <li>Actual result</li>
          <li>Expected Value at time of bet</li>
        </ul>
        <p className="mt-3 text-white/70">
          Closing Line Value (CLV) is monitored — but EV is the core driver.
        </p>
        <p className="mt-2 text-white/70">
          Most bettors bet at close. We evaluate against both.
        </p>
        <p className="mt-2 text-white/70">
          Performance isn&apos;t a screenshot. It&apos;s recorded. And the system is profitable.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">5. Discipline Philosophy</h2>
        <p className="mt-3 text-white/70">
          The biggest leak in sports betting isn&apos;t information. It&apos;s behavior.
        </p>
        <p className="mt-2 text-white/70">
          This platform is built for: Structured bettors, process-driven users, people who want to level up.
        </p>
        <p className="mt-2 text-white/70">We actively educate against:</p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>9-leg parlays</li>
          <li>Chasing losses</li>
          <li>Overexposure to heavy favorites</li>
          <li>Emotional betting</li>
        </ul>
        <p className="mt-3 text-white/70">
          The goal isn&apos;t short-term dopamine. It&apos;s long-term edge.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">6. Continuous Model Improvement</h2>
        <p className="mt-3 text-white/70">Models are not static.</p>
        <p className="mt-2 text-white/70">We:</p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>Backtest historical lines</li>
          <li>Evaluate feature importance</li>
          <li>Re-weight inputs</li>
          <li>Tune variance controls</li>
          <li>Expand feature sets</li>
        </ul>
        <p className="mt-3 text-white/70">
          The edge evolves with the market. So do we.
        </p>

        <hr className="my-8 border-white/20" />

        <h2 className="text-2xl font-bold text-[#F5B942] mt-8">What You&apos;re Using</h2>
        <p className="mt-3 text-white/70">
          You&apos;re not buying picks. You&apos;re using:
        </p>
        <ul className="mt-2 list-disc list-inside space-y-1 text-white/70">
          <li>A projection engine</li>
          <li>A simulation system</li>
          <li>A discipline framework</li>
          <li>A profitable process</li>
        </ul>
        <p className="mt-3 text-white/70">
          Built on data. Driven by edge.
        </p>

        <div className="mt-8">
          <Link
            href="/insights"
            className="inline-flex rounded-xl bg-[#F5B942] px-5 py-3 text-black font-semibold shadow"
          >
            Read Insights
          </Link>
        </div>
      </section>
    </main>
  );
}
