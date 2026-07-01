import Link from "next/link";
import { getSport } from "@/lib/sports";

type SlateTemplate = {
  market: string;
  model: string;
  writeup: string;
};

const SPORT_SLATE_TEMPLATES: Record<string, SlateTemplate> = {
  nfl: {
    market: "PHI -2.5 | 47.5",
    model: "PHI -3.0 | 46.8",
    writeup:
      "This matchup is shaped by key-number pressure, pressure-rate mismatch, and late injury designations. Priority is execution quality around 3 and 7 as limits mature.",
  },
  cfb: {
    market: "UTAH -4.0 | 52.5",
    model: "UTAH -4.8 | 51.7",
    writeup:
      "Primary drivers are tempo divergence, havoc differential, and red-zone efficiency variance. Late quarterback and weather confirmations remain the swing factors.",
  },
  nba: {
    market: "BOS -5.5 | 228.5",
    model: "BOS -6.2 | 227.1",
    writeup:
      "Rotation stability and pace-state assumptions drive this projection. Final confirmation is tied to late availability and back-to-back fatigue adjustments.",
  },
  wnba: {
    market: "NYL -4.5 | 164.5",
    model: "NYL -5.1 | 163.8",
    writeup:
      "Usage concentration and turnover control are the primary levers. Watch travel compression and late guard status for any final repricing.",
  },
  mlb: {
    market: "LAD -128 | 8.5",
    model: "LAD -136 | 8.1",
    writeup:
      "Starter arsenal fit, bullpen leverage depth, and weather-adjusted run environment define the edge. Lineup cards and bullpen burn rates are final checks.",
  },
  nhl: {
    market: "EDM -132 | 6.5",
    model: "EDM -138 | 6.2",
    writeup:
      "Goaltender confirmation and five-on-five chance quality drive this setup. Special-teams volatility remains the dominant downside risk.",
  },
  ncaam: {
    market: "GONZ -6.0 | 149.5",
    model: "GONZ -6.8 | 148.7",
    writeup:
      "Tempo profile, offensive rebounding leverage, and whistle environment determine projection quality. Late lineup notes can still move this market.",
  },
};

export default function SlatePage({
  params,
}: {
  params: { sport: string; date: string };
}) {
  const base = `/pro/${params.sport}`;
  const sport = getSport(params.sport);
  const sportName = sport?.fullName ?? params.sport.toUpperCase();
  const template = SPORT_SLATE_TEMPLATES[params.sport];
  const hasData = Boolean(template);

  const games = [
    {
      slug: `${params.sport}-premium-placeholder`,
      away: `${sportName} Away`,
      home: `${sportName} Home`,
      market: template?.market ?? "Market pending",
      model: template?.model ?? "Model pending",
      writeup:
        template?.writeup ??
        "Premium placeholder state: matchup narratives publish once validated market and model inputs are available for this date.",
    },
  ];

  return (
    <main>
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-2xl font-semibold">{sportName} Slate: {params.date}</h2>
          <p className="mt-2 text-kos-text/70">
            {hasData
              ? "Write-ups are collapsed by default. Model reference is informational only."
              : "Premium placeholder mode: slate cards expand automatically when validated game feeds are available."}
          </p>
        </div>

        <Link
          href={`${base}/overview`}
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          Back to Hub
        </Link>
      </div>

      <div className="mt-8 space-y-4">
        {games.map((g) => (
          <div
            key={g.slug}
            className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6"
          >
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-lg font-semibold">
                  {g.away} @ {g.home}
                </div>
                <div className="mt-1 text-sm text-kos-text/70">
                  Market: {g.market} · Model: {g.model}
                </div>
              </div>

              <Link
                href={`${base}/matchups/${params.date}/${g.slug}`}
                className="rounded-xl border border-kos-border bg-kos-surface/20 px-4 py-2 text-sm hover:border-kos-gold/40"
              >
                {hasData ? "Open Matchup" : "Open Placeholder Brief"}
              </Link>
            </div>

            {/* Collapsed by default */}
            <details className="mt-4">
              <summary className="cursor-pointer select-none text-sm text-kos-gold hover:text-edge-green">
                View matchup context
              </summary>
              <p className="mt-3 text-kos-text/80">{g.writeup}</p>
              <p className="mt-4 text-sm text-kos-text/60">
                Model Reference (Not a Recommendation): {g.model}
              </p>
            </details>
          </div>
        ))}
      </div>
    </main>
  );
}
