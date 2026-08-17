"use client";

import { useState, useTransition } from "react";
import { TruthStateBadges } from "@/components/pro/TruthStateBadge";
import {
  americanOddsFromWinProb,
  formatAmericanOdds,
  formatFavoriteSpread,
  formatIndex,
  formatProjectedScoreLine,
  formatQbClassLabel,
  formatScore,
  formatSpread,
  formatWinProb,
  type CfbTeamOption,
} from "@/lib/cfb-season-engine-format";
import { findCfbKeiGame } from "@/lib/cfb-kei-artifacts";
import { cfbModelDeskTruthStates } from "@/lib/cfb-truth-label";

type PlayerProjectionRow = {
  player_key?: string;
  player_name?: string;
  team?: string;
  position?: string;
  role?: string;
  depth_order?: number;
  pass_yards?: number | null;
  pass_tds?: number | null;
  interceptions?: number | null;
  rush_yards?: number | null;
  rush_tds?: number | null;
  rec_yards?: number | null;
  rec_tds?: number | null;
  rb_role_style?: string | null;
  fidelity?: string;
};

type ProjectPayload = {
  ok?: boolean;
  mode?: string;
  season?: number;
  week?: number;
  home_team?: string;
  away_team?: string;
  engine_version?: string;
  home_win_prob?: number;
  away_win_prob?: number;
  expected_home_score?: number;
  expected_away_score?: number;
  expected_total?: number;
  spread_home?: number;
  margin_sd?: number;
  fidelity?: string;
  uncertainty?: Record<string, unknown>;
  early_season_uncertainty?: Record<string, unknown>;
  drivers?: Record<string, unknown>;
  home_layers?: Record<string, unknown>;
  away_layers?: Record<string, unknown>;
  player_projections?: PlayerProjectionRow[];
  players?: PlayerProjectionRow[];
  notes?: Record<string, string>;
  error?: string;
  hint?: string;
};

const selectClass =
  "min-h-11 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-kos-text outline-none focus:border-kos-gold/50";
const labelClass =
  "mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/55";

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function str(v: unknown): string | null {
  return typeof v === "string" && v.length > 0 ? v : null;
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex min-h-8 items-center gap-1.5 rounded-md border border-white/10 bg-black/35 px-2 py-1 text-[11px] text-kos-text/80">
      <span className="uppercase tracking-[0.1em] text-kos-text/45">
        {label}
      </span>
      <span className="font-medium tabular-nums text-kos-text">{value}</span>
    </span>
  );
}

function coachingLabel(
  coaching: Record<string, unknown> | undefined,
  adj: number | null,
): string {
  if (!coaching) return adj != null ? `${adj >= 0 ? "+" : ""}${adj.toFixed(1)} pts` : "—";
  const flags = [
    coaching.new_hc ? "new HC" : null,
    coaching.new_oc ? "new OC" : null,
    coaching.new_dc ? "new DC" : null,
  ].filter(Boolean);
  const base = flags.length ? flags.join(" · ") : "returning";
  if (adj == null || Math.abs(adj) < 0.05) return base;
  const pts = `${adj >= 0 ? "+" : ""}${adj.toFixed(1)}`;
  return `${base} (${pts})`;
}

function DriverStrip({
  side,
  team,
  drivers,
  layers,
  coachingAdj,
  showHfa,
}: {
  side: "home" | "away";
  team: string;
  drivers: Record<string, unknown> | undefined;
  layers: Record<string, unknown> | undefined;
  coachingAdj: number | null;
  showHfa: boolean;
}) {
  if (!drivers) return null;
  const unit = (drivers.unit_grades as Record<string, unknown> | undefined) ?? {};
  const coaching =
    (drivers.coaching as Record<string, unknown> | undefined) ??
    (layers?.coaching as Record<string, unknown> | undefined);
  const hfa =
    (drivers.home_field as Record<string, unknown> | undefined) ?? {};
  const qbLayer = (layers?.qb as Record<string, unknown> | undefined) ?? {};
  const qbName = str(qbLayer.starter_name);
  const qbClass = formatQbClassLabel(str(drivers.qb_class));
  const qbValue = qbName
    ? `${qbName}${qbClass !== "—" ? ` · ${qbClass}` : ""}`
    : qbClass;

  return (
    <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold/85">
          {team} · {side}
        </p>
        {str(drivers.roster_fidelity) ? (
          <span className="text-[10px] uppercase tracking-[0.1em] text-kos-text/40">
            {String(drivers.roster_fidelity)}
          </span>
        ) : null}
      </div>
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        <Chip
          label="Off Eff"
          value={formatIndex(num(drivers.off_eff), 0)}
        />
        <Chip
          label="Def Eff"
          value={formatIndex(num(drivers.def_eff), 0)}
        />
        <Chip
          label="Roster"
          value={formatIndex(num(drivers.roster_strength), 1)}
        />
        <Chip label="QB" value={qbValue} />
        <Chip label="OL" value={formatIndex(num(unit.ol), 0)} />
        <Chip label="Skill" value={formatIndex(num(unit.skill), 0)} />
        <Chip label="F7" value={formatIndex(num(unit.front_seven), 0)} />
        <Chip label="Sec" value={formatIndex(num(unit.secondary), 0)} />
        {showHfa ? (
          <Chip
            label="HFA"
            value={`${str(hfa.bucket) ?? "—"} ${formatIndex(num(hfa.hfa_points), 1)}`}
          />
        ) : null}
        <Chip label="Coach" value={coachingLabel(coaching, coachingAdj)} />
      </div>
    </div>
  );
}

