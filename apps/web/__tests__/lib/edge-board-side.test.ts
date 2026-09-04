import { describe, expect, it } from "vitest";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";

describe("edge board side + play action", () => {
  it("favors home when KEI home spread is stiffer than market home", () => {
    // Odds API best = away line. Away -3 ⇒ home +3. KEI home -7 ⇒ lean Home.
    // |edge|=10 ≥ SPREAD_PLAY_MAX(7) → NFL PASS (mega-edge band).
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
    expect(row.edgeLineNum).toBe(10);
    expect(row.tagLine).toBe("PASS"); // mega-edge ≥7
    expect(row.tagOU).toBe("PASS"); // totals sides-only launch
    expect(row.edgeOUCaution).toBe(true); // ≥3 → size down
  });

  it("favors away when KEI home spread is softer than market home", () => {
    // Away +7 ⇒ home -7. KEI home -2 ⇒ lean Away. |edge|=5 → PLAY band.
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
    expect(row.tagLine).toBe("PLAY");
  });

  it("applies NFL spread/total tag bands", () => {
    // Odds best = away line. Away -3 ⇒ market home +3.
    const mid = flatRowsToLegacy(
      [
        {
          game: "A @ B",
          market: "Spread",
          best: "-3.0",
          bookKey: "dk",
          kei: "+1.8",
        }, // |1.8-3|=1.2 → below PLAY band; LEAN disabled → PASS
        {
          game: "A @ B",
          market: "Total",
          best: "45.0",
          bookKey: "dk",
          kei: "47.2",
        }, // totals sides-only → PASS
      ],
      "nfl",
    )[0];
    expect(mid.tagLine).toBe("PASS");
    expect(mid.tagOU).toBe("PASS");
    expect(mid.edgeOUCaution).toBe(false);

    const play = flatRowsToLegacy(
      [
        {
          game: "A @ B",
          market: "Spread",
          best: "+3.0",
          bookKey: "dk",
          kei: "-1.0",
        }, // market home -3, kei -1 → |2| → PASS (<2.5)
        {
          game: "A @ B",
          market: "Total",
          best: "45.0",
          bookKey: "dk",
          kei: "47.7",
        },
      ],
      "nfl",
    )[0];
    expect(play.tagLine).toBe("PASS");
    expect(play.tagOU).toBe("PASS");

    const spreadPlay = flatRowsToLegacy(
      [
        {
          game: "A @ B",
          market: "Spread",
          best: "+3.0",
          bookKey: "dk",
          kei: "-1.0",
        },
        // Remap: away +6 ⇒ home -6; kei -3 ⇒ |3| in PLAY band
        {
          game: "C @ D",
          market: "Spread",
          best: "+6.0",
          bookKey: "dk",
          kei: "-3.0",
        },
        {
          game: "C @ D",
          market: "Total",
          best: "45.0",
          bookKey: "dk",
          kei: "46.0",
        },
      ],
      "nfl",
    ).find((r) => r.teamA.name === "C");
    expect(spreadPlay?.tagLine).toBe("PLAY");
    expect(spreadPlay?.edgeLineNum).toBe(3);

    const pass = flatRowsToLegacy(
      [
        {
          game: "A @ B",
          market: "Spread",
          best: "-3.0",
          bookKey: "dk",
          kei: "+2.5",
        }, // 0.5 → PASS
        {
          game: "A @ B",
          market: "Total",
          best: "45.0",
          bookKey: "dk",
          kei: "46.5",
        },
      ],
      "nfl",
    )[0];
    expect(pass.tagLine).toBe("PASS");
    expect(pass.tagOU).toBe("PASS");
  });

  it("MLB moneyline edge uses no-vig prob points (no American flip)", () => {
    // Market: away +120 / home -140 → no-vig home ≈ 0.5652
    // Model homeWinProb 0.60 → +3.48pp → lean Home / PLAY
    const rows = flatRowsToLegacy(
      [
        {
          game: "New York Yankees @ Chicago Cubs",
          market: "Moneyline",
          open: "+110",
          best: "+120",
          openJuiceHome: "-130",
          bestJuiceHome: "-140",
          bookKey: "draftkings",
          book: "DraftKings",
          kei: "-150",
          keiAway: "+130",
          homeWinProb: 0.6,
        },
        {
          game: "New York Yankees @ Chicago Cubs",
          market: "Total",
          best: "8.5",
          bookKey: "fanduel",
          kei: "9.0",
        },
      ],
      "mlb",
    );
    const row = rows[0];
    expect(row.bestLine.top.label).toBe("+120");
    expect(row.bestLine.bottom.label).toBe("-140");
    // Must not flip Americans into spread-style mirrors.
    expect(row.bestLine.bottom.label).not.toBe("-120");
    expect(row.keiLine.top.label).toBe("+130");
    expect(row.keiLine.bottom.label).toBe("-150");
    expect(row.edgeLineFavor).toBe("Cubs");
    expect(row.edgeLineNum).toBeGreaterThan(3);
    expect(row.tagLine).toBe("PLAY");
    expect(row.playLine).toBe("Cubs -140");
  });

  it("MLB moneyline tags use 1.5pp LEAN / 3.0pp PLAY (totals stay run-point cuts)", () => {
    const mk = (homeWinProb: number) =>
      flatRowsToLegacy(
        [
          {
            game: "New York Yankees @ Chicago Cubs",
            market: "Moneyline",
            best: "+120",
            bestJuiceHome: "-140",
            bookKey: "draftkings",
            kei: "-150",
            keiAway: "+130",
            homeWinProb,
          },
          {
            game: "New York Yankees @ Chicago Cubs",
            market: "Total",
            best: "8.5",
            bookKey: "fanduel",
            kei: "9.7", // 1.2 run pts → LEAN under legacy total cut
          },
        ],
        "mlb",
      )[0];

    // Market no-vig home ≈ 0.562; 0.575 → ~1.3pp → PASS
    expect(mk(0.575).tagLine).toBe("PASS");
    // 0.58 → ~1.8pp → LEAN
    expect(mk(0.58).tagLine).toBe("LEAN");
    // 0.59 → ~2.8pp → still LEAN (<3.0)
    expect(mk(0.59).tagLine).toBe("LEAN");
    // 0.60 → ~3.8pp → PLAY
    expect(mk(0.6).tagLine).toBe("PLAY");
    // Totals remain run-point LEAN (≥1.0)
    expect(mk(0.6).tagOU).toBe("LEAN");
  });
});
