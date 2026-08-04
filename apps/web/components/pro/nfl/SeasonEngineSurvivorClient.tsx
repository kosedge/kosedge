"use client";

import { useMemo, useState, useTransition } from "react";
import {
  NFL_SEASON_ENGINE_TEAMS,
  formatPct,
  formatStatNumber,
  parseAlreadyUsedTeams,
  rankSurvivorPicks,
} from "@/lib/nfl-season-engine-format";

type SurvivorPick = {
  team: string;
  opponent?: string | null;
  home_away?: string | null;
  win_rate: number;
  save_score: number;
  pick_now_score: number;
  plays_this_week?: boolean;
};

type SurvivorPayload = {
  mode?: string;
  week?: number;
  n_sims?: number;
  engine_version?: string;
  already_used?: string[];
  ranked_picks?: SurvivorPick[];
  formula?: Record<string, string>;
  notes?: Record<string, string>;
  error?: string;
};

const selectClass =
  "min-h-11 w-full rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-kos-text outline-none focus:border-kos-gold/50";
const labelClass =
  "mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/55";

export default function SeasonEngineSurvivorClient({
  defaultWeek = 1,
  engineVersion,
}: {
  defaultWeek?: number;
  engineVersion?: string;
}) {
  const [week, setWeek] = useState(defaultWeek);
  const [used, setUsed] = useState<string[]>([]);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SurvivorPayload | null>(null);

  const ranked = useMemo(
    () => rankSurvivorPicks(result?.ranked_picks ?? []),
    [result],
  );

  function toggleTeam(team: string) {
    setUsed((prev) =>
      prev.includes(team) ? prev.filter((t) => t !== team) : [...prev, team],
    );
  }

  function run() {
    startTransition(async () => {
      setError(null);
      setResult(null);
      try {
        const res = await fetch("/api/nfl/season-engine/survivor", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            week,
            alreadyUsed: used,
            nSims: 200,
            topN: 16,
          }),
        });
        const json = (await res.json()) as SurvivorPayload;
        if (!res.ok || json.error) {
          setError(json.error || `Request failed (${res.status})`);
          return;
        }
        setResult(json);
        if (Array.isArray(json.already_used)) {
          setUsed(parseAlreadyUsedTeams(json.already_used));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      }
    });
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className={labelClass} htmlFor="survivor-week">
              Future week
            </label>
            <select
              id="survivor-week"
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
          <div>
            <p className={labelClass}>Already used ({used.length})</p>
            <p className="min-h-11 rounded-lg border border-white/10 bg-black/25 px-3 py-2 text-sm text-kos-text/80">
              {used.length ? used.join(", ") : "None selected"}
            </p>
          </div>
        </div>

        <div className="mt-4">
          <p className={labelClass}>Tap teams already used in your pool</p>
          <div className="flex flex-wrap gap-2">
            {NFL_SEASON_ENGINE_TEAMS.map((team) => {
              const active = used.includes(team);
              return (
                <button
                  key={team}
                  type="button"
                  onClick={() => toggleTeam(team)}
                  className={`min-h-10 rounded-lg border px-2.5 py-1.5 text-xs font-semibold tabular-nums transition ${
                    active
                      ? "border-kos-gold/50 bg-kos-gold/20 text-kos-gold"
                      : "border-white/10 bg-white/5 text-kos-text/75 hover:border-white/25"
                  }`}
                >
                  {team}
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={pending}
            className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {pending ? "Running season sims…" : "Rank survivor picks"}
          </button>
          <button
            type="button"
            onClick={() => setUsed([])}
            className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-kos-text/80 transition hover:border-white/30"
          >
            Clear used
          </button>
          <p className="text-xs text-kos-text/55">
            {engineVersion
              ? `Engine ${engineVersion}`
              : "Season engine via model-service"}{" "}
            · 200 path sims · heuristic scores
          </p>
        </div>
      </section>

      {error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      ) : null}

      {result ? (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold text-kos-text">
              Week {result.week} ranked picks
            </h2>
            <p className="mt-1 text-xs text-kos-text/60">
              Mode: {result.mode || "—"}
              {result.engine_version ? ` · ${result.engine_version}` : ""}
              {result.n_sims ? ` · ${result.n_sims} sims` : ""}
            </p>
          </div>

          {result.mode === "demo" ? (
            <p className="rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90">
              Demo schedule mode — round-robin placeholder (no byes; explicit
              demo=true). Scores are inspectable heuristics (this-week win rate
              vs future save value), not full multi-entry pool EV.
            </p>
          ) : (
            <p className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-kos-text/70">
              Real 2026 schedule
              {result.schedule_source ? ` · ${result.schedule_source}` : ""}
              {result.schedule_game_count
                ? ` · ${result.schedule_game_count} REG games`
                : ""}
              {result.roster_as_of
                ? ` · roster as of ${result.roster_as_of}`
                : ""}
              . Scores are inspectable heuristics (this-week win rate vs future
              save value), not full multi-entry pool EV. Bye weeks are respected.
            </p>
          )}

          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-black/25">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-[11px] uppercase tracking-wide text-kos-text/45">
                  <th className="px-4 py-3 font-medium">Rank</th>
                  <th className="px-3 py-3 font-medium">Team</th>
                  <th className="px-3 py-3 font-medium">Opponent</th>
                  <th className="px-3 py-3 font-medium">This week WP</th>
                  <th className="px-3 py-3 font-medium">Save</th>
                  <th className="px-3 py-3 font-medium">Pick now</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((pick) => (
                  <tr
                    key={`${pick.rank}-${pick.team}`}
                    className="border-t border-white/5"
                  >
                    <td className="px-4 py-2.5 tabular-nums text-kos-text/60">
                      {pick.rank}
                    </td>
                    <td className="px-3 py-2.5 font-semibold text-kos-gold">
                      {pick.team}
                    </td>
                    <td className="px-3 py-2.5 text-kos-text/75">
                      {pick.opponent
                        ? `${pick.home_away === "home" ? "vs" : "@"} ${pick.opponent}`
                        : "—"}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-kos-text">
                      {formatPct(pick.win_rate)}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums text-kos-text/70">
                      {formatStatNumber(pick.save_score, 3)}
                    </td>
                    <td className="px-3 py-2.5 tabular-nums font-semibold text-kos-text">
                      {formatStatNumber(pick.pick_now_score, 3)}
                    </td>
                  </tr>
                ))}
                {!ranked.length ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-6 text-sm text-kos-text/60"
                    >
                      No remaining teams play this week after exclusions.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          {result.formula?.pick_now_score ? (
            <p className="text-xs leading-relaxed text-kos-text/50">
              Pick-now: {result.formula.pick_now_score}
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