function MarketCell({
  label,
  primary,
  secondary,
}: {
  label: string;
  primary: string;
  secondary?: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/30 px-3 py-3 sm:px-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/45">
        {label}
      </p>
      <p className="mt-1.5 text-xl font-semibold tabular-nums text-kos-gold sm:text-2xl">
        {primary}
      </p>
      {secondary ? (
        <p className="mt-1 text-xs tabular-nums text-kos-text/60">{secondary}</p>
      ) : null}
    </div>
  );
}

function fmtStat(v: number | null | undefined, digits = 0): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return digits > 0 ? v.toFixed(digits) : String(Math.round(v));
}

function PlayerHooksTable({
  team,
  rows,
  scriptDetail,
  coherenceApplied,
}: {
  team: string;
  rows: PlayerProjectionRow[];
  scriptDetail?: string | null;
  coherenceApplied?: boolean;
}) {
  if (!rows.length) return null;
  const qbs = rows.filter((r) => r.position === "QB");
  const skill = rows.filter((r) => r.position !== "QB");
  const scriptLabel = scriptDetail
    ? scriptDetail.replace(/_/g, " ")
    : null;
  return (
    <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold/85">
        {team} · player hooks
      </p>
      {scriptLabel || coherenceApplied ? (
        <p className="mt-1 text-[10px] text-kos-text/50">
          {scriptLabel ? <>script {scriptLabel}</> : null}
          {scriptLabel && coherenceApplied ? " · " : null}
          {coherenceApplied ? "coherence caps applied" : null}
        </p>
      ) : null}
      <div className="mt-2 -mx-1 overflow-x-auto">
        <table className="min-w-[520px] w-full border-collapse text-left text-[11px] sm:text-xs">
          <thead>
            <tr className="border-b border-white/10 text-kos-text/45">
              <th className="px-1.5 py-1.5 font-semibold">Player</th>
              <th className="px-1.5 py-1.5 font-semibold">Role</th>
              <th className="px-1.5 py-1.5 font-semibold tabular-nums">Pass</th>
              <th className="px-1.5 py-1.5 font-semibold tabular-nums">pTD</th>
              <th className="px-1.5 py-1.5 font-semibold tabular-nums">INT</th>
              <th className="px-1.5 py-1.5 font-semibold tabular-nums">Rush</th>
              <th className="px-1.5 py-1.5 font-semibold tabular-nums">Rec</th>
              <th className="px-1.5 py-1.5 font-semibold tabular-nums">rTD</th>
            </tr>
          </thead>
          <tbody>
            {[...qbs, ...skill].map((r) => {
              const roleBits = [r.role ?? r.position ?? "—"];
              if (r.rb_role_style) roleBits.push(r.rb_role_style);
              const recTd =
                r.position === "QB"
                  ? r.rush_tds
                  : (r.rec_tds ?? 0) + (r.rush_tds ?? 0);
              return (
                <tr
                  key={`${r.team}-${r.player_key ?? r.player_name}`}
                  className="border-b border-white/5 text-kos-text/85"
                >
                  <td className="px-1.5 py-1.5 font-medium text-kos-text">
                    {r.player_name ?? "—"}
                  </td>
                  <td className="px-1.5 py-1.5 text-kos-text/60">
                    {roleBits.join(" · ")}
                  </td>
                  <td className="px-1.5 py-1.5 tabular-nums">
                    {fmtStat(r.pass_yards)}
                  </td>
                  <td className="px-1.5 py-1.5 tabular-nums">
                    {fmtStat(r.pass_tds, 1)}
                  </td>
                  <td className="px-1.5 py-1.5 tabular-nums">
                    {fmtStat(r.interceptions, 1)}
                  </td>
                  <td className="px-1.5 py-1.5 tabular-nums">
                    {fmtStat(r.rush_yards)}
                  </td>
                  <td className="px-1.5 py-1.5 tabular-nums">
                    {fmtStat(r.rec_yards)}
                  </td>
                  <td className="px-1.5 py-1.5 tabular-nums">
                    {fmtStat(recTd, 1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function CfbProjectGameClient({
  teams,
  defaultHome = "OSU",
  defaultAway = "MICH",
  defaultWeek = 1,
  defaultNeutral = false,
  engineVersion,
}: {
  teams: CfbTeamOption[];
  defaultHome?: string;
  defaultAway?: string;
  defaultWeek?: number;
  defaultNeutral?: boolean;
  engineVersion?: string;
}) {
  const [homeTeam, setHomeTeam] = useState(defaultHome);
  const [awayTeam, setAwayTeam] = useState(defaultAway);
  const [week, setWeek] = useState(defaultWeek);
  const [neutralSite, setNeutralSite] = useState(defaultNeutral);
  const [nightGame, setNightGame] = useState(false);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectPayload | null>(null);
  const [hasRun, setHasRun] = useState(false);

  function run() {
    startTransition(async () => {
      setError(null);
      setResult(null);
      setHasRun(true);
      try {
        const res = await fetch("/api/cfb/season-engine/project-game", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            homeTeam,
            awayTeam,
            week,
            neutralSite,
            nightGame,
          }),
        });
        const json = (await res.json()) as ProjectPayload;
        if (!res.ok || json.error) {
          setError(
            json.error || json.hint || `Request failed (${res.status})`,
          );
          return;
        }
        setResult(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      }
    });
  }

  const uncertainty = result?.uncertainty ?? result?.early_season_uncertainty ?? {};
  const earlyActive = uncertainty.active === true;
  const drivers = result?.drivers as
    | {
        home?: Record<string, unknown>;
        away?: Record<string, unknown>;
        matchup?: Record<string, unknown>;
        player_projections?: {
          by_team?: Record<
            string,
            {
              game_script?: { script_detail?: string };
              coherence?: { applied?: boolean };
            }
          >;
          coherence_adjustments_applied?: boolean;
          script_aware?: boolean;
        };
      }
    | undefined;
  const matchup = drivers?.matchup ?? {};
  const homeAdj = (() => {
    const raw = matchup.home_coaching_adj;
    if (typeof raw === "number") return raw;
    if (raw && typeof raw === "object") {
      const own = (raw as Record<string, unknown>).own_scoring_adj;
      return typeof own === "number" ? own : null;
    }
    return null;
  })();
  const awayAdj = (() => {
    const raw = matchup.away_coaching_adj;
    if (typeof raw === "number") return raw;
    if (raw && typeof raw === "object") {
      const own = (raw as Record<string, unknown>).own_scoring_adj;
      return typeof own === "number" ? own : null;
    }
    return null;
  })();

  const home = result?.home_team ?? homeTeam;
  const away = result?.away_team ?? awayTeam;
  const homeMl = formatAmericanOdds(
    americanOddsFromWinProb(result?.home_win_prob),
  );
  const awayMl = formatAmericanOdds(
    americanOddsFromWinProb(result?.away_win_prob),
  );
  const favoriteSpread = formatFavoriteSpread(
    result?.spread_home,
    home,
    away,
  );
  const scoreLine = formatProjectedScoreLine(
    result?.expected_away_score,
    result?.expected_home_score,
  );
  const marginSd =
    num(uncertainty.effective_margin_sd) ?? result?.margin_sd ?? null;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <p className="mb-4 text-xs leading-relaxed text-kos-text/65">
          Pick two FBS teams and project a market-style line — spread, total,
          win probability with American moneyline — plus approximate QB /
          skill player hooks and the roster / unit / HFA / coaching drivers.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className={labelClass} htmlFor="cfb-away">
              Away
            </label>
            <select
              id="cfb-away"
              className={selectClass}
              value={awayTeam}
              onChange={(e) => setAwayTeam(e.target.value)}
            >
              {teams.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="cfb-home">
              Home
            </label>
            <select
              id="cfb-home"
              className={selectClass}
              value={homeTeam}
              onChange={(e) => setHomeTeam(e.target.value)}
            >
              {teams.map((t) => (
                <option key={`h-${t.code}`} value={t.code}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="cfb-week">
              Week
            </label>
            <select
              id="cfb-week"
              className={selectClass}
              value={week}
              onChange={(e) => setWeek(Number(e.target.value))}
            >
              {Array.from({ length: 16 }, (_, i) => i).map((w) => (
                <option key={w} value={w}>
                  Week {w}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col justify-end gap-2">
            <label className="flex min-h-11 items-center gap-2 text-sm text-kos-text/80">
              <input
                type="checkbox"
                className="h-4 w-4 accent-kos-gold"
                checked={neutralSite}
                onChange={(e) => setNeutralSite(e.target.checked)}
              />
              Neutral site
            </label>
            <label className="flex min-h-11 items-center gap-2 text-sm text-kos-text/80">
              <input
                type="checkbox"
                className="h-4 w-4 accent-kos-gold"
                checked={nightGame}
                onChange={(e) => setNightGame(e.target.checked)}
                disabled={neutralSite}
              />
              Night game (HFA bump)
            </label>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <button
            type="button"
            onClick={run}
            disabled={pending || homeTeam === awayTeam}
            className="min-h-11 w-full rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-5 py-2.5 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {pending ? "Projecting…" : "Project game"}
          </button>
          <p className="text-xs text-kos-text/50">
            {engineVersion
              ? `Engine ${engineVersion}`
              : "Season engine via model-service"}{" "}
            · approximate calibration · KEI is the published Edge Board line
          </p>
        </div>
      </section>

      {error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          <p className="font-semibold text-red-100">Could not project game</p>
          <p className="mt-1 text-red-200/90">{error}</p>
        </div>
      ) : null}

      {pending ? (
        <div className="rounded-xl border border-white/10 bg-black/25 px-4 py-8 text-center text-sm text-kos-text/65">
          Building strength → score → market lines…
        </div>
      ) : null}

      {!pending && !result && !error ? (
        <div className="rounded-xl border border-dashed border-white/15 bg-black/20 px-4 py-8 text-center text-sm text-kos-text/60">
          {hasRun
            ? "No projection returned."
            : "Choose a matchup and press Project game."}
        </div>
      ) : null}

      {result && !pending ? (
        <section className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <TruthStateBadges
                  states={cfbModelDeskTruthStates()}
                  testId="cfb-truth-state"
                  className="mb-2"
                />
                <h2 className="text-xl font-semibold tracking-tight text-kos-text sm:text-2xl">
                  {away} @ {home}
                  <span className="ml-2 text-sm font-normal text-kos-text/50">
                    Week {result.week}
                  </span>
                </h2>
                <p className="mt-1 text-xs text-kos-text/55">
                  {result.engine_version || engineVersion || "season engine"}
                  {result.mode ? ` · ${result.mode}` : ""}
                </p>
              </div>
              <span className="rounded-md border border-white/10 px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-kos-text/55">
                {result.fidelity ?? "approximate"}
              </span>
            </div>

            <div className="mt-5 flex flex-wrap items-end justify-between gap-3 border-b border-white/10 pb-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/45">
                  Projected score
                </p>
                <p className="mt-1 text-3xl font-semibold tabular-nums text-kos-text sm:text-4xl">
                  {scoreLine}
                </p>
                <p className="mt-1 text-xs text-kos-text/50">
                  Away – Home · coherent with spread & total
                </p>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
                  Home WP
                </p>
                <p className="mt-0.5 text-2xl font-semibold tabular-nums text-kos-gold">
                  {formatWinProb(result.home_win_prob)}
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <MarketCell
                label="Spread"
                primary={favoriteSpread}
                secondary={`Home line ${formatSpread(result.spread_home)}`}
              />
              <MarketCell
                label="Total"
                primary={formatScore(result.expected_total)}
                secondary={`${formatScore(result.expected_away_score)} + ${formatScore(result.expected_home_score)}`}
              />
              <MarketCell
                label="Moneyline"
                primary={`${home} ${homeMl}`}
                secondary={`${away} ${awayMl} · from WP (no vig)`}
              />
            </div>
            {(() => {
              const published = findCfbKeiGame(
                String(result.home_team || home),
                String(result.away_team || away),
              );
              const kei = published?.kei?.kei_spread_home;
              if (kei == null) return null;
              return (
                <p className="mt-3 text-xs text-kos-text/70">
                  Published KEI {formatSpread(kei)} · Model{" "}
                  {formatSpread(result.spread_home)} · Tag{" "}
                  {published?.kei?.tag ?? "PASS"} · used_in_spread on KEI only
                </p>
              );
            })()}

            <div
              className={`mt-4 rounded-xl border px-3 py-3 text-xs leading-relaxed ${
                earlyActive
                  ? "border-amber-400/30 bg-amber-500/10 text-amber-100/90"
                  : "border-white/10 bg-white/5 text-kos-text/65"
              }`}
            >
              <p className="font-semibold uppercase tracking-[0.12em]">
                {earlyActive
                  ? "Early-season uncertainty (W1–W4)"
                  : "Mid/late-season priors"}
              </p>
              <p className="mt-1.5">
                Margin SD{" "}
                <span className="font-semibold tabular-nums text-kos-text">
                  {formatIndex(marginSd, 1)}
                </span>
                {earlyActive ? (
                  <span className="text-amber-100/75">
                    {" "}
                    — wider than mid-season; lines are directional, not precise
                  </span>
                ) : (
                  <span className="text-kos-text/55">
                    {" "}
                    — identity priors have narrowed
                  </span>
                )}
              </p>
              {num(uncertainty.roster_identity_uncertainty) != null ||
              num(uncertainty.team_identity_uncertainty_blend) != null ? (
                <p className="mt-1 text-kos-text/55">
                  Roster/QB identity U{" "}
                  <span className="font-medium tabular-nums text-kos-text">
                    {formatIndex(
                      num(uncertainty.roster_identity_uncertainty) ??
                        num(uncertainty.team_identity_uncertainty_blend),
                      2,
                    )}
                  </span>
                </p>
              ) : null}
              <p className="mt-1 text-kos-text/50">
                {str(uncertainty.honesty) ??
                  str(uncertainty.note) ??
                  "Wide early priors; not a claim of known identity."}
              </p>
            </div>
          </div>

          {(() => {
            const playerRows =
              result.player_projections ?? result.players ?? [];
            if (!playerRows.length) return null;
            const awayRows = playerRows.filter((r) => r.team === away);
            const homeRows = playerRows.filter((r) => r.team === home);
            const ppDrivers = drivers?.player_projections ?? {};
            const awayMeta = ppDrivers.by_team?.[away];
            const homeMeta = ppDrivers.by_team?.[home];
            return (
              <div>
                <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-text/50">
                  Player hooks (approximate)
                </h3>
                <div className="grid gap-3 lg:grid-cols-2">
                  <PlayerHooksTable
                    team={away}
                    rows={awayRows}
                    scriptDetail={awayMeta?.game_script?.script_detail}
                    coherenceApplied={awayMeta?.coherence?.applied}
                  />
                  <PlayerHooksTable
                    team={home}
                    rows={homeRows}
                    scriptDetail={homeMeta?.game_script?.script_detail}
                    coherenceApplied={homeMeta?.coherence?.applied}
                  />
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-kos-text/45">
                  Role-share allocation of team pass/rush/TD pools from
                  expected points, script-aware (lead/trail) with residual
                  &quot;other&quot; and coherence soft-caps. ESPN roster names.
                  Not a full box-score engine; does not change team scores or
                  spreads.
                  {ppDrivers.script_aware
                    ? " Game-script adjustments active."
                    : ""}
                  {ppDrivers.coherence_adjustments_applied
                    ? " Coherence caps applied (see drivers.player_projections)."
                    : ""}
                </p>
              </div>
            );
          })()}

          <div>
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-text/50">
              Key drivers
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <DriverStrip
                side="away"
                team={away}
                drivers={drivers?.away}
                layers={result.away_layers}
                coachingAdj={awayAdj}
                showHfa={false}
              />
              <DriverStrip
                side="home"
                team={home}
                drivers={drivers?.home}
                layers={result.home_layers}
                coachingAdj={homeAdj}
                showHfa={!neutralSite}
              />
            </div>
          </div>

          <p className="text-[11px] leading-relaxed text-kos-text/45">
            Drivers are inspectable layer inputs — not calibrated market
            attribution. ML is converted from model win probability (no vig).
            Fidelity: {result.fidelity ?? "approximate"}. MODEL research — not a
            published handicap. KEI on the Edge Board is the action line.
          </p>
        </section>
      ) : null}
    </div>
  );
}
