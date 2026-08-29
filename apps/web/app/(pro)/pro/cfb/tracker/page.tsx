import Link from "next/link";
import ModelTrackerGradeForm from "@/components/pro/model-tracker/ModelTrackerGradeForm";
import ModelTrackerLogForm from "@/components/pro/model-tracker/ModelTrackerLogForm";
import SportHubShell from "@/components/pro/SportHubShell";
import {
  fetchModelTrackerPicks,
  fetchModelTrackerStatus,
  fetchModelTrackerSummary,
} from "@/lib/model-tracker";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";
export const maxDuration = 20;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function fmtNum(v: unknown, digits = 2): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}`;
}

export default async function CfbTrackerPage({
  searchParams,
}: {
  searchParams?:
    | Promise<Record<string, SearchValue>>
    | Record<string, SearchValue>;
}) {
  const sp =
    searchParams && typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<Record<string, SearchValue>>)
      : ((searchParams as Record<string, SearchValue>) ?? {});
  const week = Number(firstValue(sp.week) ?? 0);
  const season = 2026;

  const [status, summary, picks] = await Promise.all([
    fetchModelTrackerStatus(),
    fetchModelTrackerSummary({ sport: "cfb", season, week }),
    fetchModelTrackerPicks({ sport: "cfb", season, week, limit: 80 }),
  ]);

  const units = summary.units || {};
  const plays = summary.plays || {};
  const leans = summary.leans || {};

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="CFB Model Tracker"
      summary="Week 0–1 desk ledger. Log PLAY (1u) and LEAN (0u) against games tipping today. Grades feed unit curve + model version breakdown."
      truthStates={cfbModelDeskTruthStates()}
      honestyNote={`${cfbModelDeskHonestyNote()} Tracker is internal performance — does not publish stake tags to public boards.`}
      primaryHref="/edge-board/cfb"
      primaryLabel="Edge Board"
      secondaryHref="/pro/model-tracker?sport=cfb"
      secondaryLabel="All-sports tracker"
    >
      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        {[0, 1].map((w) => (
          <Link
            key={w}
            href={`/pro/cfb/tracker?week=${w}`}
            className={`rounded-lg border px-3 py-1.5 ${
              week === w
                ? "border-kos-gold/50 bg-kos-gold/10 text-kos-gold"
                : "border-kos-border text-kos-text/70"
            }`}
          >
            Week {w}
          </Link>
        ))}
        <Link
          href="/pro/cfb/model"
          className="rounded-lg border border-kos-border px-3 py-1.5 text-kos-text/70"
        >
          Season model
        </Link>
        <Link
          href="/pro/cfb/slate"
          className="rounded-lg border border-kos-border px-3 py-1.5 text-kos-text/70"
        >
          Official slate
        </Link>
      </div>

      <p className="mt-3 text-xs text-kos-text/45">
        {status.tracker_version || "tracker"} · {status.n_picks ?? 0} picks ·
        PLAY {status.n_plays ?? 0} · LEAN {status.n_leans ?? 0}
        {status.error ? ` · ${status.error}` : ""}
      </p>

      <section className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-kos-border/80 bg-kos-surface/30 px-4 py-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-kos-text/50">
            Plays
          </div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {String(plays.record || "0-0-0")}
          </div>
          <div className="text-xs text-kos-text/45">1 unit each</div>
        </div>
        <div className="rounded-xl border border-kos-border/80 bg-kos-surface/30 px-4 py-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-kos-text/50">
            Leans
          </div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {String(leans.record || "0-0-0")}
          </div>
          <div className="text-xs text-kos-text/45">0 units · hit-rate</div>
        </div>
        <div className="rounded-xl border border-kos-border/80 bg-kos-surface/30 px-4 py-3">
          <div className="text-[11px] uppercase tracking-[0.14em] text-kos-text/50">
            Units net
          </div>
          <div className="mt-1 text-2xl font-semibold tabular-nums text-kos-gold">
            {fmtNum(units.units_net)}
          </div>
          <div className="text-xs text-kos-text/45">
            ROI{" "}
            {units.roi == null
              ? "—"
              : `${(Number(units.roi) * 100).toFixed(1)}%`}
          </div>
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-kos-text/80">
          Log today&apos;s Week {week} picks
        </h2>
        <p className="mt-1 text-xs text-kos-text/50">
          Prefer Edge Board numbers. Mark PLAY only when KEI edge clears early
          thresholds (4.0 pts W0–2). LEAN at 2.5+.
        </p>
        <div className="mt-3 rounded-xl border border-kos-border/80 bg-kos-surface/20 p-4">
          <ModelTrackerLogForm
            defaultSport="cfb"
            defaultSeason={season}
            defaultWeek={week}
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold text-kos-text/80">
          Week {week} ledger
        </h2>
        <div className="mt-2 overflow-x-auto rounded-xl border border-kos-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-kos-border text-left text-kos-text/50">
                <th className="px-3 py-2">Tag</th>
                <th className="px-3 py-2">Matchup</th>
                <th className="px-3 py-2">Side / line</th>
                <th className="px-3 py-2">Engine</th>
                <th className="px-3 py-2">Grade</th>
                <th className="px-3 py-2 text-right">PnL</th>
                <th className="px-3 py-2">Final</th>
              </tr>
            </thead>
            <tbody>
              {(picks.picks || []).map((p) => (
                <tr key={p.id} className="border-b border-kos-border/60">
                  <td className="px-3 py-2">
                    <span
                      className={
                        p.tag === "PLAY" ? "text-edge-green" : "text-kos-text/70"
                      }
                    >
                      {p.tag}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {p.away_team}@{p.home_team}
                  </td>
                  <td className="px-3 py-2">
                    {p.side} {p.line_at_publish ?? ""}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-kos-text/55">
                    {p.engine_version || "—"}
                  </td>
                  <td className="px-3 py-2">{p.grade}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {fmtNum(p.units_pnl)}
                  </td>
                  <td className="px-3 py-2">
                    {p.grade === "pending" ? (
                      <ModelTrackerGradeForm pickId={p.id} />
                    ) : (
                      <span className="text-xs text-kos-text/50">
                        {p.home_score != null
                          ? `${p.away_score}@${p.home_score}`
                          : "—"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {!picks.picks?.length ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-3 py-8 text-center text-kos-text/45"
                  >
                    Empty week — log the first PLAY or LEAN for tip-off.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      {(summary.unit_curve || []).length > 0 ? (
        <section className="mt-8">
          <h2 className="text-sm font-semibold text-kos-text/80">
            Cumulative units
          </h2>
          <ol className="mt-2 space-y-1 text-sm">
            {(summary.unit_curve || []).map((row) => (
              <li
                key={String(row.id)}
                className="flex justify-between gap-4 border-b border-kos-border/40 py-1.5"
              >
                <span className="font-mono text-xs text-kos-text/60">
                  {row.game_key}
                </span>
                <span className="tabular-nums text-kos-gold">
                  {fmtNum(row.cumulative_units)}
                </span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </SportHubShell>
  );
}
