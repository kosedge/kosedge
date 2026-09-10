/**
 * NFL DFS V1 identities. Site is a real join key (DK | FD), not a URL flag.
 * Failed joins never produce value. Season averages are never substituted.
 */

export const DFS_SITES = ["DK", "FD"] as const;
export type DfsSite = (typeof DFS_SITES)[number];
export const SCORING_BY_SITE = { DK: "dk_classic", FD: "fd_classic" } as const;
export const DFS_SKILL_POSITIONS = ["QB", "RB", "WR", "TE"] as const;
export const DFS_IDENTITY_VERSION = "nfl-dfs-identity-v1";

export type DfsJoinReason =
  | "ok"
  | "site_mismatch"
  | "scoring_site_mismatch"
  | "season_mismatch"
  | "week_mismatch"
  | "slate_mismatch"
  | "missing_slate"
  | "missing_player_identity"
  | "player_mismatch"
  | "wrong_player"
  | "opponent_mismatch"
  | "game_mismatch"
  | "team_changed"
  | "stale_salary"
  | "missing_salary"
  | "missing_projection"
  | "duplicate_player_identity"
  | "position_not_supported";

const TEAM_ALIASES: Record<string, string> = {
  LA: "LAR",
  LAR: "LAR",
  WSH: "WAS",
  WAS: "WAS",
  JAC: "JAX",
  JAX: "JAX",
  STL: "LAR",
  SD: "LAC",
  OAK: "LV",
};

export function canonicalDfsSite(raw: unknown): DfsSite | null {
  const token = String(raw ?? "")
    .trim()
    .toUpperCase();
  if (token === "DK" || token === "DRAFTKINGS" || token === "DRAFT_KINGS") {
    return "DK";
  }
  if (token === "FD" || token === "FANDUEL" || token === "FAN_DUEL") {
    return "FD";
  }
  return null;
}

export function canonicalDfsPosition(raw: unknown): string | null {
  const token = String(raw ?? "")
    .trim()
    .toUpperCase();
  if (!token) return null;
  const primary = token.split("/")[0]?.trim() ?? "";
  if ((DFS_SKILL_POSITIONS as readonly string[]).includes(primary))
    return primary;
  if (primary === "FB" || primary === "HB") return "RB";
  return null;
}

export function canonicalTeamCode(raw: unknown): string | null {
  const token = String(raw ?? "")
    .trim()
    .toUpperCase();
  if (!token) return null;
  return TEAM_ALIASES[token] ?? token;
}

export type DfsSlateIdentity = {
  season: number;
  week: number;
  site: DfsSite;
  slateId: string;
};

export type DfsSalaryObservation = {
  site: DfsSite;
  season: number;
  week: number;
  slateId: string;
  sourcePlayerId: string;
  playerUid: string | null;
  playerName: string;
  team: string;
  opponent: string;
  position: string;
  salary: number;
  gameId?: string | null;
  isCurrent: boolean;
  identityStatus?: string;
};

export type DfsProjectionTarget = {
  season: number;
  week: number;
  playerUid: string | null;
  team: string;
  opponent?: string | null;
  position: string;
  gameId?: string | null;
  scoringSystem: "dk_classic" | "fd_classic";
};

export type DfsJoinVerdict = {
  ok: boolean;
  reason: DfsJoinReason;
  failClosed: boolean;
  allowValue: boolean;
};

function verdict(ok: boolean, reason: DfsJoinReason): DfsJoinVerdict {
  return { ok, reason, failClosed: !ok, allowValue: ok };
}

export function certifyDfsJoin(input: {
  requested: DfsSlateIdentity;
  salary: DfsSalaryObservation | null;
  projection: DfsProjectionTarget | null;
}): DfsJoinVerdict {
  const { requested, salary, projection } = input;
  if (!salary) return verdict(false, "missing_salary");
  if (!projection) return verdict(false, "missing_projection");

  const reqSite = canonicalDfsSite(requested.site);
  const salSite = canonicalDfsSite(salary.site);
  if (!reqSite || !salSite || reqSite !== salSite) {
    return verdict(false, "site_mismatch");
  }
  if (projection.scoringSystem !== SCORING_BY_SITE[reqSite]) {
    return verdict(false, "scoring_site_mismatch");
  }
  if (
    salary.season !== requested.season ||
    projection.season !== requested.season
  ) {
    return verdict(false, "season_mismatch");
  }
  if (salary.week !== requested.week || projection.week !== requested.week) {
    return verdict(false, "week_mismatch");
  }
  if (!requested.slateId || salary.slateId !== requested.slateId) {
    return verdict(
      false,
      requested.slateId ? "slate_mismatch" : "missing_slate",
    );
  }
  if (!salary.isCurrent) return verdict(false, "stale_salary");
  if (!(salary.salary > 0)) return verdict(false, "missing_salary");
  if (salary.identityStatus === "conflict") {
    return verdict(false, "duplicate_player_identity");
  }
  if (!salary.playerUid || !projection.playerUid) {
    return verdict(false, "missing_player_identity");
  }
  if (salary.playerUid !== projection.playerUid) {
    return verdict(false, "wrong_player");
  }
  const salPos = canonicalDfsPosition(salary.position);
  const projPos = canonicalDfsPosition(projection.position);
  if (!salPos || !projPos) return verdict(false, "position_not_supported");

  const salTeam = canonicalTeamCode(salary.team);
  const projTeam = canonicalTeamCode(projection.team);
  if (!salTeam || !projTeam || salTeam !== projTeam) {
    return verdict(false, "team_changed");
  }
  const salOpp = canonicalTeamCode(salary.opponent);
  const projOpp = projection.opponent
    ? canonicalTeamCode(projection.opponent)
    : null;
  if (!salOpp) return verdict(false, "opponent_mismatch");
  if (projOpp && salOpp !== projOpp) return verdict(false, "opponent_mismatch");
  if (
    salary.gameId &&
    projection.gameId &&
    salary.gameId !== projection.gameId
  ) {
    return verdict(false, "game_mismatch");
  }
  return verdict(true, "ok");
}

export function presentSalaryForSite(
  salary: DfsSalaryObservation,
  site: string,
): DfsJoinVerdict {
  const want = canonicalDfsSite(site);
  const have = canonicalDfsSite(salary.site);
  if (!want || !have || want !== have) return verdict(false, "site_mismatch");
  if (!salary.isCurrent) return verdict(false, "stale_salary");
  return verdict(true, "ok");
}

export function filterRowsForRequestedSite<T extends { site?: string | null }>(
  rows: T[],
  site: string,
): T[] {
  const want = canonicalDfsSite(site);
  if (!want) return [];
  return rows.filter((row) => canonicalDfsSite(row.site) === want);
}
