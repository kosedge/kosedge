import Link from "next/link";
import { loadLatestNflPreseasonBundle2026 } from "@/lib/nfl-preseason-artifacts";
import { getAllNflSeasonPreviews } from "@/lib/nfl-season-previews";
import { teamDisplayName } from "@/lib/nfl-team-intel";

export const dynamic = "force-dynamic";

export default function PredictionMarketPage() {
  const bundle = loadLatestNflPreseasonBundle2026();
  const previews = getAllNflSeasonPreviews();
  const marketByTeam = new Map(
    previews.map((preview) => [preview.team, preview.market] as const),
  );
  const rows = (bundle?.teamRows ?? [])
    .slice()
    .sort(
      (a, b) =>
        b.superBowlWinProb - a.superBowlWinProb ||
        b.playoffProb - a.playoffProb,
    );

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-4 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/nfl/overview" className="hover:text-kos-gold">
          NFL Overview
        </Link>
        <span>/</span>
        <span className="text-kos-text">Prediction Markets</span>
      </nav>

      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/12 via-black/40 to-black/65 p-6 sm:p-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
          NFL Pro · Futures desk
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text">
          Prediction Markets
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-kos-text/80">
          Model-backed Super Bowl, playoff, and win-total context from the
          latest Kos Edge preseason simulation bundle, paired with writer-desk
          market numbers from the 2026 season previews.
        </p>
        <p className="mt-3 text-xs text-kos-text/55">
          Bundle {bundle?.bundleDirName ?? "unavailable"} · {rows.length} teams
        </p>
      </section>

      {rows.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-8 text-sm text-kos-text/70">
          Futures tables will appear when the preseason simulation bundle is
          available in this deployment.
        </div>
      ) : (
        <div className="mt-8 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
              <tr>
                <th className="px-4 py-3">#</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">Exp wins</th>
                <th className="px-4 py-3">Playoff</th>
                <th className="px-4 py-3">Division</th>
                <th className="px-4 py-3">Super Bowl</th>
                <th className="px-4 py-3">Market (desk)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr
                  key={row.team}
                  className="border-b border-white/5 text-kos-text/85"
                >
                  <td className="px-4 py-3 text-kos-text/55">{index + 1}</td>
                  <td className="px-4 py-3 font-medium">
                    <Link
                      href={`/pro/nfl/previews/${row.team}`}
                      className="hover:text-kos-gold"
                    >
                      {teamDisplayName(row.team)}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{row.expectedWins.toFixed(2)}</td>
                  <td className="px-4 py-3">
                    {(row.playoffProb * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    {(row.divisionTitleProb * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    {(row.superBowlWinProb * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-xs text-kos-text/65">
                    {marketByTeam.get(row.team) ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="mt-6 text-xs text-kos-text/50">
        Informational only. External prediction-market venue feeds (Kalshi /
        Polymarket style) can be layered later; this page ships model + desk
        futures now so the NFL hub never dead-ends.
      </p>
    </main>
  );
}
