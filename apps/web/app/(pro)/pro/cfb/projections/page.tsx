import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { cfbTeamDisplayName } from "@/lib/cfb-conferences";
import {
  cfbProjectionTeams,
  cfbResearchVersionStrip,
  loadCfbSeasonProjections,
} from "@/lib/cfb-research-artifacts";
import { formatIndex } from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

export default function CfbSeasonProjectionsPage() {
  const pack = loadCfbSeasonProjections();
  const ranking = cfbProjectionTeams();
  const version = cfbResearchVersionStrip();
  const scheduleLoud = ranking.filter(
    (row) =>
      (row.power_rank ?? 999) >= 35 && (row.rank ?? 999) <= 20,
  );

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Season projections"
      summary="Frozen research expected wins on the official 2026 ESPN slate. N is the artifact path count. CFP / natty live on Futures — not invented here as book prices."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/teams"
      primaryLabel="Power / Teams"
      secondaryHref="/pro/cfb/model"
      secondaryLabel="Model hub"
    >
      <section className="mt-4 rounded-2xl border border-amber-400/25 bg-amber-400/8 px-4 py-3 text-sm text-kos-text/80">
        <p className="font-semibold text-amber-100">Research only · N documented</p>
        <p className="mt-1 text-xs leading-relaxed text-kos-text/70">
          Precomputed artifact {pack.artifact_id ?? "cfb-season-projections"} ·{" "}
          <strong>N={version.n_sims}</strong> independent Bernoulli paths ·{" "}
          {pack.n_games_scored ?? 889} games scored · win_tables_final=
          {String(pack.win_tables_final ?? false)}. E[wins] is schedule-adjusted.
          Power rank is talent. Win totals are research (used_in_spread=false).
          KEI is the published game line.{" "}
          <Link href="/pro/cfb/futures" className="font-semibold text-kos-gold">
            Futures →
          </Link>
        </p>
      </section>

      <p className="mt-3 text-xs text-kos-text/55">
        Engine {version.engine_version} · N={version.n_sims} · as_of{" "}
        {version.as_of} · power {version.power_version} · used_in_spread=false
      </p>

      {scheduleLoud.length > 0 ? (
        <section className="mt-4 rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-xs text-kos-text/70">
          <p className="font-semibold text-kos-text">
            E[wins] ≠ power — schedule cluster
          </p>
          <p className="mt-1">
            These rows sit in the top 20 of expected wins with power rank 35 or
            worse. That is a soft path, not a talent inversion (USF-class).
          </p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {scheduleLoud.map((row) => (
              <li key={row.team}>
                <Link
                  href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                  className="rounded-md border border-white/10 px-2 py-1 text-kos-text/80 hover:border-kos-gold/35"
                >
                  {row.team} E#{row.rank} / P#{row.power_rank}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {ranking.length === 0 ? (
        <p className="mt-4 text-sm text-kos-text/65">No ranking rows in artifact.</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="w-full min-w-[36rem] text-left text-sm text-kos-text/80">
            <thead>
              <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                <th className="px-3 py-2">E#</th>
                <th className="px-3 py-2">Team</th>
                <th className="px-3 py-2">Conf</th>
                <th className="px-3 py-2">E[wins]</th>
                <th className="px-3 py-2">p10–p90</th>
                <th className="px-3 py-2">σ</th>
                <th className="px-3 py-2">Power #</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((row, i) => (
                <tr
                  key={row.team || i}
                  className="border-b border-white/5 last:border-0"
                >
                  <td className="px-3 py-1.5 text-kos-text/45">
                    {row.rank ?? i + 1}
                  </td>
                  <td className="px-3 py-1.5 font-medium text-kos-text">
                    <Link
                      href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                      className="hover:text-kos-gold"
                    >
                      {row.team}
                    </Link>
                    <span className="ml-2 hidden text-[11px] text-kos-text/40 sm:inline">
                      {cfbTeamDisplayName(row.team)}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-xs">
                    {row.conference ?? "—"}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums">
                    {formatIndex(row.mean, 2)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-xs text-kos-text/70">
                    {row.p10 != null && row.p90 != null
                      ? `${row.p10.toFixed(0)}–${row.p90.toFixed(0)}`
                      : "—"}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-xs">
                    {formatIndex(row.std, 2)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-xs text-kos-text/60">
                    {row.power_rank ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </SportHubShell>
  );
}
