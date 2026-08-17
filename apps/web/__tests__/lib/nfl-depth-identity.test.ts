import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const MUST: Array<{ name: string; team: string }> = [
  { name: "Kyler Murray", team: "MIN" },
  { name: "Jacoby Brissett", team: "ARI" },
  { name: "A.J. Brown", team: "NE" },
  { name: "Mike Evans", team: "SF" },
  { name: "Emeka Egbuka", team: "TB" },
  { name: "DJ Moore", team: "BUF" },
  { name: "Travis Etienne", team: "NO" },
  { name: "David Montgomery", team: "HOU" },
  { name: "Jaylen Waddle", team: "DEN" },
  { name: "Michael Pittman", team: "PIT" },
  { name: "Isiah Pacheco", team: "DET" },
  { name: "Kenneth Walker", team: "KC" },
  { name: "Zach Charbonnet", team: "SEA" },
];

function repoRoot(): string {
  let current = process.cwd();
  for (let i = 0; i < 6; i += 1) {
    if (
      existsSync(path.join(current, "apps", "web")) &&
      existsSync(path.join(current, "package.json"))
    ) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  throw new Error("repo root not found");
}

function norm(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function canon(team: string): string {
  const t = team.trim().toUpperCase();
  if (t === "LA" || t === "LAR") return "LAR";
  if (t === "JAC" || t === "JAX") return "JAX";
  return t;
}

describe("NFL depth identity: pack team = fantasy CSV team", () => {
  it("must-reconcile list matches the depth pack on the launch bundle", () => {
    const root = repoRoot();
    const pointer = JSON.parse(
      readFileSync(path.join(root, "data/ops/nfl-web-launch-bundle.json"), "utf8"),
    ) as { bundle_id?: string; active_run_id?: string };
    const bundleId = String(pointer.bundle_id || pointer.active_run_id || "");
    const csvPath = path.join(
      root,
      "data/ops",
      bundleId,
      "player_regular_season_totals.csv",
    );
    const packPath = path.join(
      root,
      "services/model-service/src/services/nfl_season_engine/data/nfl_depth_chart_2026_w1.json",
    );
    expect(existsSync(csvPath), csvPath).toBe(true);
    const pack = JSON.parse(readFileSync(packPath, "utf8")) as {
      rows: Array<{ player_name?: string; team?: string; position?: string }>;
    };
    const packBy = new Map<string, string>();
    for (const row of pack.rows ?? []) {
      const name = norm(String(row.player_name ?? ""));
      const pos = String(row.position ?? "").toUpperCase();
      if (!name || !["QB", "RB", "WR", "TE"].includes(pos)) continue;
      packBy.set(name, canon(String(row.team ?? "")));
    }
    const csv = readFileSync(csvPath, "utf8");
    const lines = csv.trim().split(/\r?\n/);
    const header = lines[0].split(",");
    const nameIdx = header.indexOf("player_name");
    const teamIdx = header.indexOf("team");
    const csvBy = new Map<string, string>();
    for (const line of lines.slice(1)) {
      const cols = line.split(",");
      csvBy.set(norm(cols[nameIdx] ?? ""), canon(cols[teamIdx] ?? ""));
    }

    for (const row of MUST) {
      const key = norm(row.name);
      const packTeam = [...packBy.entries()].find(([n]) => n.includes(key))?.[1];
      const csvTeam = [...csvBy.entries()].find(([n]) => n.includes(key))?.[1];
      expect(packTeam, `${row.name} pack`).toBe(row.team);
      expect(csvTeam, `${row.name} fantasy CSV`).toBe(row.team);
      expect(csvTeam, `${row.name} pack vs CSV`).toBe(packTeam);
    }
  });
});
