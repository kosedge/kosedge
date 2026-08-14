import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { loadCfbSeasonProjections } from "@/lib/cfb-research-artifacts";
import { formatIndex } from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

export default async function CfbSeasonProjectionsPage() {
  const pack = loadCfbSeasonProjections();
  const ranking = pack?.teams ?? [];

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Season projections"
      summary="Research expected wins on the official 2026 ESPN slate from a frozen Power SoT. Not graded. CFP and national-title percentages are omitted — we do not invent them."
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
          used_in_spread stays false. CFP / natty omitted. win_tables_final=false.
          Frozen-SoT Monte Carlo on the official slate (in-path evolution off).
        </p>
      </section>

      <p className="mt-3 text-xs text-kos-text/55">
        {pack?.engine_version || "—"} · {pack?.power_version || "—"} · N=
        {pack?.n_sims ?? "—"} · as_of {pack?.as_of || pack?.power_as_of || "—"} ·
        artifact {pack?.artifact_id || "missing"} · used_in_spread=
        {String(pack?.used_in_spread ?? false)}
      </p>

      {!pack ? (
        <p className="mt-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/70">
          Projection artifact not packaged. Run{" "}
          <code className="text-kos-text/80">
            scripts/cfb/package_power_sot_and_projections.py
          </code>
          .
        </p>
      ) : ranking.length === 0 ? (
        <p className="mt-4 text-sm text-kos-text/65">No ranking rows in artifact.</p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="w-full min-w-[36rem] text-left text-sm text-kos-text/80">
            <thead>
              <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Team</th>
                <th className="px-3 py-2">Conf</th>
                <th className="px-3 py-2">E[wins]</th>
                <th className="px-3 py-2">p10–p90</th>
                <th className="px-3 py-2">σ</th>
                <th className="px-3 py-2">P(bowl)</th>
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
                      href={`/pro/cfb/teams?q=${encodeURIComponent(row.team)}`}
                      className="hover:text-kos-gold"
                    >
                      {row.team}
                    </Link>
                  </td>
                  <td className="px-3 py-1.5 text-xs">
                    {row.conference ?? "—"}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums">
                    {formatIndex(row.mean, 1)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-xs text-kos-text/70">
                    {row.p10 != null && row.p90 != null
                      ? `${Number(row.p10).toFixed(0)}–${Number(row.p90).toFixed(0)}`
                      : "—"}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-xs">
                    {formatIndex(row.std, 1)}
                  </td>
                  <td className="px-3 py-1.5 tabular-nums text-xs">
                    {row.p_bowl == null
                      ? "—"
                      : `${(row.p_bowl * 100).toFixed(0)}%`}
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
