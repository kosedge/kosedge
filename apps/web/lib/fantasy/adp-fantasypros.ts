/**
 * FantasyPros partners consensus ADP feed.
 *
 * Public partners endpoint (no API key) returns format-aware ADP with
 * last_updated / last_updated_ts. Official FantasyPros v2 requires a key;
 * this partners feed is the stable, reviewable source for the Draft Desk.
 *
 * Attribution: ADP data from FantasyPros.
 */

import "server-only";

import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import type { FantasyScoringProfile } from "@/lib/fantasy/types";

function findWebDataRoots(): string[] {
  const roots: string[] = [];
  let current = process.cwd();
  for (let depth = 0; depth < 6; depth += 1) {
    roots.push(current);
    roots.push(path.join(current, "apps", "web"));
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return [...new Set(roots)];
}

export const ADP_FANTASYPROS_SOURCE = "fantasypros-partners-adp" as const;

export const ADP_FANTASYPROS_LABEL =
  "FantasyPros consensus ADP (partners feed — format-aware)";

const SCORING_TO_FP: Record<FantasyScoringProfile, "STD" | "HALF" | "PPR"> = {
  standard: "STD",
  half_ppr: "HALF",
  ppr: "PPR",
};

const REVALIDATE_SECONDS = 60 * 60; // hourly through draft season

export type FantasyProsAdpEntry = {
  playerId: string;
  playerName: string;
  shortName: string | null;
  team: string;
  position: string;
  /** Average draft position (rank_ave). */
  adp: number;
  ecr: number | null;
  sportsdataId: string | null;
};

export type FantasyProsAdpFeed = {
  source: typeof ADP_FANTASYPROS_SOURCE;
  sourceLabel: string;
  scoringProfile: FantasyScoringProfile;
  season: number;
  lastUpdated: string | null;
  lastUpdatedTs: number | null;
  fetchedAt: string;
  origin: "live" | "snapshot";
  players: FantasyProsAdpEntry[];
  limitations: string[];
};

type PartnersPlayer = {
  player_id?: number | string;
  player_name?: string;
  player_short_name?: string;
  player_team_id?: string;
  player_position_id?: string;
  rank_ecr?: number | string | null;
  rank_ave?: number | string | null;
  sportsdata_id?: string | null;
};

type PartnersResponse = {
  sport?: string;
  type?: string;
  year?: string | number;
  scoring?: string;
  last_updated?: string;
  last_updated_ts?: number;
  total_experts?: number;
  filters?: string;
  players?: PartnersPlayer[];
};

type SnapshotFile = {
  source?: string;
  scoringProfile?: FantasyScoringProfile;
  year?: number;
  last_updated?: string;
  last_updated_ts?: number;
  fetched_at?: string;
  total_experts?: number;
  filters?: string;
  players?: PartnersPlayer[];
};

const ADP_LIMITATIONS = [
  "ADP from FantasyPros consensus (partners feed), matched to STD / Half / PPR.",
  "Unmatched names show ADP as —; Value Δ only on high-confidence same-format matches.",
  "Refreshes ~hourly; uses a saved snapshot if the live feed is unreachable.",
];

function partnersUrl(season: number, scoring: FantasyScoringProfile): string {
  const fpScoring = SCORING_TO_FP[scoring];
  const params = new URLSearchParams({
    sport: "NFL",
    year: String(season),
    week: "0",
    position: "ALL",
    type: "ADP",
    scoring: fpScoring,
  });
  return `https://partners.fantasypros.com/api/v1/consensus-rankings.php?${params}`;
}

function resolveSnapshotPath(scoring: FantasyScoringProfile): string | null {
  const fileName = `adp-fantasypros-2026-${scoring}.json`;
  for (const root of findWebDataRoots()) {
    const candidate = path.join(root, "data", "fantasy", fileName);
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

function parseAdp(raw: number | string | null | undefined): number | null {
  if (raw == null || raw === "") return null;
  const n = typeof raw === "number" ? raw : Number(String(raw).trim());
  if (!Number.isFinite(n) || n <= 0) return null;
  return Math.round(n * 100) / 100;
}

function parsePlayers(players: PartnersPlayer[] | undefined): FantasyProsAdpEntry[] {
  const out: FantasyProsAdpEntry[] = [];
  for (const p of players ?? []) {
    const adp = parseAdp(p.rank_ave);
    if (adp == null) continue;
    const name = String(p.player_name ?? "").trim();
    if (!name) continue;
    const ecrRaw = p.rank_ecr;
    const ecr =
      ecrRaw == null || ecrRaw === ""
        ? null
        : Number(ecrRaw);
    out.push({
      playerId: String(p.player_id ?? name),
      playerName: name,
      shortName: p.player_short_name ? String(p.player_short_name) : null,
      team: String(p.player_team_id ?? "").toUpperCase(),
      position: String(p.player_position_id ?? "").toUpperCase(),
      adp,
      ecr: Number.isFinite(ecr) ? ecr : null,
      sportsdataId: p.sportsdata_id ? String(p.sportsdata_id) : null,
    });
  }
  return out;
}

function feedFromPartners(
  data: PartnersResponse,
  scoringProfile: FantasyScoringProfile,
  origin: "live" | "snapshot",
  fetchedAt: string,
): FantasyProsAdpFeed {
  const season = Number(data.year) || 2026;
  const experts =
    typeof data.total_experts === "number" ? data.total_experts : null;
  const limitations = [...ADP_LIMITATIONS];
  if (experts != null) {
    limitations.push(`FantasyPros panel: ${experts} ADP sources.`);
  }
  if (origin === "snapshot") {
    limitations.push("Saved FantasyPros ADP snapshot (live feed unavailable).");
  }

  return {
    source: ADP_FANTASYPROS_SOURCE,
    sourceLabel: ADP_FANTASYPROS_LABEL,
    scoringProfile,
    season,
    lastUpdated: data.last_updated ? String(data.last_updated) : null,
    lastUpdatedTs:
      typeof data.last_updated_ts === "number" ? data.last_updated_ts : null,
    fetchedAt,
    origin,
    players: parsePlayers(data.players),
    limitations,
  };
}

function loadSnapshotFeed(
  scoringProfile: FantasyScoringProfile,
): FantasyProsAdpFeed | null {
  try {
    const filePath = resolveSnapshotPath(scoringProfile);
    if (!filePath) return null;
    const raw = readFileSync(filePath, "utf8");
    const data = JSON.parse(raw) as SnapshotFile;
    return feedFromPartners(
      {
        year: data.year,
        last_updated: data.last_updated,
        last_updated_ts: data.last_updated_ts,
        total_experts: data.total_experts,
        filters: data.filters,
        players: data.players,
      },
      scoringProfile,
      "snapshot",
      data.fetched_at ?? new Date().toISOString(),
    );
  } catch {
    return null;
  }
}

export async function fetchFantasyProsAdpFeed(input: {
  season?: number;
  scoringProfile?: FantasyScoringProfile;
}): Promise<FantasyProsAdpFeed> {
  const season = input.season ?? 2026;
  const scoringProfile = input.scoringProfile ?? "half_ppr";
  const fetchedAt = new Date().toISOString();

  try {
    const res = await fetch(partnersUrl(season, scoringProfile), {
      headers: { Accept: "application/json" },
      next: { revalidate: REVALIDATE_SECONDS },
    });
    if (!res.ok) {
      throw new Error(`FantasyPros ADP HTTP ${res.status}`);
    }
    const data = (await res.json()) as PartnersResponse;
    const feed = feedFromPartners(data, scoringProfile, "live", fetchedAt);
    if (feed.players.length === 0) {
      throw new Error("FantasyPros ADP returned zero players");
    }
    return feed;
  } catch {
    const snap = loadSnapshotFeed(scoringProfile);
    if (snap && snap.players.length > 0) return snap;
    return {
      source: ADP_FANTASYPROS_SOURCE,
      sourceLabel: `${ADP_FANTASYPROS_LABEL} — unavailable`,
      scoringProfile,
      season,
      lastUpdated: null,
      lastUpdatedTs: null,
      fetchedAt,
      origin: "snapshot",
      players: [],
      limitations: [
        ...ADP_LIMITATIONS,
        "FantasyPros ADP unavailable — Model vs ADP blank until a feed loads.",
      ],
    };
  }
}

const ALL_SCORING: FantasyScoringProfile[] = ["standard", "half_ppr", "ppr"];

/**
 * Primary format feed + sibling scoring panels for identity / deep-board
 * coverage. Value Δ uses primary (high confidence) only; siblings may fill
 * ADP display as cross-format when the primary panel omits a player.
 */
export async function fetchFantasyProsAdpBundle(input: {
  season?: number;
  scoringProfile?: FantasyScoringProfile;
}): Promise<{
  primary: FantasyProsAdpFeed;
  secondary: Array<{
    scoringProfile: FantasyScoringProfile;
    players: FantasyProsAdpFeed["players"];
  }>;
}> {
  const season = input.season ?? 2026;
  const scoringProfile = input.scoringProfile ?? "half_ppr";
  const feeds = await Promise.all(
    ALL_SCORING.map((profile) =>
      fetchFantasyProsAdpFeed({ season, scoringProfile: profile }),
    ),
  );
  const primary =
    feeds.find((f) => f.scoringProfile === scoringProfile) ?? feeds[0]!;
  const secondary = feeds
    .filter(
      (f) =>
        f.scoringProfile !== scoringProfile && f.players.length > 0,
    )
    .map((f) => ({
      scoringProfile: f.scoringProfile,
      players: f.players,
    }));
  return { primary, secondary };
}

export function formatAdpFreshness(feed: FantasyProsAdpFeed): string {
  const parts: string[] = [];
  if (feed.lastUpdated) parts.push(`updated ${feed.lastUpdated}`);
  else if (feed.lastUpdatedTs) {
    parts.push(
      `updated ${new Date(feed.lastUpdatedTs * 1000).toLocaleDateString("en-US", {
        month: "numeric",
        day: "numeric",
        timeZone: "UTC",
      })}`,
    );
  }
  parts.push(feed.origin === "live" ? "live cache" : "snapshot");
  return parts.join(" · ");
}
