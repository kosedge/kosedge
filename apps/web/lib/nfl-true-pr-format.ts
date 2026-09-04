/**
 * Pure True PR display helpers (safe for client + server unit tests).
 */

export type DriverChipView = {
  key: string;
  title: string;
  value: string;
  detail: string;
  approximate: boolean;
  muted: boolean;
  framing?: string;
};

type DriverLike = {
  available?: boolean;
  band?: string | null;
  label?: string | null;
  band_label?: string | null;
  reason?: string | null;
  approximate?: boolean;
  framing?: string | null;
  starter_name?: string | null;
  score?: number | null;
  state?: string | null;
  preseason?: boolean;
  early_season?: boolean;
};

export function titleCaseBand(band: string | null | undefined): string {
  if (!band) return "—";
  return band
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function continuityChip(d: DriverLike): DriverChipView | null {
  if (!d?.available) return null;
  const value = titleCaseBand(d.band || d.label);
  return {
    key: "continuity",
    title: "Continuity",
    value,
    detail: d.reason || "",
    approximate: Boolean(d.approximate),
    muted: false,
  };
}

export type QbPremiumChipOptions = {
  /** When packaged depth is past camp freshness, sit the premium claim. */
  packStale?: boolean;
};

export function qbPremiumChip(
  d: DriverLike,
  options?: QbPremiumChipOptions,
): DriverChipView | null {
  if (!d) return null;
  if (options?.packStale) {
    return {
      key: "qb",
      title: "QB premium",
      value: "Sat — pack stale",
      detail:
        "Packaged depth past freshness window — named QB1 / IR / claims on Camp Desk.",
      approximate: true,
      muted: true,
    };
  }
  // Starter context can show even when magnitude is unavailable.
  if (!d.available && !d.starter_name) return null;
  const value =
    d.band && d.band_label
      ? d.band_label
      : d.band
        ? titleCaseBand(d.band)
        : d.band_label && d.band_label !== "unavailable"
          ? d.band_label
          : d.starter_name
            ? "Context only"
            : "—";
  const muted =
    !d.band && Boolean(d.starter_name || d.band_label === "Context only");
  return {
    key: "qb",
    title: "QB premium",
    value,
    detail: d.reason || "",
    approximate: Boolean(d.approximate) || muted,
    muted,
  };
}

export function pastSosChip(d: DriverLike): DriverChipView | null {
  if (!d?.available) return null;
  return {
    key: "past_sos",
    title: "Past SOS",
    value: titleCaseBand(d.band || d.label),
    detail: d.reason || "",
    approximate: Boolean(d.approximate),
    muted: false,
  };
}

export function projectedSosChip(d: DriverLike): DriverChipView | null {
  if (!d?.available) return null;
  return {
    key: "proj_sos",
    title: "2026 SOS",
    value: titleCaseBand(d.band || d.label),
    detail: d.reason || "",
    approximate: Boolean(d.approximate),
    muted: false,
    framing:
      d.framing || "Schedule outlook only — does not change intrinsic PR",
  };
}

export function blendChip(d: DriverLike): DriverChipView | null {
  if (!d?.available) return null;
  // Preseason / games 0–2: prior-heavy; never invent current-sample story.
  const early =
    Boolean(d.preseason) ||
    Boolean(d.early_season) ||
    d.state === "prior_heavy";
  return {
    key: "blend",
    title: "Blend",
    value: d.label || titleCaseBand(d.state) || "—",
    detail: d.reason || "",
    approximate: Boolean(d.approximate),
    muted: early,
  };
}

export function driverChipsForTeam(
  drivers: {
    continuity: DriverLike;
    qb_premium: DriverLike;
    past_sos: DriverLike;
    projected_sos_2026: DriverLike;
    blend: DriverLike;
  },
  options?: QbPremiumChipOptions,
): DriverChipView[] {
  return [
    continuityChip(drivers.continuity),
    qbPremiumChip(drivers.qb_premium, options),
    pastSosChip(drivers.past_sos),
    projectedSosChip(drivers.projected_sos_2026),
    blendChip(drivers.blend),
  ].filter((chip): chip is DriverChipView => chip != null);
}
