/**
 * Match FantasyPros ADP entries onto KosEdge desk rows.
 *
 * Deterministic, reviewable rules (no fuzzy edit-distance guesses):
 * 1. sportsdata id
 * 2. full / core name + team + pos (Jr/Sr/II/III stripped)
 * 3. short name (compact) + team + pos
 * 4. first-initial + last + team + pos
 * 5. unique last + team + pos
 * 6. team-agnostic unique variants of 2–4 (roster moves)
 * 7. same rules against secondary scoring panels (cross-format ADP only)
 *
 * Value Δ should use confidence === "high" only.
 */

import type { FantasyProsAdpEntry } from "@/lib/fantasy/adp-fantasypros";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";

export type AdpMatchTarget = {
  playerId: string;
  playerUid?: string | null;
  playerName: string;
  team: string;
  position: string;
  rankOverall?: number;
};

export type AdpMatchConfidence = "high" | "cross_format";

export type AdpMatchKind =
  | "sportsdata_id"
  | "full_name"
  | "core_name"
  | "short_name"
  | "initial_last"
  | "last_team_pos"
  | "full_name_pos"
  | "core_name_pos"
  | "short_name_pos"
  | "initial_last_pos";

export type AdpMatchResult = {
  adp: number;
  ecr: number | null;
  matchedName: string;
  matchKind: AdpMatchKind;
  confidence: AdpMatchConfidence;
  /** Set when ADP value came from a sibling scoring panel. */
  adpScoringProfile?: FantasyScoringProfile;
};

export type AdpUnmatchedRow = {
  playerId: string;
  playerName: string;
  team: string;
  position: string;
  rankOverall: number | null;
};

export type AdpSecondaryPool = {
  scoringProfile: FantasyScoringProfile;
  players: FantasyProsAdpEntry[];
};

const TEAM_ALIASES: Record<string, string[]> = {
  ARI: ["ARI", "ARZ"],
  ARZ: ["ARI", "ARZ"],
  LA: ["LA", "LAR", "STL"],
  LAR: ["LA", "LAR", "STL"],
  STL: ["LA", "LAR", "STL"],
  LAC: ["LAC", "SD"],
  SD: ["LAC", "SD"],
  LV: ["LV", "OAK", "LVR"],
  OAK: ["LV", "OAK", "LVR"],
  LVR: ["LV", "OAK", "LVR"],
  WAS: ["WAS", "WSH", "WFT"],
  WSH: ["WAS", "WSH", "WFT"],
  WFT: ["WAS", "WSH", "WFT"],
  JAC: ["JAC", "JAX"],
  JAX: ["JAC", "JAX"],
  NE: ["NE", "NEP"],
  NEP: ["NE", "NEP"],
  TB: ["TB", "TAM", "TBB"],
  TAM: ["TB", "TAM", "TBB"],
  TBB: ["TB", "TAM", "TBB"],
  GB: ["GB", "GNB"],
  GNB: ["GB", "GNB"],
  KC: ["KC", "KAN"],
  KAN: ["KC", "KAN"],
  SF: ["SF", "SFO"],
  SFO: ["SF", "SFO"],
  NO: ["NO", "NOR"],
  NOR: ["NO", "NOR"],
};

/**
 * Reviewable core-name aliases (normalized token join → FP-style core).
 * Only add entries that are deterministic and manually verified.
 */
const REVIEWABLE_NAME_ALIASES: Record<string, string> = {
  "amonra st brown": "amon ra st brown",
  "amon ra stbrown": "amon ra st brown",
  "chigoziem okonkwo": "chig okonkwo",
};

function normalizeTeam(team: string): string {
  return team.trim().toUpperCase();
}

function teamsCompatible(a: string, b: string): boolean {
  const ta = normalizeTeam(a);
  const tb = normalizeTeam(b);
  if (!ta || !tb) return true;
  if (ta === tb) return true;
  const aliases = TEAM_ALIASES[ta] ?? [ta];
  return aliases.includes(tb);
}

