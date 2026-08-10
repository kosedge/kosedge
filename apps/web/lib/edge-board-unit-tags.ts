/**
 * Structural unit tags for Stat Drop / overview.
 * Real index-driven tags when available; otherwise honest em dash (no fluff).
 */

export type UnitTagInputs = {
  offenseIndex?: number | null;
  defenseIndex?: number | null;
  /** Optional role tag from intel (QB uncertainty, etc.). */
  roleTag?: string | null;
};

/**
 * Map relative unit strength to a short structural label.
 * Indexes are "higher = stronger" when present.
 */
export function structuralUnitTag(input: UnitTagInputs): string | null {
  const role = input.roleTag?.trim();
  if (role) return role.slice(0, 28);

  const off = input.offenseIndex;
  const def = input.defenseIndex;
  if (off == null && def == null) return null;

  const offBand =
    off == null ? null : off >= 1.08 ? "elite" : off <= 0.94 ? "soft" : "avg";
  const defBand =
    def == null ? null : def >= 1.08 ? "elite" : def <= 0.94 ? "soft" : "avg";

  if (offBand === "elite" && defBand === "elite") return "Two-way strength";
  if (offBand === "elite") return "Offense edge";
  if (defBand === "elite") return "Defense edge";
  if (offBand === "soft" && defBand === "soft") return "Unit questions";
  if (offBand === "soft") return "Offense questions";
  if (defBand === "soft") return "Defense questions";
  return "Balanced profile";
}
