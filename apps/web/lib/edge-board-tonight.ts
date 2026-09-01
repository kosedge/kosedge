import type {
  FlatEdgeBoardRow,
  LegacyEdgeBoardRow,
} from "@/lib/flat-rows-to-legacy";
import { flatRowsToLegacy } from "@/lib/flat-rows-to-legacy";
import { loadAssembledEdgeBoardRows } from "@/lib/build-edge-board-rows";
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

/** Fetch edge board flat rows for a sport (direct assemble — no self-HTTP). */
export async function getEdgeBoardRows(
  sport: string,
): Promise<FlatEdgeBoardRow[]> {
  if (!getSport(sport)) return [];
  try {
    return await loadAssembledEdgeBoardRows(sport);
  } catch {
    return [];
  }
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

  try {
    const flat = await getEdgeBoardRows(sport);
    const legacy = flatRowsToLegacy(Array.isArray(flat) ? flat : [], sport);
    return legacy
      .filter((row) => row?.teamA?.name && row?.teamB?.name)
      .map((row) => ({
        slug: tonightSlug(sport, row.teamA.name, row.teamB.name),
        row,
        sport,
      }));
  } catch {
    // Overview / slate must empty-state — never throw into the error boundary.
    return [];
  }
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
