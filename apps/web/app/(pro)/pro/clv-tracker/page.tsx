import Link from "next/link";
import NflProShell from "@/components/pro/nfl/NflProShell";
import { loadNflClvBenchmarkReport } from "@/lib/nfl-clv-benchmark";

function ClvCard({
  label,
  n,
  avgClv,
  positiveRate,
  unit,
}: {
  label: string;
  n: number;
  avgClv: number;
  positiveRate: number;
  unit: string;
}) {
  const positive = avgClv > 0;
  return (
    <div className="rounded-xl border border-kos-border bg-kos-surface/40 p-5">
      <div className="text-sm text-kos-text/70">{label}</div>
      <div className="mt-2 flex items-baseline gap-2">
        <span
          className={`text-2xl font-semibold ${positive ? "text-edge-green" : "text-kos-text"}`}
        >
          {avgClv > 0 ? "+" : ""}
          {avgClv.toFixed(3)}
        </span>
        <span className="text-xs text-kos-text/50">
          avg CLV{unit ? ` (${unit})` : ""}
        </span>
      </div>
      <div className="mt-1 text-sm text-kos-text/60">
        {(positiveRate * 100).toFixed(1)}% of plays beat the closing line
      </div>
      <div className="mt-1 text-xs text-kos-text/45">
        n = {n.toLocaleString()} plays
      </div>
    </div>
  );
}

export default function CLVTrackerPage() {
  const report = loadNflClvBenchmarkReport();

  return (
    <NflProShell
      pageTitle="CLV Tracker"
      pageSubtitle="Closing Line Value — did the market move toward our number after we made the play? Research accountability, not a picks feed."
      actions={
        <Link
          href="/pro/model-transparency"
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
        >
          Model Health
        </Link>
      }
    >
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        {report ? (
          <>
            <section>
              <h2 className="text-lg font-semibold text-kos-gold">
                NFL — 2024–2025 seasons (real open-to-close line movement)
              </h2>
              <p className="mt-1 text-sm text-kos-text/60">
                Only games where the model showed genuine edge vs. the opening
                price are counted as a play — no edge, no play, matching our
                &quot;doesn&apos;t clear the threshold, doesn&apos;t make the
                board&quot; policy.
              </p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <ClvCard
                  label="Moneyline"
                  n={report.resultsCombined.moneyline.n}
                  avgClv={report.resultsCombined.moneyline.avgClv}
                  positiveRate={report.resultsCombined.moneyline.positiveRate}
                  unit="implied win %"
                />
                <ClvCard
                  label="Totals"
                  n={report.resultsCombined.total.n}
                  avgClv={report.resultsCombined.total.avgClv}
                  positiveRate={report.resultsCombined.total.positiveRate}
                  unit="points"
                />
              </div>
            </section>

            <section className="mt-8">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-text/60">
                By season
              </h2>
              <div className="mt-3 overflow-x-auto rounded-xl border border-kos-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-kos-border text-left text-kos-text/60">
                      <th className="px-4 py-2">Season</th>
                      <th className="px-4 py-2">Market</th>
                      <th className="px-4 py-2 text-right">Plays</th>
                      <th className="px-4 py-2 text-right">Avg CLV</th>
                      <th className="px-4 py-2 text-right">Beat close %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.resultsBySeason.map((row) => (
                      <tr
                        key={`${row.season}-${row.market}`}
                        className="border-b border-white/5"
                      >
                        <td className="px-4 py-2 text-kos-text/80">
                          {row.season}
                        </td>
                        <td className="px-4 py-2 text-kos-text/80 capitalize">
                          {row.market}
                        </td>
                        <td className="px-4 py-2 text-right text-kos-text/80">
                          {row.n}
                        </td>
                        <td
                          className={`px-4 py-2 text-right font-medium ${
                            row.avgClv > 0
                              ? "text-edge-green"
                              : "text-kos-text/80"
                          }`}
                        >
                          {row.avgClv > 0 ? "+" : ""}
                          {row.avgClv.toFixed(3)}
                        </td>
                        <td className="px-4 py-2 text-right text-kos-text/80">
                          {(row.positiveRate * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="mt-8 rounded-xl border border-kos-gold/25 bg-kos-gold/5 p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-gold">
                Methodology &amp; honest caveats
              </h2>
              <p className="mt-2 text-sm text-kos-text/75">
                {report.methodology.clvDefinition}
              </p>
              <p className="mt-2 text-sm text-kos-text/65">
                {report.methodology.excluded}
              </p>
              <p className="mt-3 text-xs text-kos-text/45">
                Report generated {report.generatedAt} · model{" "}
                {report.modelVersion} · source: {report.methodology.dataSource}
              </p>
            </section>
          </>
        ) : (
          <p className="text-sm text-kos-text/60">
            CLV report not found. Run run_nfl_clv_attribution after backfilling
            real historical odds to generate
            data/ops/nfl-clv-benchmark-report.json.
          </p>
        )}
      </main>
    </NflProShell>
  );
}
