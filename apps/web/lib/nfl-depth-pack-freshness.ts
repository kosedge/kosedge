/**
 * Packaged NFL depth freshness + competition labels (display only).
 *
 * Authoritative pack: services/model-service/.../nfl_depth_chart_2026_w1.json
 * (snapshot_id nfl-depth-2026-w1-20260813T120000Z). No remat — stamps only.
 */

/** Pack `as_of` date (YYYY-MM-DD) from the packaged SoT. */
export const NFL_DEPTH_PACK_AS_OF = "2026-08-13";

/** Pack `snapshot_policy.max_age_days_camp_season`. */
export const NFL_DEPTH_PACK_MAX_AGE_DAYS = 7;

export const NFL_DEPTH_PACK_SNAPSHOT_ID = "nfl-depth-2026-w1-20260813T120000Z";

const COMPETITION_LABELS: Record<string, string> = {
  open_competition: "Open competition",
  named_starter: "Named starter",
  camp_arm: "Camp arm",
};

/** Competition statuses that must not read as a locked starter crown. */
const OPENISH = new Set(["open_competition", "camp_arm"]);

function utcDayMs(isoDate: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate.trim());
  if (!m) return null;
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

/** Whole UTC days since pack as_of (0 on as_of day). */
export function packagedDepthAgeDays(
  now: Date = new Date(),
  asOf: string = NFL_DEPTH_PACK_AS_OF,
): number | null {
  const start = utcDayMs(asOf);
  if (start == null) return null;
  const today = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  );
  return Math.floor((today - start) / 86_400_000);
}

export function isPackagedDepthStale(
  now: Date = new Date(),
  asOf: string = NFL_DEPTH_PACK_AS_OF,
  maxAgeDays: number = NFL_DEPTH_PACK_MAX_AGE_DAYS,
): boolean {
  const age = packagedDepthAgeDays(now, asOf);
  if (age == null) return true;
  return age > maxAgeDays;
}

/** Subscriber English for competition_status (null when unknown/empty). */
export function formatCompetitionStatus(
  status: string | null | undefined,
): string | null {
  if (typeof status !== "string") return null;
  const key = status.trim().toLowerCase();
  if (!key) return null;
  if (COMPETITION_LABELS[key]) return COMPETITION_LABELS[key];
  // Fallback: humanize unknown snake_case without inventing meaning.
  return key
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/** Alias used by PR 447 / CoS notes — same helper as formatCompetitionStatus. */
export const formatCompetitionLabel = formatCompetitionStatus;

/**
 * Depth slot for display. Pack sometimes stores competition_status in
 * depth_slot (ATL/CLE QB open races) — never show raw snake_case as a slot.
 */
export function formatDepthSlotLabel(
  slot: string | null | undefined,
  depthOrder: number,
): string {
  const raw = typeof slot === "string" ? slot.trim().toLowerCase() : "";
  if (!raw || COMPETITION_LABELS[raw] || OPENISH.has(raw)) {
    if (depthOrder <= 1) return "starter";
    if (depthOrder === 2) return "backup";
    if (depthOrder === 3) return "rotation";
    return "depth";
  }
  return raw;
}

/**
 * Intel table cell formatter for depth_slot / competition_status columns
 * (Roster Pulse, league Rosters, etc.). Returns null when the column should
 * fall through to generic intel formatting.
 *
 * Never returns raw snake_case for competition-as-slot values.
 */
export function formatCompetitionAwareIntelCell(
  columnKey: string,
  value: unknown,
): string | null {
  if (columnKey !== "depth_slot" && columnKey !== "competition_status") {
    return null;
  }
  if (typeof value !== "string") {
    if (value == null) return "—";
    if (typeof value === "number" && Number.isFinite(value)) {
      return String(value);
    }
    return "—";
  }
  const raw = value.trim();
  if (!raw) return "—";
  if (columnKey === "competition_status") {
    return formatCompetitionStatus(raw) ?? "—";
  }
  // depth_slot: competition statuses (and any snake_case) → subscriber English
  if (raw.includes("_") || COMPETITION_LABELS[raw.toLowerCase()]) {
    return formatCompetitionStatus(raw) ?? raw;
  }
  return raw;
}

export function competitionImpliesOpenRace(
  status: string | null | undefined,
): boolean {
  if (typeof status !== "string") return false;
  return OPENISH.has(status.trim().toLowerCase());
}
