"use client";

import { useMemo, useState, useTransition } from "react";
import {
  NFL_DEFAULT_N_GAME_BOX,
  NFL_SEASON_ENGINE_TEAMS,
  buildStarOutInjuryPath,
  formatDepthBadge,
  formatPct,
  formatRange,
  formatStatLabel,
  formatStatNumber,
  formatTdStat,
  isTdStat,
  positionSortKey,
  primaryStatsForPosition,
  starOutOptionsForMatchup,
} from "@/lib/nfl-season-engine-format";
import type {
  SeasonEngineMatchupOption,
  StatDist,
} from "@/lib/nfl-season-engine-format";
import {
  HIDE_PERCENTILES_LABEL,
  RANGE_LABEL,
  RANGE_TOOLTIP,
  SHOW_PERCENTILES_LABEL,
  TYPICAL_RANGE_LABEL,
  formatPercentileReveal,
} from "@/lib/nfl-range-ux";

type PlayerRow = {
  player_key: string;
  player_name: string;
  team: string;
  position: string;
  usage_role?: string;
  point_estimate: Record<string, number>;
  distributions: Record<string, StatDist>;
};

type KickingTeamLine = {
  team?: string;
  kicker_name?: string;
  fg_att?: number;
  fg_made?: number;
  xp_att?: number;
  xp_made?: number;
  points_from_fg?: number;
  points_from_xp?: number;
  points_from_kicking?: number;
  model_status?: string;
  source?: string;
};

type BoxesPayload = {
  mode?: string;
  schedule_source?: string;
  schedule_game_count?: number;
  roster_source?: string;
  roster_as_of?: string;
  season?: number;
  week?: number;
  home_team?: string;
  away_team?: string;
  n_replicates?: number;
  engine_version?: string;
  game_script_summary?: Record<string, number>;
  notes?: Record<string, string>;
  sim_depth?: { depth_label?: string; honest_precision?: boolean; n?: number };
  players?: PlayerRow[];
  kicking?: {
    home?: KickingTeamLine;
    away?: KickingTeamLine;
    team_points?: {
      home?: {
        points_from_skill_tds?: number;
        points_from_fg?: number;
        points_from_xp?: number;
        points_skill_tds_plus_kicking?: number;
      };
      away?: {
        points_from_skill_tds?: number;
        points_from_fg?: number;
        points_from_xp?: number;
        points_skill_tds_plus_kicking?: number;
      };
    };
    model_status?: string;
  };
  error?: string;
};

const selectClass =
  "min-h-11 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-kos-text outline-none focus:border-kos-gold/50";
const labelClass =
  "mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/55";

