import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { cfbTeamDisplayName } from "@/lib/cfb-conferences";
import {
  cfbKeiVersionStrip,
  loadCfbFuturesPack,
} from "@/lib/cfb-kei-artifacts";

export const dynamic = "force-dynamic";

export default function CfbFuturesPage() {
  const pack = loadCfbFuturesPack();
  const version = cfbKeiVersionStrip();
  const rows = pack.teams ?? [];
  const confs = Object.entries(pack.conference_titles ?? {}).sort(([a], [b]) =>
    a.localeCompare(b),
  );

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Futures"
      summary="Sim-derived CFP / national title / conference title probabilities from our 2026 paths. Not book prices. Not an ESPN bracket copy."
      primaryHref="/pro/cfb/projections"
      primaryLabel="Win totals"
      secondaryHref="/edge-board/cfb"
      secondaryLabel="Edge Board"
    >
      <section className="mt-4 rounded-2xl border border-kos-gold/25 bg-black/35 px-4 py-3 text-sm text-kos-text/80">
        <p className="font-semibold text-kos-gold">
          12-team CFP · N={version.n_sims} · {version.futures_version}
        </p>
        <p className="mt-1 text-xs leading-relaxed text-kos-text/70">
          {pack.method} Engine {version.engine_version} · as_of {version.as_of} ·
          used_in_spread=false (sim probabilities, not a KEI line). Preseason
          mass is wide — 1-decimal percents, not fake 0.1% precision beyond N.
          Independents are at-large only. G5 champs can take an auto bid if they
          rank among the top-5 conference champions.
        </p>
      </section>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-white/10">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-black/40 text-[11px] uppercase tracking-[0.12em] text-kos-text/55">
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">Team</th>
              <th className="px-3 py-2">Conf</th>
              <th className="px-3 py-2">Natty %</th>
              <th className="px-3 py-2">CFP %</th>
              <th className="px-3 py-2">Conf title %</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 40).map((row) => (
              <tr key={row.team} className="border-b border-white/6">
                <td className="px-3 py-2 text-kos-text/55">{row.rank}</td>
                <td className="px-3 py-2">
                  <Link
                    href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                    className="font-semibold text-kos-text hover:text-kos-gold"
                  >
                    {cfbTeamDisplayName(row.team)}
                  </Link>
                </td>
                <td className="px-3 py-2 text-kos-text/65">{row.conference}</td>
                <td className="px-3 py-2 font-semibold text-kos-gold">
                  {row.natty_pct}
                </td>
                <td className="px-3 py-2">{row.cfp_make_pct}</td>
                <td className="px-3 py-2 text-kos-text/70">
                  {row.conf_title_pct ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="mt-8">
        <h2 className="text-lg font-semibold text-kos-text">
          Conference titles
        </h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {confs.map(([conf, list]) => (
            <div
              key={conf}
              className="rounded-xl border border-white/10 bg-black/30 px-4 py-3"
            >
              <p className="text-sm font-semibold text-kos-gold">{conf}</p>
              <ol className="mt-2 space-y-1 text-xs text-kos-text/75">
                {list.slice(0, 5).map((row) => (
                  <li key={row.team}>
                    {cfbTeamDisplayName(row.team)} · {row.conf_title_pct}% title
                    · {row.cfp_make_pct}% CFP
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>
    </SportHubShell>
  );
}
