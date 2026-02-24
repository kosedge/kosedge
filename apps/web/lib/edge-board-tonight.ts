import { headers } from "next/headers";
import type { FlatEdgeBoardRow, LegacyEdgeBoardRow } from "@/components/EdgeBoard";
import { flatRowsToLegacy } from "@/components/EdgeBoard";
import { env } from "@/lib/config/env";
import { mergeKeiIntoEdgeBoardRows } from "@/lib/edge-board-kei";
import { getSport, SPORTS } from "@/lib/sports";

/** Build a URL slug from away/home team names (e.g. "Duke", "UNC" -> "duke-unc"). */
export function slugifyGame(away: string, home: string): string {
  const a = (away ?? "")
    .toLowerCase()
    .replace(/['.]/g, "")
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
  const b = (home ?? "")
    .toLowerCase()
    .replace(/['.]/g, "")
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
  return [a, b].filter(Boolean).join("-") || "game";
}

/** Full slug for article URL: sport + game (e.g. "ncaam-duke-unc"). */
export function tonightSlug(sport: string, away: string, home: string): string {
  return `${sport}-${slugifyGame(away, home)}`;
}

async function getRequestOrigin(): Promise<string> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto") ?? "http";
  return `${proto}://${host}`;
}

type EdgeBoardApiResponse =
  | FlatEdgeBoardRow[]
  | { rows: FlatEdgeBoardRow[]; cached?: boolean; ttl?: number }
  | { error: string; [k: string]: unknown };

/** Fetch edge board flat rows for a sport (same as edge board page: API + KEI merge). */
export async function getEdgeBoardRows(
  sport: string,
): Promise<FlatEdgeBoardRow[]> {
  const origin = await getRequestOrigin();
  const headersObj: Record<string, string> = { accept: "application/json" };
  if (env.INTERNAL_API_SECRET)
    headersObj["x-kosedge-secret"] = env.INTERNAL_API_SECRET;

  const res = await fetch(`${origin}/api/edge-board/${sport}/today`, {
    cache: "no-store",
    headers: headersObj,
  });

  if (!res.ok) return [];

  const json = (await res.json()) as EdgeBoardApiResponse;
  let rows: FlatEdgeBoardRow[] = [];
  if (Array.isArray(json)) rows = json;
  else if (
    json &&
    typeof json === "object" &&
    "rows" in json &&
    Array.isArray((json as { rows?: unknown }).rows)
  ) {
    rows = (json as { rows: FlatEdgeBoardRow[] }).rows;
  }

  return mergeKeiIntoEdgeBoardRows(rows, sport);
}

export type TonightGame = {
  slug: string;
  row: LegacyEdgeBoardRow;
  sport: string;
};

/** Tonight's games from the edge board for a sport, with article slugs. */
export async function getTonightGames(sport: string): Promise<TonightGame[]> {
  const valid = getSport(sport);
  if (!valid) return [];

  const flat = await getEdgeBoardRows(sport);
  const legacy = flatRowsToLegacy(flat);

  return legacy.map((row) => ({
    slug: tonightSlug(sport, row.teamA.name, row.teamB.name),
    row,
    sport,
  }));
}

const SPORT_PREFIXES = SPORTS.map((s) => ({
  prefix: `${s.key}-`,
  sport: s.key,
}));

/** Resolve a slug to a tonight game (for article page). Returns null if not found. */
export async function getGameBySlug(
  slug: string,
): Promise<{ row: LegacyEdgeBoardRow; sport: string } | null> {
  const trimmed = (slug ?? "").trim();
  if (!trimmed) return null;

  for (const { prefix, sport } of SPORT_PREFIXES) {
    if (!trimmed.startsWith(prefix)) continue;
    const gamePart = trimmed.slice(prefix.length);
    const games = await getTonightGames(sport);
    const match = games.find(
      (g) =>
        g.slug === trimmed ||
        slugifyGame(g.row.teamA.name, g.row.teamB.name) === gamePart,
    );
    if (match) return { row: match.row, sport: match.sport };
  }

  // Fallback: try ncaam (common for "tonight")
  const games = await getTonightGames("ncaam");
  const match = games.find((g) => g.slug === trimmed);
  if (match) return { row: match.row, sport: match.sport };

  return null;
}
