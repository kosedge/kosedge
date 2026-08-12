/**
 * Authoritative NFL research-surface labeling.
 * Every surface states what reality it is showing. August must never read as
 * “2026 Week 18 current.”
 *
 * UI state machine: LIVE | MODEL | PRESEASON | ARCHIVE
 */

import type { TruthUiState } from "@/lib/truth-ui-state";

export type NflTruthUiState = TruthUiState;

export type NflTruthSourceType =
  | "actual"
  | "model"
  | "preseason"
  | "archive"
  | "fallback";

export type NflTruthLabel = {
  season: number | null;
  /** Real REG week, or null when the display week is Preseason. */
  week: number | null;
  week_label: string;
  ui_state: NflTruthUiState;
  source_type: NflTruthSourceType;
  is_current: boolean;
  run_id: string | null;
  model_version: string | null;
  generated_at: string | null;
  data_as_of: string | null;
  /** e.g. "Season 2026 · Preseason" */
  period_line: string;
  /** Honesty / fallback note, or null when the period line is enough. */
  honesty_note: string | null;
};

/** Product season on the 2026 launch board. */
export const NFL_PRODUCT_SEASON = 2026;

/**
 * Inclusive last calendar day treated as preseason (Labor Day Monday approx).
 * Matches `PRESEASON_CUTOFF_BY_SEASON` in historical_replay.py.
 * REG Week 1 2026 is Thursday 2026-09-10.
 */
export const NFL_PRESEASON_CUTOFF_ISO: Record<number, string> = {
  2025: "2025-09-01",
  2026: "2026-09-07",
};

const DEFAULT_PRESEASON_CUTOFF_MD = "09-07";
/** After Super Bowl weekend the prior REG season is archive, not “current Week 18”. */
const SEASON_COMPLETE_MD = "02-20";

export type ResolveNflTruthLabelInput = {
  season?: number | null;
  week?: number | null;
  fallbackApplied?: boolean;
  latestSeason?: number | null;
  latestWeek?: number | null;
  now?: Date;
  inSeason?: boolean | null;
  isModelSurface?: boolean;
  launchPreseason?: boolean;
  runId?: string | null;
  modelVersion?: string | null;
  generatedAt?: string | null;
  dataAsOf?: string | null;
  productSeason?: number;
};

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function truncWeek(week: number | null | undefined): number | null {
  if (typeof week !== "number" || !Number.isFinite(week)) return null;
  const n = Math.trunc(week);
  return n >= 1 ? n : null;
}

function truncSeason(season: number | null | undefined): number | null {
  if (typeof season !== "number" || !Number.isFinite(season)) return null;
  const n = Math.trunc(season);
  return n >= 2010 && n <= 2100 ? n : null;
}

export function nflPreseasonCutoffIso(season: number): string {
  return NFL_PRESEASON_CUTOFF_ISO[season] ?? `${season}-${DEFAULT_PRESEASON_CUTOFF_MD}`;
}

export function isNflCalendarPreseason(
  season: number,
  now: Date = new Date(),
): boolean {
  return isoDate(now) <= nflPreseasonCutoffIso(season);
}

export function isNflSeasonComplete(
  season: number,
  now: Date = new Date(),
): boolean {
  return isoDate(now) > `${season + 1}-${SEASON_COMPLETE_MD}`;
}

/** MAX(week) dumps (18 REG / 19–22 postseason) are not a live August week. */
export function isNflMaxWeekFallback(week: number | null | undefined): boolean {
  const n = truncWeek(week);
  return n != null && n >= 18;
}

/**
 * Display week: real REG week, or "Preseason" / finals — never a future
 * completed week (e.g. 2026 W18 in August).
 */
export function formatNflWeekLabel(
  week: number | null | undefined,
  opts?: {
    season?: number | null;
    now?: Date;
    emptySlate?: boolean;
    archive?: boolean;
  },
): string {
  const weekN = truncWeek(week);
  const season = truncSeason(opts?.season);
  const now = opts?.now ?? new Date();

  if (weekN == null) return "Preseason";

  if (opts?.archive && weekN >= 18) {
    return season != null ? `${season} finals` : "Finals";
  }

  if (season != null && isNflCalendarPreseason(season, now)) {
    return "Preseason";
  }

  // MAX(week)=18 with no season stamp still must not read as current in August.
  if (weekN >= 18 && isNflCalendarPreseason(NFL_PRODUCT_SEASON, now)) {
    return "Preseason";
  }

  if (weekN >= 18 && opts?.emptySlate) {
    return "Preseason";
  }

  if (season != null && isNflSeasonComplete(season, now) && weekN >= 18) {
    return `${season} finals`;
  }

  return `Week ${weekN}`;
}

export function formatNflFreshnessPeriod(
  season: number | null | undefined,
  week: number | null | undefined,
  now: Date = new Date(),
): string {
  const s = truncSeason(season);
  if (s == null) return "";
  const label = formatNflWeekLabel(week, { season: s, now });
  if (label === "Preseason") return `S${s} Preseason`;
  if (label.endsWith("finals")) return `S${s} finals`;
  const weekN = truncWeek(week);
  if (weekN != null && !label.startsWith("Week")) return `S${s} ${label}`;
  return weekN != null ? `S${s} ${label}` : `S${s}`;
}

