import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import {
  fetchCfbSeasonEngineStatus,
  fetchCfbSimulate,
} from "@/lib/cfb-season-engine";
import { formatIndex } from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export default async function CfbSeasonProjectionsPage() {
  const [status, sim] = await Promise.all([
    fetchCfbSeasonEngineStatus(),
    fetchCfbSimulate({ nSims: 20, asOfWeek: 0, seed: 2026 }),
  ]);
  const ranking = Array.isArray(sim.ranking) ? sim.ranking : [];
  const nGames = status.n_games ?? status.schedule_game_count;

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Season projections"
      summary="Research expected wins on the official 2026 ESPN slate. Limited P4 sample. Not graded. CFP and national-title percentages are omitted — ESPN postseason is empty and we do not invent them."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/teams"
      primaryLabel="Team DNA"
      secondaryHref="/pro/cfb/model"
      secondaryLabel="Model hub"
    >
      <section className="mt-4 rounded-2xl border border-amber-400/25 bg-amber-400/8 px-4 py-3 text-sm text-kos-text/80">
        <p className="font-semibold text-amber-100">Research only</p>
        <p className="mt-1 text-xs leading-relaxed text-kos-text/70">
          Pure model win totals — not a wagering instruction, not CLV, not KEI.
          Hist walk-forward is cold vs market (Week 0–1 ATS 47.7% / MAE 8.36).
          used_in_spread stays false. CFP / natty stub.{" "}
          {sim.win_tables_final === false ||
          status.season_futures?.win_tables_final === false
            ? "win_tables_final=false (research, not product truth)."
            : null}{" "}
          Web run is capped at 20 paths on the official {nGames ?? 889}-game
          slate — distribution width is approximate.
        </p>
      </section>

      <p className="mt-3 text-xs text-kos-text/55">
        Engine {sim.engine_version || status.engine_version || "—"} · n_sims{" "}
        {sim.n_sims ?? "—"} · slate_complete{" "}
        {String(status.slate_complete ?? sim.slate_complete ?? false)} ·
        used_in_spread={String(sim.used_in_spread ?? status.used_in_spread ?? false)}
      </p>

      {sim.error ? (
        <p className="mt-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/70">
          Season sim unavailable ({sim.error}). Hub and project-game still work.
        </p>
      ) : ranking.length === 0 ? (
        <p className="mt-4 text-sm text-kos-text/65">No ranking rows returned.</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="w-full min-w-[32rem] text-left text-sm text-kos-text/80">
            <thead>
              <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Team</th>
                <th className="px-3 py-2">Conf</th>
                <th className="px-3 py-2">E[wins]</th>
                <th className="px-3 py-2">p10–p90</th>
                <th className="px-3 py-2">σ</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((row, i) => {
                const team = String(row.team ?? "");
                const mean = num(row.mean);
                const p10 = num(row.p10);
                const p90 = num(row.p90);
                const std = num(row.std);
                return (
                  <tr
                    key={team || i}
                    className="border-b border-white/5 last:border-0"
                  >
                    <td className="px-3 py-1.5 text-kos-text/45">
                      {num(row.rank) ?? i + 1}
                    </td>
                    <td className="px-3 py-1.5 font-medium text-kos-text">
                      <Link
                        href={`/pro/cfb/teams?q=${encodeURIComponent(team)}`}
                        className="hover:text-kos-gold"
                      >
                        {team}
                      </Link>
                    </td>
                    <td className="px-3 py-1.5 text-xs">
                      {String(row.conference ?? "—")}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums">
                      {formatIndex(mean, 1)}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums text-xs text-kos-text/70">
                      {p10 != null && p90 != null
                        ? `${p10.toFixed(0)}–${p90.toFixed(0)}`
                        : "—"}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums text-xs">
                      {formatIndex(std, 1)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </SportHubShell>
  );
}
