/**
 * Match FantasyPros ADP entries onto KosEdge desk rows.
 *
 * Board names are often abbreviated ("J.Taylor"); FP uses full names.
 * Matching priority: sportsdata id → exact full name+team+pos →
 * short name → first-initial + last + team + pos → last+team+pos (unique).
 */

import type { FantasyProsAdpEntry } from "@/lib/fantasy/adp-fantasypros";

export type AdpMatchTarget = {
  playerId: string;
  playerUid?: string | null;
  playerName: string;
  team: string;
  position: string;
};

export type AdpMatchResult = {
  adp: number;
  ecr: number | null;
  matchedName: string;
  matchKind:
    | "sportsdata_id"
    | "full_name"
    | "short_name"
    | "initial_last"
    | "last_team_pos";
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

function normalizeTeam(team: string): string {
  return team.trim().toUpperCase();
}

function teamsCompatible(a: string, b: string): boolean {
  const ta = normalizeTeam(a);
  const tb = normalizeTeam(b);
  if (!ta || !tb) return true; // allow missing team
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

function stripSuffixes(tokens: string[]): string[] {
  const skip = new Set(["jr", "sr", "ii", "iii", "iv", "v"]);
  return tokens.filter((t) => !skip.has(t.replace(/\./g, "")));
}

/** Collapse "st brown" style multi-token lasts used by both board and FP. */
function lastNameKey(tokens: string[]): string {
  if (tokens.length >= 2) {
    const a = tokens[tokens.length - 2]!;
    const b = tokens[tokens.length - 1]!;
    if (a === "st" || a === "st.") return `${a.replace(/\./g, "")} ${b}`;
  }
  return tokens[tokens.length - 1] ?? "";
}

export function parseNameParts(name: string): {
  normalized: string;
  firstInitial: string | null;
  lastName: string;
  tokens: string[];
} {
  const normalized = normalizePlayerName(name);
  const abbr = normalized.match(/^([a-z])\.\s*(.+)$/);
  if (abbr) {
    const rest = stripSuffixes(abbr[2]!.split(" ").filter(Boolean));
    const lastName = lastNameKey(rest) || abbr[2]!.trim();
    return {
      normalized,
      firstInitial: abbr[1]!,
      lastName,
      tokens: [abbr[1]!, ...rest],
    };
  }
  const tokens = stripSuffixes(normalized.split(" ").filter(Boolean));
  const lastName = lastNameKey(tokens) || normalized;
  const first = tokens[0] ?? "";
  return {
    normalized,
    firstInitial: first ? first[0]! : null,
    lastName,
    tokens,
  };
}

function indexKey(parts: string[]): string {
  return parts.join("|");
}

export function matchAdpToDeskRows(
  targets: AdpMatchTarget[],
  adpPlayers: FantasyProsAdpEntry[],
): {
  byPlayerId: Map<string, AdpMatchResult>;
  matched: number;
  unmatched: number;
} {
  const bySportsdata = new Map<string, FantasyProsAdpEntry>();
  const byFull = new Map<string, FantasyProsAdpEntry[]>();
  const byShort = new Map<string, FantasyProsAdpEntry[]>();
  const byInitialLast = new Map<string, FantasyProsAdpEntry[]>();
  const byLastTeamPos = new Map<string, FantasyProsAdpEntry[]>();

  const push = (
    map: Map<string, FantasyProsAdpEntry[]>,
    key: string,
    entry: FantasyProsAdpEntry,
  ) => {
    const list = map.get(key) ?? [];
    list.push(entry);
    map.set(key, list);
  };

  for (const entry of adpPlayers) {
    if (entry.sportsdataId) bySportsdata.set(entry.sportsdataId, entry);
    const parts = parseNameParts(entry.playerName);
    const team = normalizeTeam(entry.team);
    const pos = entry.position.toUpperCase();
    push(byFull, indexKey([parts.normalized, team, pos]), entry);
    if (entry.shortName) {
      const short = normalizePlayerName(entry.shortName);
      push(byShort, indexKey([short, team, pos]), entry);
    }
    if (parts.firstInitial && parts.lastName) {
      push(
        byInitialLast,
        indexKey([parts.firstInitial, parts.lastName, team, pos]),
        entry,
      );
    }
    push(byLastTeamPos, indexKey([parts.lastName, team, pos]), entry);
  }

  const byPlayerId = new Map<string, AdpMatchResult>();
  let matched = 0;
  let unmatched = 0;

  const takeUnique = (
    list: FantasyProsAdpEntry[] | undefined,
    kind: AdpMatchResult["matchKind"],
  ): AdpMatchResult | null => {
    if (!list || list.length !== 1) return null;
    const entry = list[0]!;
    return {
      adp: entry.adp,
      ecr: entry.ecr,
      matchedName: entry.playerName,
      matchKind: kind,
    };
  };

  const takeCompatible = (
    list: FantasyProsAdpEntry[] | undefined,
    team: string,
    kind: AdpMatchResult["matchKind"],
  ): AdpMatchResult | null => {
    if (!list?.length) return null;
    const compatible = list.filter((e) => teamsCompatible(team, e.team));
    if (compatible.length !== 1) return null;
    const entry = compatible[0]!;
    return {
      adp: entry.adp,
      ecr: entry.ecr,
      matchedName: entry.playerName,
      matchKind: kind,
    };
  };

  for (const target of targets) {
    let hit: AdpMatchResult | null = null;
    const uid = target.playerUid?.trim();
    if (uid && bySportsdata.has(uid)) {
      const entry = bySportsdata.get(uid)!;
      hit = {
        adp: entry.adp,
        ecr: entry.ecr,
        matchedName: entry.playerName,
        matchKind: "sportsdata_id",
      };
    }

    const parts = parseNameParts(target.playerName);
    const team = normalizeTeam(target.team);
    const pos = target.position.toUpperCase();

    if (!hit) {
      hit = takeUnique(
        byFull.get(indexKey([parts.normalized, team, pos])),
        "full_name",
      );
    }
    if (!hit) {
      // Try without requiring exact team key — aliases
      const candidates = adpPlayers.filter((e) => {
        const ep = parseNameParts(e.playerName);
        return (
          ep.normalized === parts.normalized &&
          e.position.toUpperCase() === pos &&
          teamsCompatible(team, e.team)
        );
      });
      if (candidates.length === 1) {
        const entry = candidates[0]!;
        hit = {
          adp: entry.adp,
          ecr: entry.ecr,
          matchedName: entry.playerName,
          matchKind: "full_name",
        };
      }
    }

    if (!hit && parts.firstInitial && parts.lastName) {
      hit = takeCompatible(
        byInitialLast.get(
          indexKey([parts.firstInitial, parts.lastName, team, pos]),
        ),
        team,
        "initial_last",
      );
      if (!hit) {
        const candidates = adpPlayers.filter((e) => {
          const ep = parseNameParts(e.playerName);
          return (
            ep.firstInitial === parts.firstInitial &&
            ep.lastName === parts.lastName &&
            e.position.toUpperCase() === pos &&
            teamsCompatible(team, e.team)
          );
        });
        if (candidates.length === 1) {
          const entry = candidates[0]!;
          hit = {
            adp: entry.adp,
            ecr: entry.ecr,
            matchedName: entry.playerName,
            matchKind: "initial_last",
          };
        }
      }
    }

    if (!hit) {
      const shortKey = normalizePlayerName(target.playerName);
      hit = takeCompatible(
        byShort.get(indexKey([shortKey, team, pos])),
        team,
        "short_name",
      );
    }

    if (!hit && parts.lastName) {
      hit = takeCompatible(
        byLastTeamPos.get(indexKey([parts.lastName, team, pos])),
        team,
        "last_team_pos",
      );
      if (!hit) {
        const candidates = adpPlayers.filter(
          (e) =>
            parseNameParts(e.playerName).lastName === parts.lastName &&
            e.position.toUpperCase() === pos &&
            teamsCompatible(team, e.team),
        );
        if (candidates.length === 1) {
          const entry = candidates[0]!;
          hit = {
            adp: entry.adp,
            ecr: entry.ecr,
            matchedName: entry.playerName,
            matchKind: "last_team_pos",
          };
        }
      }
    }

    if (hit) {
      byPlayerId.set(target.playerId, hit);
      matched += 1;
    } else {
      unmatched += 1;
    }
  }

  return { byPlayerId, matched, unmatched };
}
