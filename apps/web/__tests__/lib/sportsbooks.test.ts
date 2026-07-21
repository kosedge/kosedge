import { describe, expect, it } from "vitest";
import { getSportsbook, sportsbookHomepage } from "@/lib/sportsbooks";

describe("sportsbooks", () => {
  it("resolves by Odds API key and display name", () => {
    expect(getSportsbook("draftkings")?.short).toBe("DK");
    expect(getSportsbook("DraftKings")?.key).toBe("draftkings");
    expect(sportsbookHomepage("fanduel")).toBe("https://www.fanduel.com");
  });
});
