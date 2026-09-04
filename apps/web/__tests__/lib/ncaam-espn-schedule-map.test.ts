/**
 * NCAAM ESPN schedule names → B7 identity (fail-closed).
 * Complements Python reader tests; keeps Miami FL ≠ Miami OH on ESPN labels.
 */
import { describe, expect, it } from "vitest";
import { resolveTeamId } from "@/lib/ncaam/identity";

/** ESPN-style schedule names observed on public scoreboard. */
const ESPN_SCHEDULE_NAMES = [
  { name: "Miami Hurricanes", teamId: "miami fl" },
  { name: "Miami (OH) RedHawks", teamId: "miami oh" },
  { name: "Miami (OH)", teamId: "miami oh" },
  { name: "Duke Blue Devils", teamId: "duke" },
  { name: "North Carolina Tar Heels", teamId: "north carolina" },
  { name: "Indiana State Sycamores", teamId: "indiana state" },
] as const;

describe("NCAAM ESPN schedule name → B7 map (fail-closed)", () => {
  it("resolves ESPN Miami FL / Miami OH distinctly", () => {
    const fl = resolveTeamId("Miami Hurricanes", "unknown");
    const oh = resolveTeamId("Miami (OH) RedHawks", "unknown");
    expect(fl.ok).toBe(true);
    expect(oh.ok).toBe(true);
    if (!fl.ok || !oh.ok) return;
    expect(fl.teamId).toBe("miami fl");
    expect(oh.teamId).toBe("miami oh");
    expect(fl.teamId).not.toBe(oh.teamId);
  });

  it("omits bare miami and unknown ESPN schedule aliases", () => {
    const bare = resolveTeamId("Miami", "unknown");
    expect(bare.ok).toBe(false);
    expect(bare.teamId).toBeNull();

    const unknown = resolveTeamId("ZZZ Fake U Explorers", "unknown");
    expect(unknown.ok).toBe(false);
    expect(unknown.teamId).toBeNull();
  });

  it("maps curated ESPN schedule display names without inventing", () => {
    for (const row of ESPN_SCHEDULE_NAMES) {
      const r = resolveTeamId(row.name, "unknown");
      expect(r.ok).toBe(true);
      expect(r.teamId).toBe(row.teamId);
    }
  });
});
