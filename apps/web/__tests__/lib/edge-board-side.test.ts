import { describe, expect, it } from "vitest";
import { flatRowsToLegacy } from "@/components/EdgeBoard";

describe("edge board side + play action", () => {
  it("favors home when KEI home spread is stiffer than market home", () => {
    // Odds API best = away line. Away -3 ⇒ home +3. KEI home -7 ⇒ lean Home.
    const rows = flatRowsToLegacy(
      [
        {
          game: "Buffalo Bills @ Kansas City Chiefs",
          market: "Spread",
          best: "-3.0",
          bookKey: "draftkings",
          book: "DraftKings",
          kei: "-7.0",
          commenceTime: "2026-09-10T00:00:00Z",
        },
        {
          game: "Buffalo Bills @ Kansas City Chiefs",
          market: "Total",
          best: "47.5",
          bookKey: "fanduel",
          book: "FanDuel",
          kei: "44.0",
          commenceTime: "2026-09-10T00:00:00Z",
        },
      ],
      "nfl",
    );
    expect(rows).toHaveLength(1);
    const row = rows[0];
    expect(row.edgeLineFavor).toBe("Chiefs");
    expect(row.playLine).toBe("Chiefs +3");
    expect(row.edgeOUFavor).toBe("Under");
    expect(row.playOU).toBe("Under 47.5");
    expect(row.tagLine).toBe("PLAY"); // abs 10
    expect(row.tagOU).toBe("PLAY"); // abs 3.5 ≥ 2.5
    expect(row.edgeOUCaution).toBe(true); // ≥3 → size down
  });

  it("favors away when KEI home spread is softer than market home", () => {
    // Away +7 ⇒ home -7. KEI home -2 ⇒ lean Away.
    const rows = flatRowsToLegacy(
      [
        {
          game: "Buffalo Bills @ Kansas City Chiefs",
          market: "Spread",
          best: "+7.0",
          bookKey: "draftkings",
          kei: "-2.0",
        },
        {
          game: "Buffalo Bills @ Kansas City Chiefs",
          market: "Total",
          best: "44.0",
          bookKey: "draftkings",
          kei: "48.5",
        },
      ],
      "nfl",
    );
    const row = rows[0];
    expect(row.edgeLineFavor).toBe("Bills");
    expect(row.playLine).toBe("Bills +7.0");
    expect(row.edgeOUFavor).toBe("Over");
    expect(row.playOU).toBe("Over 44.0");
  });

  it("applies NFL spread/total tag bands", () => {
    // Odds best = away line. Away -3 ⇒ market home +3.
    const mid = flatRowsToLegacy(
      [
        { game: "A @ B", market: "Spread", best: "-3.0", bookKey: "dk", kei: "+1.8" }, // |1.8-3|=1.2 → LEAN
        { game: "A @ B", market: "Total", best: "45.0", bookKey: "dk", kei: "47.2" }, // 2.2 → LEAN
      ],
      "nfl",
    )[0];
    expect(mid.tagLine).toBe("LEAN");
    expect(mid.tagOU).toBe("LEAN");
    expect(mid.edgeOUCaution).toBe(false);

    const play = flatRowsToLegacy(
      [
        { game: "A @ B", market: "Spread", best: "+3.0", bookKey: "dk", kei: "-1.0" },
        { game: "A @ B", market: "Total", best: "45.0", bookKey: "dk", kei: "47.7" }, // 2.7 → PLAY
      ],
      "nfl",
    )[0];
    expect(play.tagOU).toBe("PLAY");
    expect(play.edgeOUCaution).toBe(false);

    const bigTotal = flatRowsToLegacy(
      [
        { game: "A @ B", market: "Spread", best: "-3.0", bookKey: "dk", kei: "-3.0" },
        { game: "A @ B", market: "Total", best: "45.0", bookKey: "dk", kei: "50.2" }, // 5.2 → PLAY + size down
      ],
      "nfl",
    )[0];
    expect(bigTotal.tagOU).toBe("PLAY");
    expect(bigTotal.edgeOUCaution).toBe(true);

    const pass = flatRowsToLegacy(
      [
        { game: "A @ B", market: "Spread", best: "-3.0", bookKey: "dk", kei: "+2.5" }, // 0.5 → PASS
        { game: "A @ B", market: "Total", best: "45.0", bookKey: "dk", kei: "46.5" }, // 1.5 → PASS
      ],
      "nfl",
    )[0];
    expect(pass.tagLine).toBe("PASS");
    expect(pass.tagOU).toBe("PASS");
  });
});
