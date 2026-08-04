"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
  formatPct,
  formatStatNumber,
  normalizeSurvivorPlanPicks,
} from "@/lib/nfl-season-engine-format";

type PlanPick = {
  team: string;
  opponent?: string | null;
  home_away?: string | null;
  win_rate: number;
  save_score?: number;
  pick_now_score?: number;
};

type PlanWeek = {
  week: number;
  status: string;
  locked_team?: string | null;
  locked_pick?: PlanPick | null;
  ranked_picks?: PlanPick[];
  available_teams?: string[];
};

type PlanPayload = {
  mode?: string;
  schedule_source?: string;
  schedule_game_count?: number;
  n_sims?: number;
  engine_version?: string;
  locked_picks?: Record<string, string>;
  used_teams?: string[];
  weeks?: PlanWeek[];
  path_survival?: number;
  path_survival_pct?: number;
  path_strength?: string;
  path_strength_geo?: number | null;
  locked_pick_count?: number;
  formula?: Record<string, string>;
  error?: string;
};

const STORAGE_KEY = "kosedge.nfl.survivor.planner.picks";
const N_SIMS = 250;

const selectClass =
  "min-h-11 w-full rounded-lg border border-white/15 bg-black/40 px-2.5 py-2 text-sm text-kos-text outline-none focus:border-kos-gold/50";
const labelClass =
  "mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/55";

function strengthTone(band: string | undefined): string {
  switch (band) {
    case "Strong":
      return "border-emerald-500/35 bg-emerald-500/10 text-emerald-100";
    case "OK":
      return "border-kos-gold/40 bg-kos-gold/10 text-kos-gold";
    case "Fragile":
      return "border-amber-500/40 bg-amber-500/10 text-amber-100";
    default:
      return "border-white/15 bg-white/5 text-kos-text/70";
  }
}

function readPicksFromUrl(): Record<string, string> | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("picks");
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, string>;
    return normalizeSurvivorPlanPicks(parsed);
  } catch {
    // Compact form: 1:KC,2:BUF
    const out: Record<string, string> = {};
    for (const part of raw.split(",")) {
      const [w, t] = part.split(":");
      if (w && t) out[w.trim()] = t.trim();
    }
    return normalizeSurvivorPlanPicks(out);
  }
}

function readPicksFromStorage(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return normalizeSurvivorPlanPicks(JSON.parse(raw) as Record<string, string>);
  } catch {
    return {};
  }
}

function compactPicksParam(picks: Record<string, string>): string {
  return Object.keys(picks)
    .sort((a, b) => Number(a) - Number(b))
    .map((w) => `${w}:${picks[w]}`)
    .join(",");
}