export default function SeasonEngineGameBoxesClient({
  matchups,
  defaultWeek = 1,
}: {
  matchups: SeasonEngineMatchupOption[];
  defaultWeek?: number;
  engineVersion?: string;
  depthSource?: string;
  depthAsOf?: string;
}) {
  const [matchupId, setMatchupId] = useState(matchups[0]?.id ?? "manual");
  const [homeTeam, setHomeTeam] = useState(matchups[0]?.homeTeam ?? "KC");
  const [awayTeam, setAwayTeam] = useState(matchups[0]?.awayTeam ?? "BUF");
  const [week, setWeek] = useState(matchups[0]?.week ?? defaultWeek);
  const [starOutKey, setStarOutKey] = useState("");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [baseline, setBaseline] = useState<BoxesPayload | null>(null);
  const [injured, setInjured] = useState<BoxesPayload | null>(null);
  const [hasRun, setHasRun] = useState(false);

  const starOptions = useMemo(
    () => starOutOptionsForMatchup(homeTeam, awayTeam),
    [homeTeam, awayTeam],
  );

  function applyMatchup(id: string) {
    setMatchupId(id);
    if (id === "manual") return;
    const found = matchups.find((m) => m.id === id);
    if (!found) return;
    setHomeTeam(found.homeTeam);
    setAwayTeam(found.awayTeam);
    if (found.week != null) setWeek(found.week);
    setStarOutKey("");
  }

  function run() {
    startTransition(async () => {
      setError(null);
      setBaseline(null);
      setInjured(null);
      setHasRun(true);

      const injuryPath =
        starOutKey &&
        buildStarOutInjuryPath({
          team: starOutKey.split("|")[0] ?? "",
          playerName: starOutKey.split("|")[1] ?? "",
          week,
        });

      try {
        const baseRes = await fetch("/api/nfl/season-engine/game-boxes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            homeTeam,
            awayTeam,
            week,
            nReplicates: NFL_DEFAULT_N_GAME_BOX,
          }),
        });
        const baseJson = (await baseRes.json()) as BoxesPayload;
        if (!baseRes.ok || baseJson.error) {
          setError(baseJson.error || `Request failed (${baseRes.status})`);
          return;
        }
        setBaseline(baseJson);

        if (injuryPath) {
          const injRes = await fetch("/api/nfl/season-engine/game-boxes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              homeTeam,
              awayTeam,
              week,
              nReplicates: NFL_DEFAULT_N_GAME_BOX,
              injuryPaths: [injuryPath],
            }),
          });
          const injJson = (await injRes.json()) as BoxesPayload;
          if (!injRes.ok || injJson.error) {
            setError(injJson.error || `Injury run failed (${injRes.status})`);
            return;
          }
          setInjured(injJson);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      }
    });
  }

  const active = injured ?? baseline;
  const modeNote = active?.mode === "demo" || baseline?.mode === "demo";
  const byeWarning = active?.notes?.bye_warning || baseline?.notes?.bye_warning;
  const synthetic =
    (active?.notes?.schedule_match || baseline?.notes?.schedule_match) ===
    "synthetic_matchup";

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <p className="mb-4 text-xs leading-relaxed text-kos-text/65">
          Pick a 2026 matchup (or custom teams), then project skill-player boxes
          from the season engine. Optional star-out applies an{" "}
          <span className="text-kos-text/85">out</span> injury path for that
          week only and shows side-by-side vs baseline.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2 lg:col-span-2">
            <label className={labelClass} htmlFor="matchup">
              Matchup
            </label>
            <select
              id="matchup"
              className={selectClass}
              value={matchupId}
              onChange={(e) => applyMatchup(e.target.value)}
            >
              {matchups.length === 0 ? (
                <option value="manual">
                  No slate loaded — use teams below
                </option>
              ) : null}
              {matchups.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
              <option value="manual">Custom teams…</option>
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="away">
              Away
            </label>
            <select
              id="away"
              className={selectClass}
              value={awayTeam}
              onChange={(e) => {
                setMatchupId("manual");
                setAwayTeam(e.target.value);
                setStarOutKey("");
              }}
            >
              {NFL_SEASON_ENGINE_TEAMS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="home">
              Home
            </label>
            <select
              id="home"
              className={selectClass}
              value={homeTeam}
              onChange={(e) => {
                setMatchupId("manual");
                setHomeTeam(e.target.value);
                setStarOutKey("");
              }}
            >
              {NFL_SEASON_ENGINE_TEAMS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="week">
              Week
            </label>
            <select
              id="week"
              className={selectClass}
              value={week}
              onChange={(e) => setWeek(Number(e.target.value))}
            >
              {Array.from({ length: 18 }, (_, i) => i + 1).map((w) => (
                <option key={w} value={w}>
                  Week {w}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className={labelClass} htmlFor="injury">
              Star out (optional)
            </label>
            <select
              id="injury"
              className={selectClass}
              value={starOutKey}
              onChange={(e) => setStarOutKey(e.target.value)}
            >
              <option value="">None — full strength</option>
              {starOptions.map((s) => (
                <option
                  key={`${s.team}|${s.playerName}`}
                  value={`${s.team}|${s.playerName}`}
                >
                  {s.label}
                </option>
              ))}
            </select>
            {starOptions.length === 0 ? (
              <p className="mt-1.5 text-xs text-kos-text/50">
                Quick toggles for KC, BUF, PHI, SF, DET when those teams are in
                the matchup.
              </p>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <button
            type="button"
            onClick={run}
            disabled={pending || homeTeam === awayTeam}
            className="min-h-11 w-full rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {pending ? "Simulating…" : "Project box scores"}
          </button>
          <p className="text-xs text-kos-text/55">
            Yards median + {TYPICAL_RANGE_LABEL.toLowerCase()} · TDs as P(TD) +
            expected rate
          </p>
        </div>
      </section>

      {error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          <p className="font-semibold text-red-100">Could not project boxes</p>
          <p className="mt-1 text-red-200/90">{error}</p>
          <p className="mt-2 text-xs text-red-200/70">
            Check teams/week, then retry. If this persists, the model-service
            may be unreachable.
          </p>
        </div>
      ) : null}

      {pending ? (
        <div className="rounded-xl border border-white/10 bg-black/25 px-4 py-8 text-center text-sm text-kos-text/65">
          Running Monte Carlo replicates…
        </div>
      ) : null}

      {!pending && !active && !error ? (
        <div className="rounded-xl border border-dashed border-white/15 bg-black/20 px-4 py-8 text-center text-sm text-kos-text/60">
          {hasRun
            ? "No box scores returned."
            : "Choose a matchup and press Project box scores."}
        </div>
      ) : null}

      {active && !pending ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-kos-text">
                {active.away_team} @ {active.home_team}
                {active.week != null ? ` · Week ${active.week}` : ""}
              </h2>
              <p className="mt-1 text-xs text-kos-text/60">
                {injured
                  ? "Injury scenario vs baseline below"
                  : "Projected boxes"}
              </p>
            </div>
            {active.game_script_summary ? (
              <div className="text-right">
                <p className="text-lg font-semibold tabular-nums text-kos-gold">
                  {formatPct(
                    active.game_script_summary.home_win_prob_mean ?? 0,
                    {
                      n: active.n_replicates ?? NFL_DEFAULT_N_GAME_BOX,
                      digits: 1,
                    },
                  )}
                </p>
                <p className="text-[11px] uppercase tracking-wide text-kos-text/45">
                  Home win · total{" "}
                  {(
                    active.game_script_summary.expected_total_mean ?? 0
                  ).toFixed(1)}
                </p>
              </div>
            ) : null}
          </div>

          {modeNote ? (
            <p className="rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90">
              Explicit demo schedule (demo=true) — round-robin placeholder, not
              the locked 2026 NFL schedule.
            </p>
          ) : null}

          {byeWarning || synthetic ? (
            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90">
              {synthetic ? (
                <span className="font-semibold text-amber-100">
                  Synthetic matchup / usage — not a real 2026 slate row.{" "}
                </span>
              ) : null}
              {byeWarning ||
                active?.notes?.schedule_match_detail ||
                "This home/away/week is not on the loaded schedule — hypothetical what-if boxes."}
            </p>
          ) : null}
          {!synthetic &&
          (active?.players ?? []).some((p) => Boolean(p.usage_role)) ? (
            <p className="rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/85">
              Usage roles below are model/packaged depth labels — not confirmed
              2026 snap shares.
            </p>
          ) : null}

          {active.kicking?.home || active.kicking?.away ? (
            <KickingSummary
              homeTeam={active.home_team ?? homeTeam}
              awayTeam={active.away_team ?? awayTeam}
              kicking={active.kicking}
              nReplicates={active.n_replicates}
            />
          ) : null}

          {injured && baseline ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <TeamBoxTable
                title={`${baseline.away_team} @ ${baseline.home_team} — baseline`}
                team={homeTeam}
                alsoTeam={awayTeam}
                players={baseline.players ?? []}
                nReplicates={baseline.n_replicates}
              />
              <TeamBoxTable
                title="With injury applied"
                team={homeTeam}
                alsoTeam={awayTeam}
                players={injured.players ?? []}
                highlightOut={starOutKey.split("|")[1]}
                nReplicates={injured.n_replicates}
              />
            </div>
          ) : (
            <TeamBoxTable
              title="Projected player boxes"
              team={homeTeam}
              alsoTeam={awayTeam}
              players={active.players ?? []}
              nReplicates={active.n_replicates}
            />
          )}
        </section>
      ) : null}
    </div>
  );
}

function KickingSummary({
  homeTeam,
  awayTeam,
  kicking,
  nReplicates,
}: {
  homeTeam: string;
  awayTeam: string;
  kicking?: BoxesPayload["kicking"];
  nReplicates?: number;
}) {
  if (!kicking) return null;
  const n = nReplicates ?? NFL_DEFAULT_N_GAME_BOX;
  const sides: Array<{
    label: string;
    line?: KickingTeamLine;
    pts?: {
      points_from_skill_tds?: number;
      points_from_fg?: number;
      points_from_xp?: number;
      points_skill_tds_plus_kicking?: number;
    };
  }> = [
    {
      label: awayTeam,
      line: kicking.away,
      pts: kicking.team_points?.away,
    },
    {
      label: homeTeam,
      line: kicking.home,
      pts: kicking.team_points?.home,
    },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-kos-text">
          Kicking / scoring
        </h3>
        <p className="text-[11px] text-kos-text/45">
          FG + XP ·{" "}
          {kicking.model_status === "approximate"
            ? "approximate bands"
            : "kicker layer"}{" "}
          · {formatDepthBadge(n)}
        </p>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {sides.map(({ label, line, pts }) => {
          if (!line) return null;
          const name = line.kicker_name?.trim()
            ? line.kicker_name
            : `${label} K`;
          return (
            <div
              key={label}
              className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-kos-gold">
                {label}
                <span className="ml-2 font-medium normal-case tracking-normal text-kos-text/70">
                  {name}
                </span>
              </p>
              <dl className="mt-2 grid grid-cols-3 gap-x-2 gap-y-1 text-sm tabular-nums">
                <div>
                  <dt className="text-[10px] uppercase text-kos-text/45">FG</dt>
                  <dd className="text-kos-text">
                    {formatStatNumber(line.fg_made ?? 0)}/
                    {formatStatNumber(line.fg_att ?? 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] uppercase text-kos-text/45">XP</dt>
                  <dd className="text-kos-text">
                    {formatStatNumber(line.xp_made ?? 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] uppercase text-kos-text/45">
                    Kick pts
                  </dt>
                  <dd className="text-kos-text">
                    {formatStatNumber(line.points_from_kicking ?? 0)}
                  </dd>
                </div>
              </dl>
              {pts ? (
                <p className="mt-2 text-[11px] text-kos-text/55">
                  Skill TDs {formatStatNumber(pts.points_from_skill_tds ?? 0)} +
                  FG {formatStatNumber(pts.points_from_fg ?? 0)} + XP{" "}
                  {formatStatNumber(pts.points_from_xp ?? 0)} →{" "}
                  <span className="text-kos-text/80">
                    {formatStatNumber(pts.points_skill_tds_plus_kicking ?? 0)}{" "}
                    pts
                  </span>
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TeamBoxTable({
  title,
  team,
  alsoTeam,
  players,
  highlightOut,
  nReplicates,
}: {
  title: string;
  team: string;
  alsoTeam: string;
  players: PlayerRow[];
  highlightOut?: string;
  nReplicates?: number;
}) {
  const [showPercentiles, setShowPercentiles] = useState(false);
  const ordered = [...players]
    .filter((p) => p.team === team || p.team === alsoTeam)
    .sort((a, b) => {
      if (a.team !== b.team) return a.team === team ? 1 : -1;
      const pos = positionSortKey(a.position) - positionSortKey(b.position);
      if (pos !== 0) return pos;
      return a.player_name.localeCompare(b.player_name);
    });

  const byTeam = [alsoTeam, team];

  if (!ordered.length) {
    return (
      <div className="rounded-2xl border border-white/10 bg-black/25 px-4 py-6 text-sm text-kos-text/60">
        No skill-player rows for this matchup.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 overflow-hidden">
      <div className="border-b border-white/10 px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-kos-text">{title}</h3>
            <p className="mt-0.5 text-[11px] text-kos-text/45">
              Yards: median + {TYPICAL_RANGE_LABEL.toLowerCase()}. TDs: P(TD) +
              expected rate (not median tails).{" "}
              {formatDepthBadge(nReplicates ?? NFL_DEFAULT_N_GAME_BOX)}.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowPercentiles((v) => !v)}
            className="min-h-11 shrink-0 rounded-lg px-2 text-[11px] font-semibold text-kos-gold/90 underline-offset-2 hover:underline sm:min-h-0 sm:py-1"
            title={RANGE_TOOLTIP}
          >
            {showPercentiles ? HIDE_PERCENTILES_LABEL : SHOW_PERCENTILES_LABEL}
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        {byTeam.map((t) => {
          const rows = ordered.filter((p) => p.team === t);
          if (!rows.length) return null;
          return (
            <div key={t} className="border-b border-white/5 last:border-b-0">
              <div className="bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-kos-gold">
                {t}
              </div>
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="text-[11px] uppercase tracking-wide text-kos-text/45">
                    <th className="px-4 py-2 font-medium">Player</th>
                    <th className="px-3 py-2 font-medium">Pos</th>
                    <th className="px-3 py-2 font-medium">Stat</th>
                    <th className="px-3 py-2 font-medium">Projection</th>
                    <th className="px-3 py-2 font-medium" title={RANGE_TOOLTIP}>
                      {RANGE_LABEL}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((p) => {
                    const stats = primaryStatsForPosition(p.position);
                    const out =
                      highlightOut &&
                      p.player_name.replace(/\s/g, "") ===
                        highlightOut.replace(/\s/g, "");
                    const n = nReplicates ?? NFL_DEFAULT_N_GAME_BOX;
                    return (
                      <tr
                        key={p.player_key}
                        className={`border-t border-white/5 ${
                          out ? "bg-red-500/10" : ""
                        }`}
                      >
                        <td className="px-4 py-2.5">
                          <div className="font-medium text-kos-text">
                            {p.player_name}
                            {out ? (
                              <span className="ml-2 text-[10px] font-semibold uppercase tracking-wide text-red-300">
                                out
                              </span>
                            ) : null}
                          </div>
                          {p.usage_role ? (
                            <div className="text-[11px] text-kos-text/45">
                              {p.usage_role}
                            </div>
                          ) : null}
                        </td>
                        <td className="px-3 py-2.5 text-kos-text/70">
                          {p.position}
                        </td>
                        <td className="px-3 py-2.5 text-kos-text/70">
                          <div className="space-y-1">
                            {stats.map((stat) => (
                              <div key={stat}>{formatStatLabel(stat)}</div>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-base font-semibold text-kos-gold">
                          <div className="space-y-1">
                            {stats.map((stat) => {
                              const dist = p.distributions?.[stat];
                              if (isTdStat(stat)) {
                                return (
                                  <div key={stat}>
                                    {formatTdStat(dist, { n }).primary}
                                  </div>
                                );
                              }
                              const value =
                                dist?.p50 ?? p.point_estimate?.[stat];
                              return (
                                <div key={stat}>
                                  {formatStatNumber(value ?? 0)}
                                </div>
                              );
                            })}
                          </div>
                        </td>
                        <td className="px-3 py-2.5 tabular-nums text-xs text-kos-text/55">
                          <div className="space-y-1">
                            {stats.map((stat) => {
                              const dist = p.distributions?.[stat];
                              if (isTdStat(stat)) {
                                return (
                                  <div key={stat}>
                                    {formatTdStat(dist, { n }).secondary}
                                  </div>
                                );
                              }
                              return (
                                <div key={stat} title={RANGE_TOOLTIP}>
                                  {formatRange(dist, { n })}
                                  {showPercentiles && dist ? (
                                    <div className="mt-0.5 text-[10px] text-kos-text/40">
                                      {formatPercentileReveal({
                                        p10: dist.p10,
                                        p50: dist.p50,
                                        p90: dist.p90,
                                        digits: 1,
                                      })}
                                    </div>
                                  ) : null}
                                </div>
                              );
                            })}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </div>
  );
}
