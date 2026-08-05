#!/usr/bin/env node
/**
 * Refresh checked-in FantasyPros ADP snapshots for the Fantasy Draft Desk.
 *
 * Usage: node scripts/nfl/refresh-fantasypros-adp.mjs [year]
 */
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const outDir = path.join(root, "apps/web/data/fantasy");
const year = Number(process.argv[2] || 2026);

const PROFILES = [
  { scoring: "STD", scoringProfile: "standard" },
  { scoring: "HALF", scoringProfile: "half_ppr" },
  { scoring: "PPR", scoringProfile: "ppr" },
];

async function fetchScoring(scoring) {
  const params = new URLSearchParams({
    sport: "NFL",
    year: String(year),
    week: "0",
    position: "ALL",
    type: "ADP",
    scoring,
  });
  const url = `https://partners.fantasypros.com/api/v1/consensus-rankings.php?${params}`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${scoring}`);
  return res.json();
}

await mkdir(outDir, { recursive: true });
const fetchedAt = new Date().toISOString();

for (const { scoring, scoringProfile } of PROFILES) {
  const data = await fetchScoring(scoring);
  const players = (data.players || [])
    .map((p) => ({
      player_id: p.player_id,
      player_name: p.player_name,
      player_short_name: p.player_short_name ?? null,
      player_team_id: p.player_team_id ?? null,
      player_position_id: p.player_position_id ?? null,
      rank_ecr: p.rank_ecr ?? null,
      rank_ave:
        p.rank_ave == null || p.rank_ave === ""
          ? null
          : Number(p.rank_ave),
      sportsdata_id: p.sportsdata_id ?? null,
    }))
    .filter((p) => p.player_name && p.rank_ave != null && Number.isFinite(p.rank_ave));

  const snap = {
    source: "fantasypros-partners-adp",
    attribution: "ADP data from FantasyPros (partners consensus rankings API)",
    sport: data.sport,
    year,
    scoring,
    scoringProfile,
    type: data.type,
    last_updated: data.last_updated ?? null,
    last_updated_ts: data.last_updated_ts ?? null,
    total_experts: data.total_experts ?? null,
    filters: data.filters ?? null,
    fetched_at: fetchedAt,
    count: players.length,
    players,
  };

  const outPath = path.join(
    outDir,
    `adp-fantasypros-${year}-${scoringProfile}.json`,
  );
  await writeFile(outPath, `${JSON.stringify(snap, null, 2)}\n`, "utf8");
  console.log(`wrote ${outPath} (${players.length} players, updated ${snap.last_updated})`);
}
