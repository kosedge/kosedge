import Link from "next/link";
import { getSport } from "@/lib/sports";

const SPORT_CONTEXT_LABELS: Record<
  string,
  { drivers: string; execution: string; risk: string }
> = {
  nfl: {
    drivers: "key numbers, pressure rate, and explosive pass prevention",
    execution: "key-number timing and injury finalization",
    risk: "late injury designations and weather",
  },
  cfb: {
    drivers: "tempo divergence, havoc profile, and red-zone efficiency",
    execution: "market-limit timing and lineup confirmation",
    risk: "depth-chart volatility and weather",
  },
  nba: {
    drivers: "pace environment, rim pressure, and rotation depth",
    execution: "availability-aware repricing windows",
    risk: "late scratches and fatigue",
  },
  wnba: {
    drivers: "usage concentration, turnover control, and transition profile",
    execution: "book depth checks and travel-aware timing",
    risk: "rotation compression and guard availability",
  },
  mlb: {
    drivers: "starter fit, bullpen leverage, and park-adjusted run context",
    execution: "lineup-card timing and bullpen usage tracking",
    risk: "late scratches and wind shifts",
  },
  nhl: {
    drivers: "goaltender quality, five-on-five xG profile, and special teams",
    execution: "goalie confirmation and totals timing",
    risk: "goalie swaps and schedule congestion",
  },
  ncaam: {
    drivers: "tempo control, rebounding leverage, and foul environment",
    execution: "late steam handling and lineup validation",
    risk: "rotation volatility and whistle variance",
  },
};

export default function MatchupPage({
  params,
}: {
  params: { sport: string; date: string; slug: string };
}) {
  const sport = getSport(params.sport);
  const sportName = sport?.fullName ?? params.sport.toUpperCase();
  const context = SPORT_CONTEXT_LABELS[params.sport];
  const hasSportTemplate = Boolean(context);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Link
        href={`/pro/${params.sport}/slate/${params.date}`}
        className="inline-flex items-center gap-2 text-sm text-kos-gold/90 hover:text-kos-gold"
      >
        ← Back to {sportName} slate
      </Link>
      <h2 className="mt-4 text-2xl font-semibold text-kos-text">{sportName} Matchup</h2>
      <p className="mt-2 text-kos-text/70">
        {sportName} · {params.date} · {params.slug}
      </p>

      <div className="mt-8 grid gap-6">
        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h3 className="text-lg font-semibold">Fair Lines vs Market</h3>
          <p className="mt-2 text-kos-text/80">
            {hasSportTemplate
              ? `Premium placeholder: ${sportName} fair-line and best-price table will publish once validated feeds are available.`
              : "Premium placeholder: model reference and best available numbers are pending data sync."}
          </p>
        </section>

        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h3 className="text-lg font-semibold">Matchup Context</h3>
          <p className="mt-2 text-kos-text/80">
            {hasSportTemplate
              ? `Primary drivers: ${context.drivers}. Briefing copy stays in data-pending mode until matchup-level inputs are complete.`
              : "Premium placeholder: short-form informational write-up unlocks when matchup data is ready."}
          </p>
        </section>

        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h3 className="text-lg font-semibold">Execution & Availability</h3>
          <p className="mt-2 text-kos-text/80">
            {hasSportTemplate
              ? `Execution focus: ${context.execution}. Core risk watch: ${context.risk}.`
              : "Premium placeholder: execution matrix and availability signals are pending."}
          </p>
        </section>
      </div>
    </main>
  );
}