function resolveUiState(input: {
  season: number | null;
  week: number | null;
  now: Date;
  productSeason: number;
  fallbackApplied: boolean;
  latestSeason: number | null;
  inSeason: boolean | null;
  isModelSurface: boolean;
  launchPreseason: boolean;
}): { ui_state: NflTruthUiState; source_type: NflTruthSourceType; is_current: boolean } {
  const {
    season,
    week,
    now,
    productSeason,
    fallbackApplied,
    latestSeason,
    inSeason,
    isModelSurface,
    launchPreseason,
  } = input;

  const calendarPre =
    (season != null && isNflCalendarPreseason(season, now)) ||
    isNflCalendarPreseason(productSeason, now) ||
    launchPreseason;

  const dataSeason = latestSeason ?? season;
  const priorSeasonArchive =
    dataSeason != null && dataSeason < productSeason;
  const completedArchive =
    season != null &&
    isNflSeasonComplete(season, now) &&
    isNflMaxWeekFallback(week);

  if (priorSeasonArchive || completedArchive) {
    return {
      ui_state: "ARCHIVE",
      source_type: fallbackApplied ? "fallback" : "archive",
      is_current: false,
    };
  }

  if (calendarPre || (isNflMaxWeekFallback(week) && inSeason !== true)) {
    if (isModelSurface) {
      return {
        ui_state: "MODEL",
        source_type: "model",
        is_current: false,
      };
    }
    return {
      ui_state: "PRESEASON",
      source_type: fallbackApplied ? "fallback" : "preseason",
      is_current: false,
    };
  }

  if (isModelSurface) {
    return {
      ui_state: "MODEL",
      source_type: "model",
      is_current: false,
    };
  }

  const live =
    inSeason === true &&
    season === productSeason &&
    week != null &&
    week >= 1;
  return {
    ui_state: live ? "LIVE" : "ARCHIVE",
    source_type: live ? "actual" : fallbackApplied ? "fallback" : "archive",
    is_current: Boolean(live),
  };
}

export function resolveNflTruthLabel(
  input: ResolveNflTruthLabelInput = {},
): NflTruthLabel {
  const now = input.now ?? new Date();
  const productSeason = input.productSeason ?? NFL_PRODUCT_SEASON;
  const season = truncSeason(input.season);
  const rawWeek = truncWeek(input.week);
  const latestSeason = truncSeason(input.latestSeason);
  const latestWeek = truncWeek(input.latestWeek);
  const fallbackApplied = Boolean(input.fallbackApplied);

  const { ui_state, source_type, is_current } = resolveUiState({
    season,
    week: rawWeek,
    now,
    productSeason,
    fallbackApplied,
    latestSeason,
    inSeason: input.inSeason ?? null,
    isModelSurface: Boolean(input.isModelSurface),
    launchPreseason: Boolean(input.launchPreseason),
  });

  const archive = ui_state === "ARCHIVE";
  const week_label = formatNflWeekLabel(rawWeek, {
    season,
    now,
    archive,
  });
  const displayWeek =
    week_label === "Preseason" || week_label.endsWith("finals")
      ? null
      : rawWeek;

  const periodWeek =
    archive && week_label.endsWith("finals") ? "finals" : week_label;
  const period_line = season
    ? `Season ${season} · ${periodWeek}`
    : week_label;

  let honesty_note: string | null = null;
  if (ui_state === "ARCHIVE") {
    const asOfSeason = latestSeason ?? season;
    const asOfLabel = formatNflWeekLabel(latestWeek ?? rawWeek, {
      season: asOfSeason,
      now,
      archive: true,
    });
    honesty_note = `ARCHIVE · showing ${asOfLabel} (as-of) — not ${productSeason} current`;
  } else if (
    ui_state === "PRESEASON" &&
    (fallbackApplied || isNflMaxWeekFallback(rawWeek))
  ) {
    honesty_note = `PRESEASON · latest snapshot is not a completed ${productSeason} week`;
  }

  return {
    season,
    week: displayWeek,
    week_label,
    ui_state,
    source_type,
    is_current,
    run_id: input.runId ?? null,
    model_version: input.modelVersion ?? null,
    generated_at: input.generatedAt ?? null,
    data_as_of: input.dataAsOf ?? null,
    period_line,
    honesty_note,
  };
}

/** Column header when W–L may be a prior-season actual next to 2026 projections. */
export function nflActualRecordColumnLabel(
  truth: NflTruthLabel,
  productSeason = NFL_PRODUCT_SEASON,
): string {
  if (
    truth.ui_state === "ARCHIVE" &&
    truth.season != null &&
    truth.season < productSeason
  ) {
    return `${truth.season} W–L`;
  }
  if (truth.ui_state === "PRESEASON" || truth.ui_state === "MODEL") {
    return truth.season != null && truth.season < productSeason
      ? `${truth.season} W–L`
      : "W–L (none yet)";
  }
  return "W–L";
}

export function nflModelWinsColumnLabel(
  productSeason = NFL_PRODUCT_SEASON,
): string {
  return `${productSeason} E[wins]`;
}

export function nflModelPlayoffColumnLabel(
  productSeason = NFL_PRODUCT_SEASON,
): string {
  return `${productSeason} Playoff %`;
}

/** True when copy would claim a finished REG week that has not occurred. */
export function nflTruthCopyClaimsFutureWeek(text: string): boolean {
  return /\bW(?:eek)?\s*18\b/i.test(text) || /\b2026 W18\b/i.test(text);
}
