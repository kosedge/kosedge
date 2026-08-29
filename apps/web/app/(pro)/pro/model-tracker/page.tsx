import Link from "next/link";
import ModelTrackerGradeForm from "@/components/pro/model-tracker/ModelTrackerGradeForm";
import ModelTrackerLogForm from "@/components/pro/model-tracker/ModelTrackerLogForm";
import SportHubShell from "@/components/pro/SportHubShell";
import {
  fetchModelTrackerPicks,
  fetchModelTrackerStatus,
  fetchModelTrackerSummary,
} from "@/lib/model-tracker";

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

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-kos-border/80 bg-kos-surface/30 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.14em] text-kos-text/50">
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold tabular-nums text-kos-text">
        {value}
      </div>
      {hint ? (
        <div className="mt-0.5 text-xs text-kos-text/45">{hint}</div>
      ) : null}
    </div>
  );
}

export default async function ModelTrackerPage({
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
  const sport = firstValue(sp.sport) || "cfb";
  const weekRaw = firstValue(sp.week);
  const week = weekRaw != null && weekRaw !== "" ? Number(weekRaw) : undefined;
  const season = Number(firstValue(sp.season) || 2026);

  const [status, summary, picks] = await Promise.all([
    fetchModelTrackerStatus(),
    fetchModelTrackerSummary({
      sport,
      season,
      week: Number.isFinite(week) ? week : undefined,
    }),
    fetchModelTrackerPicks({
      sport,
      season,
      week: Number.isFinite(week) ? week : undefined,
      limit: 50,
    }),
  ]);

  const units = summary.units || {};
  const plays = summary.plays || {};
  const leans = summary.leans || {};
  const curve = summary.unit_curve || [];

  return (
    <SportHubShell
      sportKey={sport === "cfb" ? "cfb" : sport}
      sportName={sport.toUpperCase()}
      base={sport === "cfb" ? "/pro/cfb" : `/pro/${sport}`}
      title="Model Tracker"
      summary="Enterprise PLAY/LEAN ledger + unit bankroll. PLAY = 1u · LEAN = 0u (hit-rate only). Internal desk — not public props chrome."
      badge="Desk performance"
      primaryHref="/pro/cfb/tracker"
      primaryLabel="CFB desk"
      secondaryHref="/pro/model-transparency"
      secondaryLabel="Transparency"
    >
      <div className="mt-4 flex flex-wrap gap-2 text-sm">
        {(["cfb", "nfl", "nba", "mlb", "wnba"] as const).map((s) => (
          <Link
            key={s}
            href={`/pro/model-tracker?sport=${s}&season=${season}`}
            className={`rounded-lg border px-3 py-1.5 ${
              sport === s
                ? "border-kos-gold/50 bg-kos-gold/10 text-kos-gold"
                : "border-kos-border text-kos-text/70 hover:border-kos-gold/30"
            }`}
          >
            {s.toUpperCase()}
            {s !== "cfb" ? (
              <span className="ml-1 text-[10px] text-kos-text/40">stub</span>
            ) : null}
          </Link>
        ))}
        <Link
          href="/pro/cfb/tracker"
          className="rounded-lg border border-kos-border px-3 py-1.5 text-kos-text/70 hover:border-kos-gold/30"
        >
          CFB Week 0 desk →
        </Link>
      </div>

      {status.error || summary.error ? (
        <p className="mt-4 text-sm text-red-400">
          {status.error || summary.error}
        </p>
      ) : (
        <p className="mt-3 text-xs text-kos-text/45">
          {status.tracker_version || "model-tracker"} · picks{" "}
          {status.n_picks ?? 0} · pending {status.n_pending ?? 0} · healthy{" "}
          {status.healthy ? "yes" : "no"}
        </p>
      )}

      <section className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Plays W-L-P"
          value={String(plays.record || "0-0-0")}
          hint={`hit ${plays.hit_rate != null ? `${(Number(plays.hit_rate) * 100).toFixed(0)}%` : "—"}`}
        />
        <Stat
          label="Leans W-L-P"
          value={String(leans.record || "0-0-0")}
          hint="0 units — training signal"
        />
        <Stat
          label="Units net"
          value={fmtNum(units.units_net)}
          hint={`risked ${fmtNum(units.units_risked, 1)} · pending ${fmtNum(units.units_pending, 1)}`}
        />
        <Stat
          label="ROI (plays)"
          value={
            units.roi == null ? "—" : `${(Number(units.roi) * 100).toFixed(1)}%`
          }
          hint={`CLV avg ${fmtNum(summary.clv?.avg_clv)}`}
        />
      </section>

      {curve.length > 0 ? (
        <section className="mt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-text/60">
            Unit curve (plays)
          </h2>
          <div className="mt-2 overflow-x-auto rounded-xl border border-kos-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-kos-border text-left text-kos-text/50">
                  <th className="px-3 py-2">When</th>
                  <th className="px-3 py-2">Game</th>
                  <th className="px-3 py-2">Grade</th>
                  <th className="px-3 py-2 text-right">PnL</th>
                  <th className="px-3 py-2 text-right">Cum</th>
                </tr>
              </thead>
              <tbody>
                {curve.map((row) => (
                  <tr
                    key={String(row.id)}
                    className="border-b border-kos-border/60"
                  >
                    <td className="px-3 py-2 text-xs text-kos-text/55">
                      {row.graded_at?.slice(0, 16) || "—"}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {row.game_key}
                    </td>
                    <td className="px-3 py-2">{row.grade}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {fmtNum(row.units_pnl)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-kos-gold">
                      {fmtNum(row.cumulative_units)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {summary.by_engine && Object.keys(summary.by_engine).length > 0 ? (
        <section className="mt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-text/60">
            By model / engine
          </h2>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {Object.entries(summary.by_engine).map(([eng, row]) => (
              <div
                key={eng}
                className="rounded-xl border border-kos-border/80 px-4 py-3 text-sm"
              >
                <div className="font-mono text-xs text-kos-gold">{eng}</div>
                <div className="mt-1 text-kos-text/75">
                  {String(row.record || "0-0-0")} · net{" "}
                  {fmtNum(row.units_net)} · n {String(row.n ?? 0)}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-text/60">
          Log PLAY / LEAN
        </h2>
        <div className="mt-3 rounded-xl border border-kos-border/80 bg-kos-surface/20 p-4">
          <ModelTrackerLogForm
            defaultSport={sport}
            defaultSeason={season}
            defaultWeek={Number.isFinite(week) ? Number(week) : 0}
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-kos-text/60">
          Recent picks
        </h2>
        {picks.error ? (
          <p className="mt-2 text-sm text-red-400">{picks.error}</p>
        ) : (
          <div className="mt-2 overflow-x-auto rounded-xl border border-kos-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-kos-border text-left text-kos-text/50">
                  <th className="px-3 py-2">Tag</th>
                  <th className="px-3 py-2">Game</th>
                  <th className="px-3 py-2">Market</th>
                  <th className="px-3 py-2">Line</th>
                  <th className="px-3 py-2">Grade</th>
                  <th className="px-3 py-2 text-right">u</th>
                  <th className="px-3 py-2">Score / grade</th>
                </tr>
              </thead>
              <tbody>
                {(picks.picks || []).map((p) => (
                  <tr
                    key={p.id}
                    className="border-b border-kos-border/60 align-top"
                  >
                    <td className="px-3 py-2">
                      <span
                        className={
                          p.tag === "PLAY"
                            ? "text-edge-green"
                            : "text-kos-text/70"
                        }
                      >
                        {p.tag}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {p.game_key || `${p.away_team}@${p.home_team}`}
                    </td>
                    <td className="px-3 py-2">
                      {p.market_type} {p.side}
                    </td>
                    <td className="px-3 py-2 tabular-nums">
                      {p.line_at_publish ?? "—"}
                    </td>
                    <td className="px-3 py-2">{p.grade || "pending"}</td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {fmtNum(p.units_pnl, 2)}
                    </td>
                    <td className="px-3 py-2">
                      {p.grade === "pending" ? (
                        <ModelTrackerGradeForm pickId={p.id} />
                      ) : (
                        <span className="text-xs text-kos-text/50">
                          {p.home_score != null
                            ? `${p.home_score}-${p.away_score}`
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
                      className="px-3 py-6 text-center text-kos-text/45"
                    >
                      No picks yet — log a PLAY or LEAN above for Week 0.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </SportHubShell>
  );
}
