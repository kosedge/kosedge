"use client";

import { useState, useTransition } from "react";
import {
  formatIndex,
  formatScore,
  formatSpread,
  formatWinProb,
  type CfbTeamOption,
} from "@/lib/cfb-season-engine-format";

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
  drivers?: Record<string, unknown>;
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

function DriverCard({
  side,
  drivers,
}: {
  side: "home" | "away";
  drivers: Record<string, unknown> | undefined;
}) {
  if (!drivers) return null;
  const unit = (drivers.unit_grades as Record<string, unknown> | undefined) ?? {};
  const coaching = (drivers.coaching as Record<string, unknown> | undefined) ?? {};
  const hfa = (drivers.home_field as Record<string, unknown> | undefined) ?? {};
  const flags = [
    coaching.new_hc ? "new HC" : null,
    coaching.new_oc ? "new OC" : null,
    coaching.new_dc ? "new DC" : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold/80">
        {side} drivers
      </p>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs text-kos-text/75">
        <div>
          <dt className="text-kos-text/45">Roster</dt>
          <dd className="font-medium text-kos-text">
            {formatIndex(num(drivers.roster_strength), 1)}
            {str(drivers.roster_fidelity) ? (
              <span className="ml-1 text-[10px] text-kos-text/40">
                {String(drivers.roster_fidelity)}
              </span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="text-kos-text/45">QB index</dt>
          <dd className="font-medium text-kos-text">
            {formatIndex(num(drivers.qb_situation_index), 2)}
            {str(drivers.qb_class) ? (
              <span className="ml-1 text-[10px] text-kos-text/40">
                {String(drivers.qb_class)}
              </span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="text-kos-text/45">OL / Skill</dt>
          <dd className="font-medium text-kos-text">
            {formatIndex(num(unit.ol), 0)} / {formatIndex(num(unit.skill), 0)}
          </dd>
        </div>
        <div>
          <dt className="text-kos-text/45">F7 / Sec</dt>
          <dd className="font-medium text-kos-text">
            {formatIndex(num(unit.front_seven), 0)} /{" "}
            {formatIndex(num(unit.secondary), 0)}
          </dd>
        </div>
        <div>
          <dt className="text-kos-text/45">O / D index</dt>
          <dd className="font-medium text-kos-text">
            {formatIndex(num(drivers.offense_index), 2)} /{" "}
            {formatIndex(num(drivers.defense_index), 2)}
          </dd>
        </div>
        <div>
          <dt className="text-kos-text/45">Early U</dt>
          <dd className="font-medium text-kos-text">
            {formatIndex(num(drivers.early_season_uncertainty), 2)}
          </dd>
        </div>
        {side === "home" ? (
          <div className="col-span-2">
            <dt className="text-kos-text/45">HFA</dt>
            <dd className="font-medium text-kos-text">
              {str(hfa.bucket) ?? "—"} · {formatIndex(num(hfa.hfa_points), 1)} pts
            </dd>
          </div>
        ) : null}
        <div className="col-span-2">
          <dt className="text-kos-text/45">Coaching</dt>
          <dd className="font-medium text-kos-text">
            {flags || "returning staff"}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export default function CfbProjectGameClient({
  teams,
  defaultHome = "UGA",
  defaultAway = "CLEM",
  defaultWeek = 1,
  engineVersion,
}: {
  teams: CfbTeamOption[];
  defaultHome?: string;
  defaultAway?: string;
  defaultWeek?: number;
  engineVersion?: string;
}) {
  const [homeTeam, setHomeTeam] = useState(defaultHome);
  const [awayTeam, setAwayTeam] = useState(defaultAway);
  const [week, setWeek] = useState(defaultWeek);
  const [neutralSite, setNeutralSite] = useState(false);
  const [nightGame, setNightGame] = useState(false);
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectPayload | null>(null);

  function run() {
    startTransition(async () => {
      setError(null);
      setResult(null);
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
            json.error ||
              json.hint ||
              `Request failed (${res.status})`,
          );
          return;
        }
        setResult(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      }
    });
  }

  const uncertainty = result?.uncertainty ?? {};
  const earlyActive = uncertainty.active === true;
  const drivers = result?.drivers as
    | { home?: Record<string, unknown>; away?: Record<string, unknown> }
    | undefined;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
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
              {Array.from({ length: 15 }, (_, i) => i + 1).map((w) => (
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

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={pending}
            className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-5 py-2.5 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25 disabled:opacity-50"
          >
            {pending ? "Projecting…" : "Project game"}
          </button>
          <p className="text-xs text-kos-text/50">
            {engineVersion
              ? `Engine ${engineVersion}`
              : "Season engine via model-service"}{" "}
            · fidelity approximate · Edge Board markets-only unchanged
          </p>
        </div>
      </section>

      {error ? (
        <p className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {result ? (
        <section className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-lg font-semibold text-kos-text">
                {result.away_team} @ {result.home_team}
                <span className="ml-2 text-sm font-normal text-kos-text/50">
                  W{result.week}
                </span>
              </h2>
              <span className="rounded-md border border-white/10 px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-kos-text/55">
                {result.fidelity ?? "approximate"}
              </span>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-3">
                <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
                  Spread (home)
                </p>
                <p className="mt-1 text-2xl font-semibold text-kos-gold">
                  {formatSpread(result.spread_home)}
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-3">
                <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
                  Total
                </p>
                <p className="mt-1 text-2xl font-semibold text-kos-text">
                  {formatScore(result.expected_total)}
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-3">
                <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
                  Home WP
                </p>
                <p className="mt-1 text-2xl font-semibold text-kos-text">
                  {formatWinProb(result.home_win_prob)}
                </p>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/25 px-3 py-3">
                <p className="text-[11px] uppercase tracking-[0.12em] text-kos-text/45">
                  Projected score
                </p>
                <p className="mt-1 text-2xl font-semibold text-kos-text">
                  {formatScore(result.expected_home_score)}–
                  {formatScore(result.expected_away_score)}
                </p>
              </div>
            </div>

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
              <p className="mt-1">
                Effective margin SD{" "}
                <span className="font-medium text-kos-text">
                  {formatIndex(
                    num(uncertainty.effective_margin_sd) ?? result.margin_sd,
                    1,
                  )}
                </span>
                {num(uncertainty.roster_identity_uncertainty) != null ? (
                  <>
                    {" "}
                    · roster/QB identity U{" "}
                    <span className="font-medium text-kos-text">
                      {formatIndex(
                        num(uncertainty.roster_identity_uncertainty),
                        2,
                      )}
                    </span>
                  </>
                ) : null}
              </p>
              <p className="mt-1 text-kos-text/55">
                {str(uncertainty.honesty) ??
                  str(uncertainty.note) ??
                  "Wide early priors; not a claim of known identity."}
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <DriverCard side="away" drivers={drivers?.away} />
            <DriverCard side="home" drivers={drivers?.home} />
          </div>

          <p className="text-[11px] text-kos-text/45">
            Drivers are inspectable layer inputs — not calibrated market
            attribution. Mode: {result.mode ?? "packaged"}.
          </p>
        </section>
      ) : null}
    </div>
  );
}
