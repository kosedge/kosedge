"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
  formatPathDifficultyGrade,
  formatPct,
  formatScheduleDifficulty,
  normalizeSurvivorPlanPicks,
} from "@/lib/nfl-season-engine-format";

type PlanPick = {
  team: string;
  opponent?: string | null;
  home_away?: string | null;
  matchup_label?: string | null;
  win_rate: number;
  this_week_wp?: number;
  is_favorite?: boolean;
  favorite_team?: string | null;
  favorite_wp?: number;
  save_score?: number;
  pick_now_score?: number;
  schedule_difficulty?: string | null;
  path_difficulty_grade?: string | null;
  projected_sos_2026?: number | null;
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
  avg_locked_wp?: number | null;
  danger_weeks?: number;
  best_remaining_equity?: number | null;
  slate_grade?: string;
  slate_score?: number | null;
  formula?: Record<string, string>;
  error?: string;
};

type SuggestedPath = {
  id: string;
  label: string;
  blurb: string;
  picks: Record<string, string>;
  pick_count: number;
  avg_locked_wp?: number | null;
  danger_weeks?: number;
  slate_grade?: string;
  slate_score?: number | null;
};

const STORAGE_KEY = "kosedge.nfl.survivor.planner.picks";
/** Planner interactivity budget — enough for stable WPs, fast enough for lock UX. */
const N_SIMS = 120;

const selectClass =
  "min-h-11 w-full rounded-lg border border-white/15 bg-black/40 px-2.5 py-2 text-sm text-kos-text outline-none focus:border-kos-gold/50";
const labelClass =
  "mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/55";

function gradeTone(grade: string | undefined): string {
  switch (grade) {
    case "A":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-100";
    case "B":
      return "border-kos-gold/45 bg-kos-gold/10 text-kos-gold";
    case "C":
      return "border-amber-500/35 bg-amber-500/10 text-amber-100";
    case "D":
    case "F":
      return "border-red-500/35 bg-red-500/10 text-red-100";
    default:
      return "border-white/15 bg-white/5 text-kos-text/75";
  }
}

function favoriteWp(pick: PlanPick): number {
  if (typeof pick.favorite_wp === "number") return pick.favorite_wp;
  const wp = pick.this_week_wp ?? pick.win_rate;
  return pick.is_favorite === false ? Math.max(0, 1 - wp) : wp;
}

