/**
 * NFL inactive remat-or-failclosed — customer display suppress (SOP v1.1).
 *
 * Ryan ACCEPT + CoS LOCK 2026-09-13. Product owns suppress display only.
 * Remat / KEI math / Vegas / thresholds / PLAY unlocks are out of scope.
 *
 * When a MAJOR inactive is known and remat has not completed, assemble must
 * not paint stale house fair / edge. Street quotes (open / current / books /
 * linesAsOf) may still refresh. Evaluate on every assemble so
 * EDGE_BOARD_REFRESH_MS cannot re-paint suppressed fair just because street moved.
 *
 * Fail-closed / unavailable ≠ PASS. Strip publishTag / actionLabel /
 * edgeMagnitude (including nested decision) — same chrome contract as
 * `edge-board-total-identity-gate.ts`.
 *
 * Drivers (do not silently suppress the whole NFL board):
 *   - explicit per-game suppress flag, OR
 *   - MAJOR inactive known (flag class/reason or row stamp)
 * `qb_unresolved` alone does not invent suppress (PLAY-tier handling stays).
 *
 * Canonical gameId SoT: NFL fair-lines / schedule `game_id`
 * (e.g. `2026-W01-ATL@PIT`). See `resolveNflInactiveGameId`.
 */

export const NFL_INACTIVE_SUPPRESS_REASON_MAJOR =
  "major_inactive_pending_remat" as const;

export const NFL_INACTIVE_REMAT_NONE = "none-suppressed" as const;

/** Default customer fair markets for a game when the flag lists no subset. */
export const NFL_CUSTOMER_FAIR_MARKETS = [
  "Spread",
  "Total",
  "Moneyline",
] as const;

export type NflCustomerFairMarket = (typeof NFL_CUSTOMER_FAIR_MARKETS)[number];

/** Kickoff + 3h buffer when Product omits an explicit TTL. */
export const NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS = 3 * 60 * 60 * 1000;

export type NflInactiveSuppressState = "SUPPRESSED" | "CLEAR";

export type NflInactiveSuppressReceipt = {
  state: NflInactiveSuppressState;
  reason?: string;
  players?: string[];
  classes?: string[];
  setAt?: string;
  ttlUntil?: string;
  /** Real remat receipt, or `"none-suppressed"` when suppressed without remat. */
  rematRunId?: string | null;
};

export type NflInactiveSuppressFlag = {
  markets?: string[];
  reason?: string;
  players?: string[];
  classes?: string[];
  setBy?: string;
  setAt?: string;
  /** Absolute ISO / epoch-ms TTL, or omit to use kickoff+buffer. */
  ttl?: string | number;
  ttlUntil?: string;
  rematRunId?: string | null;
  /** CoS / remat explicit clear. */
  clearedBy?: string | null;
  state?: NflInactiveSuppressState;
  aliases?: string[];
};

export type NflInactiveSuppressStore = {
  version?: number;
  /** Documented SoT join key — always `nfl_fair_line_game_id`. */
  gameIdConvention?: "nfl_fair_line_game_id";
  kickoffBufferMs?: number;
  games?: Record<string, NflInactiveSuppressFlag>;
};

export type NflInactiveFairSuppressInput = {
  gameId?: string | null;
  market?: string | null;
  aliases?: string[];
  unresolvedFlags?: string[] | null;
  /** Future SI / Product stamp — MAJOR known without inventing from qb alone. */
  majorInactiveKnown?: boolean | null;
  commenceTime?: string | null;
  flag?: NflInactiveSuppressFlag | null;
  nowMs?: number;
  kickoffBufferMs?: number;
};

export type NflInactiveFairSuppressVerdict = {
  state: NflInactiveSuppressState;
  failClosed: boolean;
  reason?: string;
  players?: string[];
  classes?: string[];
  setAt?: string;
  ttlUntil?: string;
  rematRunId?: string | null;
};

export type NflInactiveFairSuppressRowFields = {
  id?: string;
  game?: string | null;
  gameId?: string | null;
  market?: string;
  awayAbbr?: string | null;
  homeAbbr?: string | null;
  commenceTime?: string | null;
  unresolvedFlags?: string[] | null;
  majorInactiveKnown?: boolean | null;
  fairCompareEligible?: boolean;
  inactiveSuppress?: NflInactiveSuppressReceipt;
  publishTag?: unknown;
  publish_tag?: unknown;
  actionLabel?: unknown;
  action_label?: unknown;
  edgeMagnitude?: unknown;
  edge_magnitude?: unknown;
  kei?: unknown;
  modelKei?: unknown;
  model_kei?: unknown;
  fairLine?: unknown;
  fair_line?: unknown;
  keiSpreadHome?: unknown;
  keiTotal?: unknown;
  keiAway?: unknown;
  kei_away?: unknown;
  homeWinProb?: unknown;
  awayWinProb?: unknown;
  home_win_prob?: unknown;
  away_win_prob?: unknown;
  coverProb?: unknown;
  playToNotes?: unknown;
  playToPlay?: unknown;
  playToLean?: unknown;
  playToPass?: unknown;
  decision?: unknown;
  open?: unknown;
  best?: unknown;
  book?: unknown;
  bookKey?: unknown;
  linesAsOf?: unknown;
};