export default function SeasonEngineSurvivorPlannerClient({
  engineVersion,
  depthSource,
  depthAsOf,
}: {
  engineVersion?: string;
  depthSource?: string;
  depthAsOf?: string;
}) {
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [hydrated, setHydrated] = useState(false);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PlanPayload | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    const fromUrl = readPicksFromUrl();
    setPicks(fromUrl && Object.keys(fromUrl).length ? fromUrl : readPicksFromStorage());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(picks));
    } catch {
      // ignore quota
    }
    const params = new URLSearchParams(window.location.search);
    const compact = compactPicksParam(picks);
    if (compact) params.set("picks", compact);
    else params.delete("picks");
    // Keep mode=planner visible on shareable URLs.
    if (!params.get("mode")) params.set("mode", "planner");
    const qs = params.toString();
    const next = qs
      ? `${window.location.pathname}?${qs}`
      : window.location.pathname;
    window.history.replaceState(null, "", next);
  }, [picks, hydrated]);

  function evaluate(nextPicks: Record<string, string>) {
    const id = ++requestId.current;
    startTransition(async () => {
      setError(null);
      try {
        const res = await fetch("/api/nfl/season-engine/survivor/plan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            picks: nextPicks,
            nSims: N_SIMS,
            topN: 6,
          }),
        });
        const json = (await res.json()) as PlanPayload;
        if (id !== requestId.current) return;
        if (!res.ok || json.error) {
          setError(json.error || `Request failed (${res.status})`);
          return;
        }
        setResult(json);
      } catch (err) {
        if (id !== requestId.current) return;
        setError(err instanceof Error ? err.message : "Request failed");
      }
    });
  }

  useEffect(() => {
    if (!hydrated) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => evaluate(picks), 450);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- evaluate intentionally stable via picks
  }, [picks, hydrated]);

  const used = useMemo(
    () => new Set(Object.values(picks)),
    [picks],
  );

  const weeks = result?.weeks ?? [];
  const band = result?.path_strength ?? "Empty";

  function lockWeek(week: number, team: string) {
    const next = { ...picks };
    // Clear any other week using this team.
    for (const [w, t] of Object.entries(next)) {
      if (t === team) delete next[w];
    }
    next[String(week)] = team;
    setPicks(normalizeSurvivorPlanPicks(next));
  }

  function clearWeek(week: number) {
    const next = { ...picks };
    delete next[String(week)];
    setPicks(next);
  }

  function resetAll() {
    setPicks({});
    setResult(null);
    setError(null);
  }

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <p className="mb-4 text-xs leading-relaxed text-kos-text/65">
          Lock one team per week. Used teams drop from every other week&apos;s
          recommendations. Path survival is the share of season sims where{" "}
          <em>all</em> locked picks win their weeks — not pool EV.
        </p>

        <div
          className={`sticky top-[var(--kos-pro-header-h,7.5rem)] z-30 -mx-1 rounded-xl border px-4 py-4 sm:static sm:z-auto sm:mx-0 sm:px-5 ${strengthTone(band)}`}
        >
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className={labelClass}>Path survival</p>
              <p className="text-3xl font-semibold tabular-nums tracking-tight sm:text-4xl">
                {result
                  ? formatPct(result.path_survival ?? 0)
                  : pending
                    ? "…"
                    : "—"}
              </p>
              <p className="mt-1 text-xs opacity-80">
                {band === "Empty"
                  ? "No locks yet — vacuous 100% until you pick"
                  : `${band} path · geo ${(result?.path_strength_geo ?? 0).toFixed(2)} · ${result?.locked_pick_count ?? 0} locked`}
              </p>
            </div>
            <div className="shrink-0 text-left text-xs opacity-75 sm:text-right">
              <p>{result?.n_sims ?? N_SIMS} season sims</p>
              <p className="mt-0.5 break-all">
                {engineVersion || result?.engine_version || "season engine"}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <button
            type="button"
            onClick={resetAll}
            className="min-h-11 w-full rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-semibold text-kos-text/80 transition hover:border-white/30 sm:w-auto"
          >
            Reset plan
          </button>
          <p className="text-xs text-kos-text/55 break-words">
            Used: {used.size ? [...used].sort().join(", ") : "none"}
          </p>
          {(depthSource || depthAsOf) && (
            <p className="text-[11px] text-kos-text/45 break-words">
              Depth {depthSource || "—"}
              {depthAsOf ? ` · ${depthAsOf}` : ""}
            </p>
          )}
        </div>
      </section>

      {error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          <p className="font-semibold text-red-100">Planner error</p>
          <p className="mt-1 text-red-200/90">{error}</p>
        </div>
      ) : null}

      {pending && !result ? (
        <div className="rounded-xl border border-white/10 bg-black/25 px-4 py-8 text-center text-sm text-kos-text/65">
          Running season paths for the full slate…
        </div>
      ) : null}

      <section className="space-y-3">
        {weeks.map((weekRow) => {
          const week = weekRow.week;
          const lockedTeam = picks[String(week)] || weekRow.locked_team || "";
          const locked = Boolean(lockedTeam);
          const ranked = weekRow.ranked_picks ?? [];
          const available =
            weekRow.available_teams?.length
              ? weekRow.available_teams
              : ranked.map((r) => r.team);
          const selectOptions = locked
            ? Array.from(new Set([lockedTeam, ...available]))
            : available.filter((t) => !used.has(t));

          return (
            <div
              key={week}
              id={`survivor-week-${week}`}
              className={`scroll-mt-[calc(var(--kos-pro-header-h,7.5rem)+5.5rem)] rounded-xl border px-3 py-3 sm:scroll-mt-[var(--kos-pro-header-h,7.5rem)] sm:px-4 ${
                locked
                  ? "border-kos-gold/35 bg-kos-gold/5"
                  : "border-white/10 bg-black/25"
              }`}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-kos-text">
                    Week {week}
                  </p>
                  <p className="text-[11px] uppercase tracking-wide text-kos-text/45">
                    {locked ? "Locked" : "Open"}
                    {pending ? " · updating…" : ""}
                  </p>
                </div>

                <div className="flex w-full flex-col gap-2 sm:min-w-[12rem] sm:flex-1 sm:flex-row sm:flex-wrap sm:items-center">
                  <label className="sr-only" htmlFor={`plan-week-${week}`}>
                    Week {week} pick
                  </label>
                  <select
                    id={`plan-week-${week}`}
                    className={`${selectClass} sm:max-w-[14rem]`}
                    value={lockedTeam}
                    onChange={(e) => {
                      const team = e.target.value;
                      if (!team) clearWeek(week);
                      else lockWeek(week, team);
                    }}
                  >
                    {!locked ? <option value="">— pick —</option> : null}
                    {selectOptions.map((team) => (
                      <option key={team} value={team}>
                        {team}
                      </option>
                    ))}
                  </select>
                  {locked ? (
                    <button
                      type="button"
                      onClick={() => clearWeek(week)}
                      className="min-h-11 w-full rounded-lg border border-white/15 px-3 text-sm font-semibold text-kos-text/70 hover:border-white/30 sm:w-auto"
                    >
                      Clear
                    </button>
                  ) : null}
                </div>
              </div>

              {locked && weekRow.locked_pick ? (
                <p className="mt-2 text-xs text-kos-text/65">
                  {weekRow.locked_pick.opponent
                    ? `${weekRow.locked_pick.home_away === "home" ? "vs" : "@"} ${weekRow.locked_pick.opponent}`
                    : "Matchup"}
                  {" · "}
                  {formatPct(weekRow.locked_pick.win_rate)} win in sims
                </p>
              ) : null}

              {!locked && ranked.length ? (
                <div className="mt-3 grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                  {ranked.slice(0, 6).map((pick, idx) => (
                    <button
                      key={`${week}-${pick.team}`}
                      type="button"
                      onClick={() => lockWeek(week, pick.team)}
                      disabled={used.has(pick.team)}
                      className={`min-h-11 rounded-lg border px-2.5 py-2 text-left text-sm font-semibold tabular-nums transition sm:text-xs ${
                        idx === 0
                          ? "border-kos-gold/45 bg-kos-gold/15 text-kos-gold"
                          : "border-white/10 bg-white/5 text-kos-text/80 hover:border-white/25"
                      } disabled:cursor-not-allowed disabled:opacity-40`}
                    >
                      <span className="block sm:inline">
                        {pick.team}{" "}
                        <span className="opacity-70">
                          {formatPct(pick.win_rate)}
                        </span>
                      </span>
                      {pick.pick_now_score != null ? (
                        <span className="mt-0.5 block text-[11px] opacity-50 sm:ml-1 sm:mt-0 sm:inline">
                          · {formatStatNumber(pick.pick_now_score, 2)}
                        </span>
                      ) : null}
                    </button>
                  ))}
                </div>
              ) : null}

              {!locked && !ranked.length && result ? (
                <p className="mt-2 text-xs text-kos-text/55">
                  No remaining teams play this week (byes / used).
                </p>
              ) : null}
            </div>
          );
        })}

        {!weeks.length && !pending && !error ? (
          <div className="rounded-xl border border-dashed border-white/15 bg-black/20 px-4 py-8 text-center text-sm text-kos-text/60">
            Waiting for planner rankings…
          </div>
        ) : null}
      </section>

      {result?.formula?.path_survival ? (
        <p className="text-xs leading-relaxed text-kos-text/50">
          Survival: {result.formula.path_survival}
          {result.formula.path_strength
            ? ` Strength: ${result.formula.path_strength}`
            : ""}
        </p>
      ) : null}
    </div>
  );
}
