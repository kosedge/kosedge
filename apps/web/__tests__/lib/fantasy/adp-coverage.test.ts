import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { matchAdpToDeskRows } from "@/lib/fantasy/adp-match";
import type { FantasyProsAdpEntry } from "@/lib/fantasy/adp-fantasypros";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";

type Snapshot = {
  players: Array<{
    player_id?: number | string;
    player_name?: string;
    player_short_name?: string | null;
    player_team_id?: string | null;
    player_position_id?: string | null;
    rank_ecr?: number | null;
    rank_ave?: number | null;
    sportsdata_id?: string | null;
  }>;
};

function loadSnap(profile: FantasyScoringProfile): FantasyProsAdpEntry[] {
  const file = path.join(
    process.cwd(),
    "data/fantasy",
    `adp-fantasypros-2026-${profile}.json`,
  );
  const snap = JSON.parse(readFileSync(file, "utf8")) as Snapshot;
  return (snap.players ?? [])
    .filter((p) => p.player_name && p.rank_ave != null)
    .map((p) => ({
      playerId: String(p.player_id ?? p.player_name),
      playerName: String(p.player_name),
      shortName: p.player_short_name ? String(p.player_short_name) : null,
      team: String(p.player_team_id ?? "").toUpperCase(),
      position: String(p.player_position_id ?? "").toUpperCase(),
      adp: Number(p.rank_ave),
      ecr: p.rank_ecr == null ? null : Number(p.rank_ecr),
      sportsdataId: p.sportsdata_id ? String(p.sportsdata_id) : null,
    }));
}

function parseCsv(text: string): Record<string, string>[] {
  const lines = text.trim().split(/\r?\n/);
  const header = lines[0]!.split(",");
  return lines.slice(1).map((line) => {
    const cols = line.split(",");
    const row: Record<string, string> = {};
    header.forEach((key, i) => {
      row[key] = cols[i] ?? "";
    });
    return row;
  });
}

function findPreseasonCsv(): string | null {
  const roots = [
    path.join(process.cwd(), "../../data/ops"),
    path.join(process.cwd(), "data/ops"),
  ];
  for (const root of roots) {
    if (!existsSync(root)) continue;
    const dirs = readdirSync(root)
      .filter((d) => d.startsWith("nfl-preseason-sim-2026-"))
      .sort()
      .reverse();
    for (const dir of dirs) {
      const file = path.join(root, dir, "player_regular_season_totals.csv");
      if (existsSync(file)) return file;
    }
  }
  return null;
}

describe("adp coverage on preseason top-200", () => {
  it("raises linked coverage with cross-format while keeping Value Δ high-confidence", () => {
    const csvPath = findPreseasonCsv();
    if (!csvPath) {
      expect(true).toBe(true);
      return;
    }

    const rows = parseCsv(readFileSync(csvPath, "utf8"))
      .filter((r) =>
        ["QB", "RB", "WR", "TE"].includes((r.position ?? "").toUpperCase()),
      )
      .map((r) => {
        const pts =
          Number(r.pass_yards_total || 0) / 25 +
          Number(r.pass_tds_total || 0) * 4 +
          Number(r.rush_yards_total || 0) / 10 +
          Number(r.rush_tds_total || 0) * 6 +
          Number(r.receiving_yards_total || 0) / 10 +
          Number(r.receptions_total || 0) * 0.5 +
          Number(r.rec_tds_total || 0) * 6;
        return { ...r, pts };
      })
      .sort((a, b) => b.pts - a.pts)
      .slice(0, 200);

    const half = loadSnap("half_ppr");
    const ppr = loadSnap("ppr");
    const std = loadSnap("standard");

    const targets = rows.map((r, i) => ({
      playerId: `${r.team}:${r.player_name}:${i}`,
      playerName: r.player_name,
      team: r.team,
      position: r.position,
      rankOverall: i + 1,
    }));

    const before = matchAdpToDeskRows(targets, half);
    const after = matchAdpToDeskRows(targets, half, {
      secondaryPools: [
        { scoringProfile: "ppr", players: ppr },
        { scoringProfile: "standard", players: std },
      ],
    });

    expect(before.matched).toBeGreaterThanOrEqual(180);
    expect(after.matched).toBeGreaterThan(before.matched);
    expect(after.matchedHigh).toBeGreaterThanOrEqual(before.matchedHigh);
    expect(after.matched).toBeGreaterThanOrEqual(190);
    expect(after.unmatched).toBeLessThanOrEqual(12);
    expect(after.matchedCrossFormat).toBeGreaterThanOrEqual(5);
  });
});
