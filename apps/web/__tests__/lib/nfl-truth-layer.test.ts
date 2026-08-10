import { describe, expect, it } from "vitest";
import {
  canonicalizeNflTeam,
  missingCanonicalNflTeams,
  NFL_CANONICAL_TEAMS,
} from "@/lib/nfl-canonical-teams";
import {
  formatAmericanOdds,
  isValidAmericanOdds,
} from "@/lib/american-odds";
import {
  EDITORIAL_SNAPSHOT_NOTE,
  editorialSnapshotLineage,
  lineageFromActiveRun,
} from "@/lib/nfl-lineage";
import {
  assessConfidence,
  isTierConstantConfidence,
} from "@/lib/nfl-decision-engine";
import { resolveNflKickoffIso } from "@/lib/nfl-schedule-kickoff";

describe("NFL Truth Layer — team IDs", () => {
  it("maps LA → LAR and keeps 32 unique", () => {
    expect(canonicalizeNflTeam("LA")).toBe("LAR");
    expect(canonicalizeNflTeam("LAR")).toBe("LAR");
    expect(NFL_CANONICAL_TEAMS).toHaveLength(32);
    const withAlias = NFL_CANONICAL_TEAMS.map((t) =>
      t === "LAR" ? "LA" : t,
    );
    expect(missingCanonicalNflTeams(withAlias)).toEqual([]);
  });
});

describe("NFL Truth Layer — American odds", () => {
  it("rejects corrupt mid-range Americans like -66", () => {
    expect(isValidAmericanOdds(-66)).toBe(false);
    expect(isValidAmericanOdds(50)).toBe(false);
    expect(isValidAmericanOdds(-110)).toBe(true);
    expect(formatAmericanOdds(-66)).toBe("—");
    expect(formatAmericanOdds(105)).toBe("+105");
  });
});

describe("NFL Truth Layer — lineage", () => {
  it("builds active-run lineage and editorial disclaimer", () => {
    const lin = lineageFromActiveRun({
      active_run_id: "nfl-preseason-sim-2026-test",
      engine_version: "v-test",
      generated_at_utc: "2026-08-10T00:00:00Z",
      kind: "Model",
    });
    expect(lin?.run_id).toBe("nfl-preseason-sim-2026-test");
    expect(lin?.kind).toBe("Model");
    const ed = editorialSnapshotLineage("2026-08-01");
    expect(ed.kind).toBe("Editorial");
    expect(EDITORIAL_SNAPSHOT_NOTE).toMatch(/not active run/);
  });
});

describe("NFL Truth Layer — confidence band honesty", () => {
  it("flags default 0.72 score as tier-constant band", () => {
    const clear = assessConfidence();
    expect(isTierConstantConfidence(clear)).toBe(true);
    const flagged = assessConfidence({ injuryClear: false });
    expect(isTierConstantConfidence(flagged)).toBe(false);
  });
});

describe("NFL Truth Layer — kickoff source", () => {
  it("prefers fair-lines start_time over commence overlay", () => {
    expect(
      resolveNflKickoffIso({
        gameId: "g1",
        startTime: "2026-09-14T00:20:00Z",
        commenceTime: "2026-09-14T00:25:00Z",
        gameDate: "2026-09-13",
      }),
    ).toBe("2026-09-14T00:20:00Z");
  });
});