function readPicksFromUrl(): Record<string, string> | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("picks");
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, string>;
    return normalizeSurvivorPlanPicks(parsed);
  } catch {
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

function MatchupLine({ pick }: { pick: PlanPick }) {
  const team = pick.team;
  const opp = pick.opponent;
  const connector = pick.home_away === "away" ? "@" : "vs";
  const favTeam =
    pick.favorite_team || (pick.is_favorite === false ? opp || team : team);
  const wp = favoriteWp(pick);

  const renderSide = (side: string) => {
    const isFav = side === favTeam;
    return (
      <span
        className={
          isFav
            ? "font-semibold text-kos-gold"
            : "font-medium text-kos-text/55"
        }
      >
        {side}
        {isFav ? (
          <span className="ml-1 tabular-nums text-kos-gold/90">
            {formatPct(wp)}
          </span>
        ) : null}
      </span>
    );
  };

  if (!opp) {
    return (
      <span className="inline-flex flex-wrap items-baseline gap-x-1.5 text-sm">
        {renderSide(team)}
      </span>
    );
  }

  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-1.5 text-sm">
      {renderSide(team)}
      <span className="text-kos-text/35">{connector}</span>
      {renderSide(opp)}
    </span>
  );
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
  const [suggested, setSuggested] = useState<SuggestedPath[]>([]);
  const [suggestError, setSuggestError] = useState<string | null>(null);
  const [suggestPending, setSuggestPending] = useState(false);
  const [flashWeek, setFlashWeek] = useState<number | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const fromUrl = readPicksFromUrl();
    setPicks(fromUrl && Object.keys(fromUrl).length ? fromUrl : readPicksFromStorage());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      if (Object.keys(picks).length === 0) {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(picks));
      }
    } catch {
      // ignore quota
    }
    const params = new URLSearchParams(window.location.search);
    const compact = compactPicksParam(picks);
    if (compact) params.set("picks", compact);
    else params.delete("picks");
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

  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    setSuggestPending(true);
    setSuggestError(null);
    (async () => {
      try {
        const res = await fetch(
          "/api/nfl/season-engine/survivor/suggest-paths",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ picks: {}, nSims: N_SIMS }),
          },
        );
        const json = (await res.json()) as {
          paths?: SuggestedPath[];
          error?: string;
        };
        if (cancelled) return;
        if (!res.ok || json.error) {
          setSuggestError(json.error || `Suggest failed (${res.status})`);
          setSuggested([]);
          return;
        }
        setSuggested(Array.isArray(json.paths) ? json.paths.slice(0, 3) : []);
      } catch (err) {
        if (cancelled) return;
        setSuggestError(
          err instanceof Error ? err.message : "Suggest paths failed",
        );
      } finally {
        if (!cancelled) setSuggestPending(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrated]);

  const used = useMemo(() => new Set(Object.values(picks)), [picks]);
  const weeks = result?.weeks ?? [];
  const grade = result?.slate_grade ?? "Empty";
  const lockedCount = Object.keys(picks).length;

  function pulseWeek(week: number) {
    setFlashWeek(week);
    if (flashTimer.current) clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setFlashWeek(null), 520);
  }

  function lockWeek(week: number, team: string) {
    const next = { ...picks };
    for (const [w, t] of Object.entries(next)) {
      if (t === team) delete next[w];
    }
    next[String(week)] = team;
    setPicks(normalizeSurvivorPlanPicks(next));
    pulseWeek(week);
  }

  function clearWeek(week: number) {
    const next = { ...picks };
    delete next[String(week)];
    setPicks(next);
    // Drop stale server lock for this week immediately (Clear bug fix).
    setResult((prev) => {
      if (!prev?.weeks) return prev;
      return {
        ...prev,
        locked_picks: Object.fromEntries(
          Object.entries(prev.locked_picks || {}).filter(
            ([w]) => Number(w) !== week,
          ),
        ),
        used_teams: Object.values(next),
        locked_pick_count: Object.keys(next).length,
        weeks: prev.weeks.map((w) =>
          w.week === week
            ? {
                ...w,
                status: "open",
                locked_team: null,
                locked_pick: null,
              }
            : w,
        ),
      };
    });
  }

  function resetAll() {
    requestId.current += 1;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setPicks({});
    setResult(null);
    setError(null);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
    const params = new URLSearchParams(window.location.search);
    params.delete("picks");
    params.set("mode", "planner");
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
    // Re-evaluate empty slate so week chips return.
    debounceRef.current = setTimeout(() => evaluate({}), 80);
  }

  function loadSuggestedPath(path: SuggestedPath) {
    const next = normalizeSurvivorPlanPicks(path.picks || {});
    setPicks(next);
    pulseWeek(Number(Object.keys(next).sort((a, b) => Number(a) - Number(b))[0] || 1));
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.06] to-black/40">
        <div className="border-b border-white/10 px-4 py-4 sm:px-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold/80">
            Survivor command
          </p>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-kos-text/70">
            Lock one team per week. Matchups stay visible before you pick.
            Used teams are burned everywhere. Path SOS is schedule outlook —
            harder slate ≠ weaker team; E[wins] / path grades move, intrinsic
            PR does not. Metrics stay readable on a full slate — joint parlay
            survival is advanced-only.
          </p>
        </div>

        <div
          className={`sticky top-[var(--kos-pro-header-h,7.5rem)] z-30 border-b border-white/10 px-3 py-3 backdrop-blur-md sm:static sm:z-auto sm:border-b-0 sm:px-5 sm:py-4 sm:backdrop-blur-none ${gradeTone(grade)}`}
        >
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="min-w-0">
              <p className={labelClass}>Slate grade</p>
              <p className="text-3xl font-semibold tracking-tight sm:text-4xl">
                {result ? grade : pending ? "…" : "—"}
              </p>
              <p className="mt-0.5 text-[11px] opacity-75">
                {result?.slate_score != null
                  ? `Score ${result.slate_score}`
                  : lockedCount
                    ? "Updating…"
                    : "No locks yet"}
              </p>
            </div>
            <div className="min-w-0">
              <p className={labelClass}>Avg weekly WP</p>
              <p className="text-2xl font-semibold tabular-nums tracking-tight sm:text-3xl">
                {result?.avg_locked_wp != null
                  ? formatPct(result.avg_locked_wp)
                  : pending && lockedCount
                    ? "…"
                    : "—"}
              </p>
              <p className="mt-0.5 text-[11px] opacity-75">
                {lockedCount} locked
              </p>
            </div>
            <div className="min-w-0">
              <p className={labelClass}>Danger weeks</p>
              <p className="text-2xl font-semibold tabular-nums tracking-tight sm:text-3xl">
                {result && lockedCount ? (result.danger_weeks ?? 0) : "—"}
              </p>
              <p className="mt-0.5 text-[11px] opacity-75">WP &lt; 55%</p>
            </div>
            <div className="min-w-0">
              <p className={labelClass}>Best left</p>
              <p className="text-2xl font-semibold tabular-nums tracking-tight sm:text-3xl">
                {result?.best_remaining_equity != null
                  ? formatPct(result.best_remaining_equity)
                  : lockedCount && result
                    ? "Full"
                    : "—"}
              </p>
              <p className="mt-0.5 text-[11px] opacity-75">Max open chalk</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] opacity-70">
            <p>
              {result?.n_sims ?? N_SIMS} season sims ·{" "}
              {engineVersion || result?.engine_version || "season engine"}
            </p>
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="min-h-11 rounded-lg px-2 font-semibold underline-offset-2 hover:underline sm:min-h-0 sm:py-1"
            >
              {showAdvanced ? "Hide advanced" : "Advanced: joint survival"}
            </button>
          </div>
          {showAdvanced ? (
            <p className="mt-2 text-xs opacity-80">
              Joint path survival{" "}
              <span className="font-semibold tabular-nums">
                {result ? formatPct(result.path_survival ?? 0) : "—"}
              </span>
              {result?.path_strength
                ? ` · ${result.path_strength}`
                : ""}{" "}
              — share of sims where every locked pick wins (collapses on long
              parlays).
            </p>
          ) : null}
        </div>

        <div className="space-y-3 px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={resetAll}
              className="min-h-11 w-full rounded-xl border border-white/15 bg-black/30 px-4 py-2.5 text-sm font-semibold text-kos-text/85 transition hover:border-kos-gold/40 hover:text-kos-gold sm:w-auto"
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

          <div>
            <div className="mb-2 flex items-end justify-between gap-2">
              <div>
                <p className={labelClass}>AI suggested paths</p>
                <p className="text-xs text-kos-text/55">
                  Engine heuristics — chalk, balanced, contrarian save. One-click
                  load, then edit freely.
                </p>
              </div>
              {suggestPending ? (
                <span className="text-[11px] text-kos-text/45">Loading…</span>
              ) : null}
            </div>
            {suggestError ? (
              <p className="text-xs text-amber-200/90">{suggestError}</p>
            ) : null}
            <div className="grid gap-2 sm:grid-cols-3">
              {suggested.map((path) => (
                <button
                  key={path.id}
                  type="button"
                  onClick={() => loadSuggestedPath(path)}
                  className="min-h-11 rounded-xl border border-white/12 bg-black/35 px-3 py-3 text-left transition hover:border-kos-gold/45 hover:bg-kos-gold/10"
                >
                  <p className="text-sm font-semibold text-kos-gold">
                    {path.label}
                  </p>
                  <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-kos-text/55">
                    {path.blurb}
                  </p>
                  <p className="mt-2 text-[11px] tabular-nums text-kos-text/70">
                    Grade {path.slate_grade ?? "—"}
                    {path.avg_locked_wp != null
                      ? ` · avg ${formatPct(path.avg_locked_wp)}`
                      : ""}
                    {typeof path.danger_weeks === "number"
                      ? ` · ${path.danger_weeks} danger`
                      : ""}
                  </p>
                </button>
              ))}
              {!suggestPending && !suggested.length && !suggestError ? (
                <p className="text-xs text-kos-text/50 sm:col-span-3">
                  Suggested paths unavailable for this slate.
                </p>
              ) : null}
            </div>
          </div>
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
          // Trust local picks only — never fall back to stale server lock.
          const lockedTeam = picks[String(week)] || "";
          const locked = Boolean(lockedTeam);
          const ranked = weekRow.ranked_picks ?? [];
          const optimisticPick =
            ranked.find((r) => r.team === lockedTeam) || null;
          const lockedPick =
            weekRow.locked_pick?.team === lockedTeam
              ? weekRow.locked_pick
              : optimisticPick;
          const available =
            weekRow.available_teams?.length
              ? weekRow.available_teams
              : ranked.map((r) => r.team);
          const selectOptions = locked
            ? Array.from(new Set([lockedTeam, ...available.filter((t) => !used.has(t) || t === lockedTeam)]))
            : available.filter((t) => !used.has(t));
          const flashing = flashWeek === week;

          return (
            <div
              key={week}
              id={`survivor-week-${week}`}
              className={`scroll-mt-[calc(var(--kos-pro-header-h,7.5rem)+6.5rem)] rounded-xl border px-3 py-3 transition duration-300 sm:scroll-mt-[var(--kos-pro-header-h,7.5rem)] sm:px-4 ${
                locked
                  ? "border-kos-gold/40 bg-kos-gold/[0.07] shadow-[inset_0_0_0_1px_rgba(212,175,55,0.08)]"
                  : "border-white/10 bg-black/25"
              } ${flashing ? "scale-[1.01] border-kos-gold/70 bg-kos-gold/15" : ""}`}
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-kos-text">
                    Week {week}
                    <span
                      className={`ml-2 text-[11px] font-semibold uppercase tracking-wide ${
                        locked ? "text-kos-gold" : "text-kos-text/45"
                      }`}
                    >
                      {locked ? "Locked" : "Open"}
                      {pending ? " · syncing…" : ""}
                    </span>
                  </p>
                  {locked && lockedPick ? (
                    <div className="mt-1.5">
                      <MatchupLine pick={lockedPick} />
                    </div>
                  ) : locked ? (
                    <p className="mt-1.5 text-sm font-semibold text-kos-gold">
                      {lockedTeam}
                    </p>
                  ) : null}
                </div>

                <div className="flex w-full flex-col gap-2 sm:min-w-[12rem] sm:flex-1 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end">
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
                    {locked ? <option value="">— clear —</option> : null}
                    {selectOptions.map((team) => (
                      <option key={team} value={team}>
                        {team}
                        {used.has(team) && team !== lockedTeam ? " (used)" : ""}
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

              {!locked && ranked.length ? (
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {ranked.slice(0, 6).map((pick, idx) => {
                    const burned = used.has(pick.team);
                    return (
                      <button
                        key={`${week}-${pick.team}`}
                        type="button"
                        onClick={() => lockWeek(week, pick.team)}
                        disabled={burned}
                        className={`min-h-11 rounded-lg border px-3 py-2.5 text-left transition ${
                          idx === 0 && !burned
                            ? "border-kos-gold/45 bg-kos-gold/15"
                            : "border-white/10 bg-white/[0.04] hover:border-white/25"
                        } disabled:cursor-not-allowed disabled:opacity-35`}
                      >
                        <MatchupLine pick={pick} />
                        {pick.schedule_difficulty ? (
                          <span className="mt-1 block text-[11px] text-kos-text/50">
                            {formatScheduleDifficulty(pick.schedule_difficulty)}
                            {pick.path_difficulty_grade
                              ? ` · path ${formatPathDifficultyGrade(pick.path_difficulty_grade)}`
                              : ""}
                          </span>
                        ) : null}
                        <span className="mt-1 block text-[11px] text-kos-text/45">
                          {burned
                            ? "Already used"
                            : idx === 0
                              ? "Top lean · tap to lock"
                              : "Tap to lock"}
                        </span>
                      </button>
                    );
                  })}
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

      {result?.formula?.avg_locked_wp || result?.formula?.slate_grade ? (
        <div className="space-y-1 text-xs leading-relaxed text-kos-text/50">
          {result.formula.avg_locked_wp ? (
            <p>Avg WP: {result.formula.avg_locked_wp}</p>
          ) : null}
          {result.formula.danger_weeks ? (
            <p>Danger: {result.formula.danger_weeks}</p>
          ) : null}
          {result.formula.slate_grade ? (
            <p>Grade: {result.formula.slate_grade}</p>
          ) : null}
          {result.formula.best_remaining_equity ? (
            <p>Best left: {result.formula.best_remaining_equity}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
