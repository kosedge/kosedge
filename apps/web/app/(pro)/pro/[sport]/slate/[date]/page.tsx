import Link from "next/link";

export default function SlatePage({ params }: { params: { sport: string; date: string } }) {
  const base = `/pro/${params.sport}`;

  // Placeholder. Later this becomes fetched/generated list of games.
  const games = [
    {
      slug: "northwestern-state-vs-stephen-f-austin",
      away: "Northwestern State",
      home: "Stephen F. Austin",
      market: "SFA -3.0 | 145.5",
      model: "SFA -3.5 | 146.0",
      writeup:
        "Stephen F. Austin profiles as defense-first with strong interior suppression and defensive rebounding stability, while Northwestern State has struggled on the glass. With both teams operating at below-average tempo, half-court efficiency and second-chance possessions may influence outcomes.",
    },
  ];

  return (
    <main>
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-2xl font-semibold">Slate: {params.date}</h2>
          <p className="mt-2 text-kos-text/70">
            Write-ups are collapsed by default. Model reference is informational only.
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
                Open Matchup
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