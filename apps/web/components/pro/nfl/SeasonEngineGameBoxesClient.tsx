"use client";

import { useMemo, useState, useTransition } from "react";
import {
  NFL_SEASON_ENGINE_TEAMS,
  buildStarOutInjuryPath,
  formatRange,
  formatStatLabel,
  formatStatNumber,
  positionSortKey,
  primaryStatsForPosition,
  starOutOptionsForMatchup,
} from "@/lib/nfl-season-engine-format";
import type { SeasonEngineMatchupOption } from "@/lib/nfl-season-engine-format";

type PlayerRow = {
  player_key: string;
  player_name: string;
  team: string;
  position: string;
  usage_role?: string;
  point_estimate: Record<string, number>;
  distributions: Record<
    string,
    { mean: number; std: number; p10: number; p50: number; p90: number }
  >;
};

type BoxesPayload = {
  mode?: string;
  season?: number;
  week?: number;
  home_team?: string;
  away_team?: string;
  n_replicates?: number;
  engine_version?: string;
  game_script_summary?: Record<string, number>;
  notes?: Record<string, string>;
  players?: PlayerRow[];
  error?: string;
};

const selectClass =
  "min-h-11 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-kos-text outline-none focus:border-kos-gold/50";
const labelClass =
  "mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/55";

export default function SeasonEngineGameBoxesClient({
  matchups,
  defaultWeek = 1,
  engineVersion,
}: {
  matchups: SeasonEngineMatchupOption[];
  defaultWeek?: number;
  engineVersion?: string;
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
            nReplicates: 50,
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
              nReplicates: 50,
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

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="sm:col-span-2 lg:col-span-2">
            <label className={labelClass} htmlFor="matchup">
              Upcoming matchup
            </label>
            <select
              id="matchup"
              className={selectClass}
              value={matchupId}
              onChange={(e) => applyMatchup(e.target.value)}
            >
              {matchups.length === 0 ? (
                <option value="manual">No schedule slate — use teams</option>
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
              Injury scenario (optional)
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
                Named demo stars available for KC, BUF, PHI, SF, DET matchups.
              </p>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={pending || homeTeam === awayTeam}
            className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {pending ? "Simulating…" : "Project box scores"}
          </button>
          <p className="text-xs text-kos-text/55">
            {engineVersion
              ? `Engine ${engineVersion}`
              : "Season engine via model-service"}{" "}
            · 50 replicates · p50 with p10–p90 range
          </p>
        </div>
      </section>

      {error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      {active ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-kos-text">
                {active.away_team} @ {active.home_team}
                {active.week != null ? ` · Week ${active.week}` : ""}
              </h2>
              <p className="mt-1 text-xs text-kos-text/60">
                Mode: {active.mode || "—"}
                {active.engine_version
                  ? ` · ${active.engine_version}`
                  : ""}
                {injured ? " · injured view vs baseline available below" : ""}
              </p>
            </div>
            {active.game_script_summary ? (
              <p className="text-xs tabular-nums text-kos-text/65">
                Home WP{" "}
                {(
                  (active.game_script_summary.home_win_prob_mean ?? 0) * 100
                ).toFixed(1)}
                % · Total{" "}
                {(active.game_script_summary.expected_total_mean ?? 0).toFixed(
                  1,
                )}
              </p>
            ) : null}
          </div>

          {modeNote ? (
            <p className="rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90">
              Demo schedule mode — round-robin placeholder (explicit demo=true),
              not the locked 2026 NFL schedule. Player cores are sparse outside
              named skill teams.
            </p>
          ) : active ? (
            <p className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/70">
              Real 2026 schedule
              {active.schedule_source ? ` · ${active.schedule_source}` : ""}
              {active.schedule_game_count
                ? ` · ${active.schedule_game_count} REG games`
                : ""}
              {active.roster_source ? ` · roster ${active.roster_source}` : ""}
              {active.roster_as_of ? ` (as of ${active.roster_as_of})` : ""}
            </p>
          ) : null}

          {injured && baseline ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <TeamBoxTable
                title={`${baseline.away_team} @ ${baseline.home_team} — baseline`}
                team={homeTeam}
                alsoTeam={awayTeam}
                players={baseline.players ?? []}
              />
              <TeamBoxTable
                title="With injury applied"
                team={homeTeam}
                alsoTeam={awayTeam}
                players={injured.players ?? []}
                highlightOut={starOutKey.split("|")[1]}
              />
            </div>
          ) : (
            <TeamBoxTable
              title="Projected player boxes"
              team={homeTeam}
              alsoTeam={awayTeam}
              players={active.players ?? []}
            />
          )}
        </section>
      ) : null}
    </div>
  );
}

function TeamBoxTable({
  title,
  team,
  alsoTeam,
  players,
  highlightOut,
}: {
  title: string;
  team: string;
  alsoTeam: string;
  players: PlayerRow[];
  highlightOut?: string;
}) {
  const ordered = [...players]
    .filter((p) => p.team === team || p.team === alsoTeam)
    .sort((a, b) => {
      if (a.team !== b.team) return a.team === team ? 1 : -1;
      const pos = positionSortKey(a.position) - positionSortKey(b.position);
      if (pos !== 0) return pos;
      return a.player_name.localeCompare(b.player_name);
    });

  const byTeam = [alsoTeam, team];

  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 overflow-hidden">
      <div className="border-b border-white/10 px-4 py-3">
        <h3 className="text-sm font-semibold text-kos-text">{title}</h3>
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
                    <th className="px-3 py-2 font-medium">Primary</th>
                    <th className="px-3 py-2 font-medium">p50</th>
                    <th className="px-3 py-2 font-medium">p10–p90</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((p) => {
                    const stats = primaryStatsForPosition(p.position);
                    const out =
                      highlightOut &&
                      p.player_name.replace(/\s/g, "") ===
                        highlightOut.replace(/\s/g, "");
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
                        <td className="px-3 py-2.5 tabular-nums text-kos-gold">
                          <div className="space-y-1">
                            {stats.map((stat) => {
                              const dist = p.distributions?.[stat];
                              const value = dist?.p50 ?? p.point_estimate?.[stat];
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
                            {stats.map((stat) => (
                              <div key={stat}>
                                {formatRange(p.distributions?.[stat])}
                              </div>
                            ))}
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
