/**
 * Pure display-honesty helpers (safe for client + server).
 * Store I/O lives in `display-honesty.ts` (server-only).
 */
import type { ConfidenceBand } from "@/lib/nfl-decision-engine";

/** Flag keys must match `^[A-Za-z0-9_-]+$`. */
export const DISPLAY_HONESTY_FLAG_KEYS = {
  propsConfidence: "nfl_props_confidence_display",
  propsOffMarkets: "nfl_props_confidence_display_off_markets",
  gameBand: "nfl_game_confidence_band_display",
  note: "display_suppression_note",
  meta: "display_suppression_meta",
} as const;

export type DisplayOnOff = "on" | "off";

export type DisplaySuppressionMeta = {
  actor?: string;
  reason?: string;
  setAt?: string;
  trackingPr?: string;
};

export type DisplayHonestyFlags = {
  nfl_props_confidence_display: DisplayOnOff;
  nfl_props_confidence_display_off_markets: string[];
  nfl_game_confidence_band_display: DisplayOnOff;
  display_suppression_note: string;
  display_suppression_meta: DisplaySuppressionMeta | null;
  /** Where the snapshot came from. */
  source: "global-config" | "fallback";
};

const FLAG_KEY_RE = /^[A-Za-z0-9_-]+$/;

const ALL_ON: Omit<DisplayHonestyFlags, "source"> = {
  nfl_props_confidence_display: "on",
  nfl_props_confidence_display_off_markets: [],
  nfl_game_confidence_band_display: "on",
  display_suppression_note: "",
  display_suppression_meta: null,
};

/** Exactly `"off"` (case-sensitive trim) means off; everything else is on. */
export function parseOnOff(value: unknown): DisplayOnOff {
  if (typeof value === "string" && value.trim() === "off") return "off";
  return "on";
}

export function parseOffMarkets(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const out: string[] = [];
  for (const item of value) {
    if (typeof item !== "string") continue;
    const key = item.trim();
    if (!key || !FLAG_KEY_RE.test(key)) continue;
    out.push(key);
  }
  return out;
}

export function parseSuppressionMeta(
  value: unknown,
): DisplaySuppressionMeta | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  const meta: DisplaySuppressionMeta = {};
  if (typeof raw.actor === "string") meta.actor = raw.actor;
  if (typeof raw.reason === "string") meta.reason = raw.reason;
  if (typeof raw.setAt === "string") meta.setAt = raw.setAt;
  if (typeof raw.trackingPr === "string") meta.trackingPr = raw.trackingPr;
  return Object.keys(meta).length ? meta : null;
}

export function parseDisplayHonestyFlags(
  items: Partial<Record<string, unknown>> | null | undefined,
  source: DisplayHonestyFlags["source"],
): DisplayHonestyFlags {
  const bag = items ?? {};
  return {
    nfl_props_confidence_display: parseOnOff(
      bag[DISPLAY_HONESTY_FLAG_KEYS.propsConfidence],
    ),
    nfl_props_confidence_display_off_markets: parseOffMarkets(
      bag[DISPLAY_HONESTY_FLAG_KEYS.propsOffMarkets],
    ),
    nfl_game_confidence_band_display: parseOnOff(
      bag[DISPLAY_HONESTY_FLAG_KEYS.gameBand],
    ),
    display_suppression_note:
      typeof bag[DISPLAY_HONESTY_FLAG_KEYS.note] === "string"
        ? String(bag[DISPLAY_HONESTY_FLAG_KEYS.note]).trim()
        : "",
    display_suppression_meta: parseSuppressionMeta(
      bag[DISPLAY_HONESTY_FLAG_KEYS.meta],
    ),
    source,
  };
}

export function failOpenDisplayHonestyFlags(): DisplayHonestyFlags {
  return { ...ALL_ON, source: "fallback" };
}

export function isPropsConfidenceDisplayOff(
  flags: Pick<DisplayHonestyFlags, "nfl_props_confidence_display">,
): boolean {
  return flags.nfl_props_confidence_display === "off";
}

export function isGameConfidenceBandDisplayOff(
  flags: Pick<DisplayHonestyFlags, "nfl_game_confidence_band_display">,
): boolean {
  return flags.nfl_game_confidence_band_display === "off";
}

/**
 * Props confidence is suppressed when the global props flag is off, or when
 * this marketKey is listed in the off-markets subset.
 */
export function shouldSuppressPropsConfidence(
  marketKey: string | null | undefined,
  flags: Pick<
    DisplayHonestyFlags,
    "nfl_props_confidence_display" | "nfl_props_confidence_display_off_markets"
  >,
): boolean {
  if (isPropsConfidenceDisplayOff(flags)) return true;
  const mk = String(marketKey ?? "").trim();
  if (!mk) return false;
  return flags.nfl_props_confidence_display_off_markets.includes(mk);
}

/**
 * Display value for props confidence. Suppression returns null (em dash via
 * formatConfidence) — never 0, which would render as "0%".
 */
export function displayConfidenceForProps(
  value: number | null | undefined,
  marketKey: string | null | undefined,
  flags: Pick<
    DisplayHonestyFlags,
    "nfl_props_confidence_display" | "nfl_props_confidence_display_off_markets"
  >,
): number | null {
  if (shouldSuppressPropsConfidence(marketKey, flags)) return null;
  if (value === null || value === undefined) return null;
  if (!Number.isFinite(value)) return null;
  return value;
}

export function anyDisplaySuppressionActive(
  flags: Pick<
    DisplayHonestyFlags,
    | "nfl_props_confidence_display"
    | "nfl_props_confidence_display_off_markets"
    | "nfl_game_confidence_band_display"
  >,
): boolean {
  return (
    isPropsConfidenceDisplayOff(flags) ||
    isGameConfidenceBandDisplayOff(flags) ||
    flags.nfl_props_confidence_display_off_markets.length > 0
  );
}

/** Operator/subscriber-safe note when any suppression flag is active. */
export function displaySuppressionNoteForUi(
  flags: DisplayHonestyFlags,
): string | null {
  if (!anyDisplaySuppressionActive(flags)) return null;
  const note = flags.display_suppression_note.trim();
  if (note) return note;
  return "Some confidence numbers are temporarily hidden while we verify calibration.";
}

/**
 * Edge Board confidence line. When the game-band flag is off, always show a
 * suppressed label (never vanish). Otherwise keep prior behavior: no band → null.
 */
export function formatGameConfidenceLabel(
  band?: ConfidenceBand | null,
  score?: number | null,
  tierConstant?: boolean,
  opts?: { suppressed?: boolean },
): string | null {
  if (opts?.suppressed) return "Conf —";
  if (!band) return null;
  if (tierConstant || score == null) return `Conf ${band}`;
  return `Conf ${band} ${Math.round(score * 100)}%`;
}
