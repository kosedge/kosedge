/**
 * Week 1 injury → current path (manual v1).
 * Model stays research-fair. KEI may reprice from this book. No invented IR.
 */

export const NFL_DEPTH_PACK_AS_OF = "2026-08-13";

export const NFL_INJURY_CURRENT_CADENCE = [
  {
    gate: "Midweek report",
    action:
      "Desk notes + beat participation into injury_status / ol_roles on the depth pack. Do not edit Model.",
  },
  {
    gate: "Friday final",
    action:
      "Lock named Week 1 starters. If a QB1/skill1 is OUT, set injury_paths[] with a week window and republish the pack.",
  },
  {
    gate: "Gameday inactives",
    action:
      "Apply inactives to current depth. KEI may reprice (injury_net / QB backup drop-off). Model is not gut-edited.",
  },
] as const;

export function nflDepthPackagedBanner(asOf?: string | null): string {
  const date = (asOf || NFL_DEPTH_PACK_AS_OF).trim() || NFL_DEPTH_PACK_AS_OF;
  return `Depth as_of ${date} — not live injury feed`;
}

export function nflCurrentPathUsesPackaged(injuryPathCount: number): boolean {
  return !Number.isFinite(injuryPathCount) || injuryPathCount <= 0;
}
