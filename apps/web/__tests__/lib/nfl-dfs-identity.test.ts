import { describe, expect, it } from "vitest";
import {
  certifyDfsJoin,
  filterRowsForRequestedSite,
  presentSalaryForSite,
  type DfsProjectionTarget,
  type DfsSalaryObservation,
  type DfsSlateIdentity,
} from "@/lib/nfl-dfs-identity";

const requested: DfsSlateIdentity = {
  season: 2026,
  week: 1,
  site: "DK",
  slateId: "151307",
};

function salary(
  overrides: Partial<DfsSalaryObservation> = {},
): DfsSalaryObservation {
  return {
    site: "DK",
    season: 2026,
    week: 1,
    slateId: "151307",
    sourcePlayerId: "868199",
    playerUid: "uid-allen",
    playerName: "Josh Allen",
    team: "BUF",
    opponent: "HOU",
    position: "QB",
    salary: 7000,
    gameId: "buf-hou",
    isCurrent: true,
    identityStatus: "resolved",
    ...overrides,
  };
}

function projection(
  overrides: Partial<DfsProjectionTarget> = {},
): DfsProjectionTarget {
  return {
    season: 2026,
    week: 1,
    playerUid: "uid-allen",
    team: "BUF",
    opponent: "HOU",
    position: "QB",
    gameId: "buf-hou",
    scoringSystem: "dk_classic",
    ...overrides,
  };
}

describe("DFS identity fail-closed joins", () => {
  it("certifies a matching slate/site/player/game", () => {
    const v = certifyDfsJoin({
      requested,
      salary: salary(),
      projection: projection(),
    });
    expect(v.ok).toBe(true);
    expect(v.allowValue).toBe(true);
  });

  it("rejects wrong player", () => {
    expect(
      certifyDfsJoin({
        requested,
        salary: salary(),
        projection: projection({ playerUid: "uid-other" }),
      }).reason,
    ).toBe("wrong_player");
  });

  it("rejects wrong opponent", () => {
    expect(
      certifyDfsJoin({
        requested,
        salary: salary({ opponent: "MIA" }),
        projection: projection(),
      }).reason,
    ).toBe("opponent_mismatch");
  });

  it("rejects wrong week", () => {
    expect(
      certifyDfsJoin({
        requested: { ...requested, week: 2 },
        salary: salary(),
        projection: projection({ week: 2 }),
      }).reason,
    ).toBe("week_mismatch");
  });

  it("rejects wrong slate", () => {
    expect(
      certifyDfsJoin({
        requested: { ...requested, slateId: "showdown" },
        salary: salary(),
        projection: projection(),
      }).reason,
    ).toBe("slate_mismatch");
  });

  it("rejects DK salary presented as FD", () => {
    expect(presentSalaryForSite(salary(), "FD").reason).toBe("site_mismatch");
    expect(
      certifyDfsJoin({
        requested: { ...requested, site: "FD" },
        salary: salary(),
        projection: projection({ scoringSystem: "fd_classic" }),
      }).reason,
    ).toBe("site_mismatch");
  });

  it("rejects FD salary presented as DK", () => {
    expect(
      presentSalaryForSite(salary({ site: "FD", salary: 8800 }), "DK").reason,
    ).toBe("site_mismatch");
  });

  it("rejects stale and missing salary / projection", () => {
    expect(
      certifyDfsJoin({
        requested,
        salary: salary({ isCurrent: false }),
        projection: projection(),
      }).reason,
    ).toBe("stale_salary");
    expect(
      certifyDfsJoin({ requested, salary: null, projection: projection() })
        .reason,
    ).toBe("missing_salary");
    expect(
      certifyDfsJoin({ requested, salary: salary(), projection: null }).reason,
    ).toBe("missing_projection");
  });

  it("rejects traded / team-changed player", () => {
    expect(
      certifyDfsJoin({
        requested,
        salary: salary({ team: "BUF" }),
        projection: projection({ team: "LAR", opponent: "SF" }),
      }).reason,
    ).toBe("team_changed");
  });

  it("drops other-site rows when the URL site changes", () => {
    const rows = [
      { site: "DK", playerUid: "a" },
      { site: "FD", playerUid: "b" },
    ];
    expect(
      filterRowsForRequestedSite(rows, "FD").map((r) => r.playerUid),
    ).toEqual(["b"]);
    expect(
      filterRowsForRequestedSite(rows, "draftkings").map((r) => r.site),
    ).toEqual(["DK"]);
  });
});
