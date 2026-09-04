import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import b7Sample from "@/lib/ncaam/b7-odds-sample.json";
import {
  isCanonicalNcaamSportKey,
  isRetiredNcaamSportKey,
  resolveTeamId,
  toRatingsNorm,
} from "@/lib/ncaam/identity";
import { findTeamInDirectory, getTeamDirectory } from "@/lib/team-research";

const webRoot = path.join(__dirname, "../..");

/** Production publish join sites that must not call odds_team_to_short. */
const PRODUCTION_PUBLISH_PATHS = [
  "scripts/project_future_kei_lines.py",
  "src/merge_games_ensemble.py",
  "src/build_schedule_from_odds.py",
  "src/build_actual_margins.py",
  "src/join_and_backtest.py",
] as const;

describe("B7.1 Miami FL vs Miami OH never collapse", () => {
  it("resolves Odds Miami Hurricanes → miami fl and Miami (OH) → miami oh", () => {
    const fl = resolveTeamId("Miami Hurricanes", "odds");
    const oh = resolveTeamId("Miami (OH) RedHawks", "odds");
    expect(fl.ok).toBe(true);
    expect(oh.ok).toBe(true);
    if (!fl.ok || !oh.ok) return;
    expect(fl.teamId).toBe("miami fl");
    expect(oh.teamId).toBe("miami oh");
    expect(fl.teamId).not.toBe(oh.teamId);
  });

  it("resolves KenPom-style miami fl / miami oh distinctly", () => {
    expect(resolveTeamId("miami fl", "kenpom").teamId).toBe("miami fl");
    expect(resolveTeamId("miami oh", "kenpom").teamId).toBe("miami oh");
  });

  it("omits bare miami (ambiguous FL vs OH)", () => {
    const bare = resolveTeamId("miami", "odds");
    expect(bare.ok).toBe(false);
    if (bare.ok) return;
    expect(bare.reason).toBe("omit");
    expect(bare.teamId).toBeNull();
  });

  it("omits bare loyola / southern peer homonyms", () => {
    for (const bare of ["loyola", "southern"]) {
      const r = resolveTeamId(bare, "odds");
      expect(r.ok).toBe(false);
      expect(r.teamId).toBeNull();
    }
    expect(resolveTeamId("loyola chicago", "odds").teamId).toBe(
      "loyola chicago",
    );
    expect(resolveTeamId("Southern Jaguars", "odds").teamId).toBe("southern");
  });

  it("directory keeps Miami FL and Miami OH as separate entries", () => {
    const fl = findTeamInDirectory("ncaam", "miami-fl");
    const oh = findTeamInDirectory("ncaam", "miami-oh");
    expect(fl?.name).toBe("Miami (FL)");
    expect(fl?.conference).toBe("ACC");
    expect(oh?.name).toBe("Miami (OH)");
    expect(oh?.conference).toBe("MAC");
    expect(fl?.slug).not.toBe(oh?.slug);
    expect(fl?.code).not.toBe(oh?.code);
  });
});

describe("B7.2 ≥50 odds names → unique team_id OR explicit omit", () => {
  it("resolves the curated sample to unique team_ids", () => {
    const rows = b7Sample.resolve_or_omit;
    expect(rows.length).toBeGreaterThanOrEqual(50);
    const ids = rows.map((r) => {
      const resolved = resolveTeamId(r.odds_name, "odds");
      expect(resolved.ok).toBe(true);
      expect(resolved.teamId).toBe(r.team_id);
      return resolved.teamId;
    });
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("documents explicit omits for ambiguous aliases", () => {
    for (const row of b7Sample.explicit_omit) {
      const r = resolveTeamId(row.odds_name, "odds");
      expect(r.ok).toBe(false);
      expect(r.teamId).toBeNull();
    }
  });
});

describe("B7.3 zero production publish paths call odds_team_to_short", () => {
  it("source-locks publish scripts onto ncaam_identity (no def odds_team_to_short)", () => {
    for (const rel of PRODUCTION_PUBLISH_PATHS) {
      const src = readFileSync(path.join(webRoot, rel), "utf8");
      expect(src).not.toMatch(/def\s+_?odds_team_to_short\s*\(/);
      expect(src).toMatch(/ncaam_identity|odds_name_to_team_norm/);
    }
  });

  it("no remaining def odds_team_to_short under apps/web publish tree", () => {
    const roots = [path.join(webRoot, "scripts"), path.join(webRoot, "src")];
    const offenders: string[] = [];
    const scanFile = (fp: string) => {
      if (!fp.endsWith(".py")) return;
      const text = readFileSync(fp, "utf8");
      if (/def\s+_?odds_team_to_short\s*\(/.test(text)) offenders.push(fp);
    };
    for (const root of roots) {
      for (const name of readdirSync(root)) {
        scanFile(path.join(root, name));
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe("B7.4 assemble/API reject sport=cbb", () => {
  it("marks cbb/ncaab retired; ncaam canonical", () => {
    expect(isRetiredNcaamSportKey("cbb")).toBe(true);
    expect(isRetiredNcaamSportKey("CBB")).toBe(true);
    expect(isRetiredNcaamSportKey("ncaab")).toBe(true);
    expect(isRetiredNcaamSportKey("ncaam")).toBe(false);
    expect(isCanonicalNcaamSportKey("ncaam")).toBe(true);
    expect(isCanonicalNcaamSportKey("cbb")).toBe(false);
  });

  it("assemble route explicitly rejects retired cbb before Unknown sport", () => {
    const assemble = readFileSync(
      path.join(webRoot, "app/api/edge-board/[sport]/assemble/route.ts"),
      "utf8",
    );
    expect(assemble).toContain("isRetiredNcaamSportKey");
    expect(assemble).toContain("Retired sport key");
    expect(assemble).toContain('use: "ncaam"');
  });
});

describe("NCAAM identity helpers", () => {
  it("bridges nc state → inherited ratings grain without remat", () => {
    expect(toRatingsNorm("nc state")).toBe("nc stateate");
    expect(toRatingsNorm("miami fl")).toBe("miami fl");
  });

  it("expands NCAAM directory toward D1 with distinct Miami FL/OH", () => {
    const dir = getTeamDirectory("ncaam");
    expect(dir.length).toBeGreaterThan(300);
    expect(dir.some((t) => t.slug === "miami-fl")).toBe(true);
    expect(dir.some((t) => t.slug === "miami-oh")).toBe(true);
    expect(dir.some((t) => t.slug === "miami")).toBe(false);
    const slugs = dir.map((t) => t.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });
});