const FAIL_CLOSED_DECISION_KEYS = [
  "actionLabel",
  "action_label",
  "edgeMagnitude",
  "edge_magnitude",
  "numericalEdge",
  "numerical_edge",
  "playTo",
  "play_to",
  "fairLine",
  "fair_line",
  "coverProb",
  "cover_prob",
  "coverGrade",
  "cover_grade",
] as const;

const FAIR_NUMBER_KEYS = [
  "kei",
  "modelKei",
  "model_kei",
  "fairLine",
  "fair_line",
  "keiSpreadHome",
  "keiTotal",
  "keiAway",
  "kei_away",
  "homeWinProb",
  "awayWinProb",
  "home_win_prob",
  "away_win_prob",
  "coverProb",
  "playToNotes",
  "playToPlay",
  "playToLean",
  "playToPass",
] as const;

function normToken(raw: string | null | undefined): string {
  return String(raw ?? "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "")
    .replace(/[-_]/g, "");
}

function normMatchup(raw: string | null | undefined): string {
  return String(raw ?? "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "")
    .replace(/[-_]/g, "@");
}

export function isNflCustomerFairMarket(
  market: string | null | undefined,
): boolean {
  const m = String(market ?? "").trim();
  return NFL_CUSTOMER_FAIR_MARKETS.some(
    (allowed) => allowed.toLowerCase() === m.toLowerCase(),
  );
}

export function emptyNflInactiveSuppressStore(): NflInactiveSuppressStore {
  return {
    version: 1,
    gameIdConvention: "nfl_fair_line_game_id",
    kickoffBufferMs: NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS,
    games: {},
  };
}

/**
 * Canonical join key: fair-lines / schedule `game_id` (e.g. `2026-W01-ATL@PIT`).
 * Fallback: row `id` with `-spread` / `-total` / `-ml` stripped.
 * Alias: `AWAY@HOME` from abbrs (Product ops convenience — not the SoT).
 */
export function resolveNflInactiveGameId(
  row: Pick<
    NflInactiveFairSuppressRowFields,
    "gameId" | "id" | "awayAbbr" | "homeAbbr"
  >,
): string {
  const stamped = String(row.gameId ?? "").trim();
  if (stamped) return stamped;
  const id = String(row.id ?? "")
    .trim()
    .replace(/-(spread|total|ml|moneyline)$/i, "");
  if (id) return id;
  const away = String(row.awayAbbr ?? "").trim();
  const home = String(row.homeAbbr ?? "").trim();
  if (away && home) return `${away}@${home}`;
  return "";
}

export function nflInactiveGameAliases(
  row: Pick<
    NflInactiveFairSuppressRowFields,
    "gameId" | "id" | "game" | "awayAbbr" | "homeAbbr"
  >,
): string[] {
  const out = new Set<string>();
  const gameId = resolveNflInactiveGameId(row);
  if (gameId) {
    out.add(gameId);
    const at = gameId.match(/([A-Z]{2,3})@([A-Z]{2,3})$/i);
    if (at) out.add(`${at[1]!.toUpperCase()}@${at[2]!.toUpperCase()}`);
  }
  const away = String(row.awayAbbr ?? "")
    .trim()
    .toUpperCase();
  const home = String(row.homeAbbr ?? "")
    .trim()
    .toUpperCase();
  if (away && home) {
    out.add(`${away}@${home}`);
    out.add(`${away}-${home}`);
  }
  const game = String(row.game ?? "").trim();
  if (game) out.add(game);
  return [...out];
}

function parseTimeMs(raw: string | number | null | undefined): number | null {
  if (raw == null || raw === "") return null;
  if (typeof raw === "number" && Number.isFinite(raw)) return raw;
  const n = Date.parse(String(raw));
  return Number.isFinite(n) ? n : null;
}

function flagTtlUntilMs(
  flag: NflInactiveSuppressFlag | null | undefined,
  commenceTime: string | null | undefined,
  kickoffBufferMs: number,
): number | null {
  if (!flag) {
    const kick = parseTimeMs(commenceTime);
    return kick == null ? null : kick + kickoffBufferMs;
  }
  const explicit = parseTimeMs(flag.ttlUntil ?? flag.ttl);
  if (explicit != null) return explicit;
  const kick = parseTimeMs(commenceTime);
  return kick == null ? null : kick + kickoffBufferMs;
}

function rematRunIdValue(
  raw: string | null | undefined,
): string | null | undefined {
  if (raw == null) return raw;
  const t = String(raw).trim();
  return t || null;
}

export function isNflInactiveRematReceipt(
  rematRunId: string | null | undefined,
): boolean {
  const v = rematRunIdValue(rematRunId);
  return Boolean(v && v !== NFL_INACTIVE_REMAT_NONE);
}

export function isNflInactiveFlagRevoked(
  flag: NflInactiveSuppressFlag | null | undefined,
): boolean {
  if (!flag) return false;
  if (flag.state === "CLEAR") return true;
  const cleared = String(flag.clearedBy ?? "")
    .trim()
    .toLowerCase();
  if (cleared === "cos" || cleared === "remat" || cleared === "product") {
    return true;
  }
  return isNflInactiveRematReceipt(flag.rematRunId);
}

export function isNflInactiveFlagExpired(
  flag: NflInactiveSuppressFlag | null | undefined,
  args: {
    commenceTime?: string | null;
    nowMs?: number;
    kickoffBufferMs?: number;
  } = {},
): boolean {
  const now = args.nowMs ?? Date.now();
  const ttl = flagTtlUntilMs(
    flag,
    args.commenceTime,
    args.kickoffBufferMs ?? NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS,
  );
  return ttl != null && now >= ttl;
}

function hasMajorClass(
  flag: NflInactiveSuppressFlag | null | undefined,
): boolean {
  return (flag?.classes ?? []).some(
    (c) => String(c).trim().toUpperCase() === "MAJOR",
  );
}

function isMajorReason(reason: string | null | undefined): boolean {
  const r = String(reason ?? "")
    .trim()
    .toLowerCase();
  return (
    r === NFL_INACTIVE_SUPPRESS_REASON_MAJOR ||
    r === "major_inactive" ||
    r.includes("major_inactive")
  );
}

export function lookupNflInactiveSuppressFlag(
  store: NflInactiveSuppressStore | null | undefined,
  gameId: string,
  aliases: string[] = [],
): NflInactiveSuppressFlag | null {
  const games = store?.games;
  if (!games) return null;
  const keys = [gameId, ...aliases].filter(Boolean);
  for (const key of keys) {
    if (games[key]) return games[key]!;
  }
  const wanted = new Set(keys.map((k) => normMatchup(k)));
  for (const [storedKey, flag] of Object.entries(games)) {
    if (wanted.has(normMatchup(storedKey))) return flag;
    for (const alias of flag.aliases ?? []) {
      if (wanted.has(normMatchup(alias))) return flag;
    }
  }
  return null;
}

function marketListed(
  market: string | null | undefined,
  listed: string[] | undefined,
): boolean {
  if (!isNflCustomerFairMarket(market)) return false;
  if (!listed || listed.length === 0) return true;
  const token = normToken(market);
  return listed.some((m) => normToken(m) === token);
}

export function evaluateNflInactiveFairSuppress(
  args: NflInactiveFairSuppressInput,
): NflInactiveFairSuppressVerdict {
  const flag = args.flag ?? null;
  const nowMs = args.nowMs ?? Date.now();
  const buffer =
    args.kickoffBufferMs ?? NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS;
  const revoked = isNflInactiveFlagRevoked(flag);
  const expired = isNflInactiveFlagExpired(flag, {
    commenceTime: args.commenceTime,
    nowMs,
    kickoffBufferMs: buffer,
  });

  const majorKnown =
    args.majorInactiveKnown === true ||
    hasMajorClass(flag) ||
    isMajorReason(flag?.reason);
  const explicitActive = flag != null && !revoked && !expired;
  const majorActive = majorKnown && !revoked && !expired;

  // qb_unresolved alone never invents suppress.
  const should = explicitActive || majorActive;
  if (!should || !marketListed(args.market, flag?.markets)) {
    return { state: "CLEAR", failClosed: false };
  }

  const ttlMs = flagTtlUntilMs(flag, args.commenceTime, buffer);
  const remat = rematRunIdValue(flag?.rematRunId);
  return {
    state: "SUPPRESSED",
    failClosed: true,
    reason: flag?.reason || NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
    players: flag?.players,
    classes: flag?.classes,
    setAt: flag?.setAt,
    ttlUntil: ttlMs != null ? new Date(ttlMs).toISOString() : undefined,
    rematRunId: remat ?? NFL_INACTIVE_REMAT_NONE,
  };
}

/**
 * Unavailable / fail-closed ≠ PASS. Strip publish + action + edge chrome
 * and customer fair numbers. Street fields stay.
 */
export function stripSuppressedFairEdgeChrome<
  T extends NflInactiveFairSuppressRowFields,
>(row: T): T {
  const next: T = { ...row };
  delete next.publishTag;
  delete next.publish_tag;
  delete next.actionLabel;
  delete next.action_label;
  delete next.edgeMagnitude;
  delete next.edge_magnitude;
  for (const key of FAIR_NUMBER_KEYS) {
    delete next[key];
  }
  const decision = next.decision;
  if (decision && typeof decision === "object" && !Array.isArray(decision)) {
    const d: Record<string, unknown> = {
      ...(decision as Record<string, unknown>),
    };
    for (const key of FAIL_CLOSED_DECISION_KEYS) {
      delete d[key];
    }
    next.decision = d;
  }
  return next;
}

export function clearNflInactiveSuppressReceipt(): NflInactiveSuppressReceipt {
  return { state: "CLEAR" };
}

export function receiptFromVerdict(
  verdict: NflInactiveFairSuppressVerdict,
): NflInactiveSuppressReceipt {
  if (verdict.state === "CLEAR") return clearNflInactiveSuppressReceipt();
  return {
    state: "SUPPRESSED",
    reason: verdict.reason,
    players: verdict.players,
    classes: verdict.classes,
    setAt: verdict.setAt,
    ttlUntil: verdict.ttlUntil,
    rematRunId: verdict.rematRunId ?? NFL_INACTIVE_REMAT_NONE,
  };
}

/** Game-level receipt: any SUPPRESSED market wins over a sibling CLEAR. */
export function preferNflInactiveSuppressReceipt(
  ...receipts: Array<NflInactiveSuppressReceipt | null | undefined>
): NflInactiveSuppressReceipt | undefined {
  const present = receipts.filter(
    (r): r is NflInactiveSuppressReceipt => r != null && Boolean(r.state),
  );
  if (present.length === 0) return undefined;
  return present.find((r) => r.state === "SUPPRESSED") ?? present[0];
}

/**
 * Assemble-path stamp. NFL only. Idempotent.
 * Other sports are returned unchanged (CFB kill-switch / KS paths untouched).
 */
export function applyNflInactiveFairSuppressToRows<
  T extends NflInactiveFairSuppressRowFields,
>(
  rows: T[],
  sportKey: string,
  opts?: {
    nowMs?: number;
    store?: NflInactiveSuppressStore | null;
    flags?: Record<string, NflInactiveSuppressFlag>;
  },
): T[] {
  const sport = String(sportKey ?? "")
    .trim()
    .toLowerCase();
  if (sport !== "nfl") return rows;

  const store: NflInactiveSuppressStore = {
    ...emptyNflInactiveSuppressStore(),
    ...(opts?.store ?? {}),
    games: {
      ...(opts?.store?.games ?? {}),
      ...(opts?.flags ?? {}),
    },
  };
  const buffer =
    store.kickoffBufferMs ?? NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS;

  return rows.map((row) => {
    const gameId = resolveNflInactiveGameId(row);
    const aliases = nflInactiveGameAliases(row);
    const flag = lookupNflInactiveSuppressFlag(store, gameId, aliases);
    const verdict = evaluateNflInactiveFairSuppress({
      gameId,
      market: row.market,
      aliases,
      unresolvedFlags: row.unresolvedFlags,
      majorInactiveKnown: row.majorInactiveKnown,
      commenceTime: row.commenceTime,
      flag,
      nowMs: opts?.nowMs,
      kickoffBufferMs: buffer,
    });
    const receipt = receiptFromVerdict(verdict);
    if (!verdict.failClosed) {
      return {
        ...row,
        gameId: gameId || row.gameId,
        inactiveSuppress: receipt,
        fairCompareEligible: row.fairCompareEligible === false ? false : true,
      };
    }
    const next = stripSuppressedFairEdgeChrome(row);
    next.gameId = gameId || row.gameId;
    next.inactiveSuppress = receipt;
    next.fairCompareEligible = false;
    return next;
  });
}

export function rowHasNflFairSuppress(
  row:
    | Pick<
        NflInactiveFairSuppressRowFields,
        "fairCompareEligible" | "inactiveSuppress"
      >
    | null
    | undefined,
): boolean {
  if (!row) return false;
  if (row.fairCompareEligible === false) return true;
  return row.inactiveSuppress?.state === "SUPPRESSED";
}