function stripDiacritics(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/** Lowercase alphanumeric tokens; keep dots for abbreviation detection. */
export function normalizePlayerName(name: string): string {
  return stripDiacritics(name)
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/\./g, ". ")
    .replace(/[^a-z0-9.\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactName(name: string): string {
  return normalizePlayerName(name).replace(/[\s.]/g, "");
}

function stripSuffixes(tokens: string[]): string[] {
  const skip = new Set(["jr", "sr", "ii", "iii", "iv", "v"]);
  return tokens.filter((t) => !skip.has(t.replace(/\./g, "")));
}

/** Collapse "st brown" / hyphenated lasts used by both board and FP. */
function lastNameKey(tokens: string[]): string {
  if (tokens.length >= 2) {
    const a = tokens[tokens.length - 2]!.replace(/\./g, "");
    const b = tokens[tokens.length - 1]!;
    if (a === "st") return `st ${b}`;
    // Keep compound lasts like "smith njigba" when both sides use them.
    if (tokens.length >= 3 && a.length > 1 && b.length > 2) {
      // Prefer single last token for uniqueness unless original was clearly compound —
      // compound handled via coreNameKey instead.
    }
  }
  return tokens[tokens.length - 1] ?? "";
}

export function parseNameParts(name: string): {
  normalized: string;
  firstInitial: string | null;
  lastName: string;
  tokens: string[];
  coreKey: string;
  compact: string;
} {
  const normalized = normalizePlayerName(name);
  const abbr = normalized.match(/^([a-z])\.\s*(.+)$/);
  if (abbr) {
    const rest = stripSuffixes(abbr[2]!.split(" ").filter(Boolean));
    const lastName = lastNameKey(rest) || abbr[2]!.trim();
    const tokens = [abbr[1]!, ...rest];
    return {
      normalized,
      firstInitial: abbr[1]!,
      lastName,
      tokens,
      // Abbreviated boards can't form a full core key — use initial+last.
      coreKey: `${abbr[1]!}|${lastName}`,
      compact: compactName(name),
    };
  }
  const tokens = stripSuffixes(normalized.split(" ").filter(Boolean));
  const aliased = REVIEWABLE_NAME_ALIASES[tokens.join(" ")];
  const effectiveTokens = aliased
    ? stripSuffixes(normalizePlayerName(aliased).split(" ").filter(Boolean))
    : tokens;
  const lastName = lastNameKey(effectiveTokens) || normalized;
  const first = effectiveTokens[0] ?? "";
  return {
    normalized,
    firstInitial: first ? first[0]! : null,
    lastName,
    tokens: effectiveTokens,
    coreKey: effectiveTokens.join(" "),
    compact: compactName(name),
  };
}

function indexKey(parts: string[]): string {
  return parts.join("|");
}

function toResult(
  entry: FantasyProsAdpEntry,
  kind: AdpMatchKind,
  confidence: AdpMatchConfidence,
  scoringProfile?: FantasyScoringProfile,
): AdpMatchResult {
  return {
    adp: entry.adp,
    ecr: entry.ecr,
    matchedName: entry.playerName,
    matchKind: kind,
    confidence,
    adpScoringProfile: scoringProfile,
  };
}

type PlayerIndex = {
  bySportsdata: Map<string, FantasyProsAdpEntry>;
  byFullTeamPos: Map<string, FantasyProsAdpEntry[]>;
  byCoreTeamPos: Map<string, FantasyProsAdpEntry[]>;
  byShortTeamPos: Map<string, FantasyProsAdpEntry[]>;
  byCompactShortTeamPos: Map<string, FantasyProsAdpEntry[]>;
  byInitialLastTeamPos: Map<string, FantasyProsAdpEntry[]>;
  byLastTeamPos: Map<string, FantasyProsAdpEntry[]>;
  byFullPos: Map<string, FantasyProsAdpEntry[]>;
  byCorePos: Map<string, FantasyProsAdpEntry[]>;
  byShortPos: Map<string, FantasyProsAdpEntry[]>;
  byCompactShortPos: Map<string, FantasyProsAdpEntry[]>;
  byInitialLastPos: Map<string, FantasyProsAdpEntry[]>;
};

function push(
  map: Map<string, FantasyProsAdpEntry[]>,
  key: string,
  entry: FantasyProsAdpEntry,
) {
  const list = map.get(key) ?? [];
  list.push(entry);
  map.set(key, list);
}

function buildIndex(players: FantasyProsAdpEntry[]): PlayerIndex {
  const idx: PlayerIndex = {
    bySportsdata: new Map(),
    byFullTeamPos: new Map(),
    byCoreTeamPos: new Map(),
    byShortTeamPos: new Map(),
    byCompactShortTeamPos: new Map(),
    byInitialLastTeamPos: new Map(),
    byLastTeamPos: new Map(),
    byFullPos: new Map(),
    byCorePos: new Map(),
    byShortPos: new Map(),
    byCompactShortPos: new Map(),
    byInitialLastPos: new Map(),
  };

  for (const entry of players) {
    if (entry.sportsdataId) idx.bySportsdata.set(entry.sportsdataId, entry);
    const parts = parseNameParts(entry.playerName);
    const team = normalizeTeam(entry.team);
    const pos = entry.position.toUpperCase();

    push(idx.byFullTeamPos, indexKey([parts.normalized, team, pos]), entry);
    push(idx.byCoreTeamPos, indexKey([parts.coreKey, team, pos]), entry);
    push(idx.byFullPos, indexKey([parts.normalized, pos]), entry);
    push(idx.byCorePos, indexKey([parts.coreKey, pos]), entry);

    if (entry.shortName) {
      const short = normalizePlayerName(entry.shortName);
      const shortParts = parseNameParts(entry.shortName);
      push(idx.byShortTeamPos, indexKey([short, team, pos]), entry);
      push(
        idx.byCompactShortTeamPos,
        indexKey([shortParts.compact, team, pos]),
        entry,
      );
      push(idx.byShortPos, indexKey([short, pos]), entry);
      push(idx.byCompactShortPos, indexKey([shortParts.compact, pos]), entry);
    }

    if (parts.firstInitial && parts.lastName) {
      push(
        idx.byInitialLastTeamPos,
        indexKey([parts.firstInitial, parts.lastName, team, pos]),
        entry,
      );
      push(
        idx.byInitialLastPos,
        indexKey([parts.firstInitial, parts.lastName, pos]),
        entry,
      );
    }
    push(idx.byLastTeamPos, indexKey([parts.lastName, team, pos]), entry);
  }
  return idx;
}

function takeUnique(
  list: FantasyProsAdpEntry[] | undefined,
  kind: AdpMatchKind,
  confidence: AdpMatchConfidence,
  scoringProfile?: FantasyScoringProfile,
): AdpMatchResult | null {
  if (!list || list.length !== 1) return null;
  return toResult(list[0]!, kind, confidence, scoringProfile);
}

function takeCompatible(
  list: FantasyProsAdpEntry[] | undefined,
  team: string,
  kind: AdpMatchKind,
  confidence: AdpMatchConfidence,
  scoringProfile?: FantasyScoringProfile,
): AdpMatchResult | null {
  if (!list?.length) return null;
  const compatible = list.filter((e) => teamsCompatible(team, e.team));
  if (compatible.length !== 1) return null;
  return toResult(compatible[0]!, kind, confidence, scoringProfile);
}

function matchAgainstIndex(
  target: AdpMatchTarget,
  idx: PlayerIndex,
  confidence: AdpMatchConfidence,
  scoringProfile?: FantasyScoringProfile,
): AdpMatchResult | null {
  const uid = target.playerUid?.trim();
  if (uid && idx.bySportsdata.has(uid)) {
    return toResult(
      idx.bySportsdata.get(uid)!,
      "sportsdata_id",
      confidence,
      scoringProfile,
    );
  }

  const parts = parseNameParts(target.playerName);
  const team = normalizeTeam(target.team);
  const pos = target.position.toUpperCase();
  const boardShort = normalizePlayerName(target.playerName);
  const boardCompact = parts.compact;

  // Same-team (alias-aware) high-precision keys
  let hit =
    takeCompatible(
      idx.byFullTeamPos.get(indexKey([parts.normalized, team, pos])),
      team,
      "full_name",
      confidence,
      scoringProfile,
    ) ||
    takeCompatible(
      idx.byCoreTeamPos.get(indexKey([parts.coreKey, team, pos])),
      team,
      "core_name",
      confidence,
      scoringProfile,
    ) ||
    takeCompatible(
      idx.byShortTeamPos.get(indexKey([boardShort, team, pos])),
      team,
      "short_name",
      confidence,
      scoringProfile,
    ) ||
    takeCompatible(
      idx.byCompactShortTeamPos.get(indexKey([boardCompact, team, pos])),
      team,
      "short_name",
      confidence,
      scoringProfile,
    );

  if (!hit && parts.firstInitial && parts.lastName) {
    hit = takeCompatible(
      idx.byInitialLastTeamPos.get(
        indexKey([parts.firstInitial, parts.lastName, team, pos]),
      ),
      team,
      "initial_last",
      confidence,
      scoringProfile,
    );
  }

  if (!hit && parts.lastName) {
    hit = takeCompatible(
      idx.byLastTeamPos.get(indexKey([parts.lastName, team, pos])),
      team,
      "last_team_pos",
      confidence,
      scoringProfile,
    );
  }

  // Team-agnostic unique keys (roster moves / stale team codes)
  if (!hit) {
    hit =
      takeUnique(
        idx.byFullPos.get(indexKey([parts.normalized, pos])),
        "full_name_pos",
        confidence,
        scoringProfile,
      ) ||
      takeUnique(
        idx.byCorePos.get(indexKey([parts.coreKey, pos])),
        "core_name_pos",
        confidence,
        scoringProfile,
      ) ||
      takeUnique(
        idx.byShortPos.get(indexKey([boardShort, pos])),
        "short_name_pos",
        confidence,
        scoringProfile,
      ) ||
      takeUnique(
        idx.byCompactShortPos.get(indexKey([boardCompact, pos])),
        "short_name_pos",
        confidence,
        scoringProfile,
      );
  }

  if (!hit && parts.firstInitial && parts.lastName) {
    hit = takeUnique(
      idx.byInitialLastPos.get(
        indexKey([parts.firstInitial, parts.lastName, pos]),
      ),
      "initial_last_pos",
      confidence,
      scoringProfile,
    );
  }

  return hit;
}

export function matchAdpToDeskRows(
  targets: AdpMatchTarget[],
  primaryPlayers: FantasyProsAdpEntry[],
  options?: {
    secondaryPools?: AdpSecondaryPool[];
    /** When true, emit console info for unmatched rows (server load path). */
    logUnmatched?: boolean;
  },
): {
  byPlayerId: Map<string, AdpMatchResult>;
  matched: number;
  matchedHigh: number;
  matchedCrossFormat: number;
  unmatched: number;
  unmatchedRows: AdpUnmatchedRow[];
} {
  const primaryIdx = buildIndex(primaryPlayers);
  const secondary = (options?.secondaryPools ?? []).map((pool) => ({
    scoringProfile: pool.scoringProfile,
    idx: buildIndex(pool.players),
  }));

  const byPlayerId = new Map<string, AdpMatchResult>();
  const unmatchedRows: AdpUnmatchedRow[] = [];
  let matchedHigh = 0;
  let matchedCrossFormat = 0;

  for (const target of targets) {
    let hit = matchAgainstIndex(target, primaryIdx, "high");

    if (!hit) {
      for (const pool of secondary) {
        hit = matchAgainstIndex(
          target,
          pool.idx,
          "cross_format",
          pool.scoringProfile,
        );
        if (hit) break;
      }
    }

    if (hit) {
      byPlayerId.set(target.playerId, hit);
      if (hit.confidence === "high") matchedHigh += 1;
      else matchedCrossFormat += 1;
    } else {
      unmatchedRows.push({
        playerId: target.playerId,
        playerName: target.playerName,
        team: target.team,
        position: target.position,
        rankOverall: target.rankOverall ?? null,
      });
    }
  }

  if (options?.logUnmatched && unmatchedRows.length > 0) {
    const sample = unmatchedRows.slice(0, 40).map((row) => ({
      name: row.playerName,
      team: row.team,
      pos: row.position,
      rank: row.rankOverall,
    }));
    console.info(
      `[fantasy-adp] unmatched ${unmatchedRows.length}/${targets.length}`,
      sample,
    );
  }

  return {
    byPlayerId,
    matched: matchedHigh + matchedCrossFormat,
    matchedHigh,
    matchedCrossFormat,
    unmatched: unmatchedRows.length,
    unmatchedRows,
  };
}

/** True when Value Δ may be shown (same-format / high-confidence match). */
export function isHighConfidenceAdp(
  hit: AdpMatchResult | null | undefined,
): boolean {
  return hit?.confidence === "high";
}
