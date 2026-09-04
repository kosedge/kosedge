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
  // B7 alias expand — former high-frequency misses
  { name: "UAB Blazers", teamId: "uab" },
  { name: "Charlotte 49ers", teamId: "charlotte" },
  { name: "Furman Paladins", teamId: "furman" },
  { name: "Charleston Cougars", teamId: "charleston" },
  { name: "Sam Houston Bearkats", teamId: "sam houston state" },
  { name: "Texas A&M-Corpus Christi Islanders", teamId: "texas a&m corpus chris" },
  { name: "IU Indianapolis Jaguars", teamId: "iu indy" },
  { name: "Gardner-Webb Runnin' Bulldogs", teamId: "gardner webb" },
  { name: "Fairleigh Dickinson Knights", teamId: "fairleigh dickinson" },
  { name: "Green Bay Phoenix", teamId: "green bay" },
  { name: "Loyola Chicago Ramblers", teamId: "loyola chicago" },
  { name: "Loyola Maryland Greyhounds", teamId: "loyola md" },
  { name: "Southern Jaguars", teamId: "southern" },
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

  it("omits bare miami / loyola / southern and unknown ESPN schedule aliases", () => {
    for (const bare of ["Miami", "miami", "loyola", "southern"]) {
      const r = resolveTeamId(bare, "unknown");
      expect(r.ok).toBe(false);
      expect(r.teamId).toBeNull();
    }

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

  it("keeps peer Loyola / Southern disambiguators unique", () => {
    expect(resolveTeamId("Loyola Marymount Lions", "unknown").teamId).toBe(
      "loyola marymount",
    );
    expect(resolveTeamId("Southern Miss Golden Eagles", "unknown").teamId).toBe(
      "southern miss",
    );
    expect(resolveTeamId("Southern Illinois Salukis", "unknown").teamId).toBe(
      "southern illinois",
    );
  });
});
