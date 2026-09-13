/**
 * Interim Product store for NFL inactive fair suppress (SOP v1.1).
 *
 * Server-only. SI→builder auto-detect is out of scope.
 *
 * Set a per-game flag (Product owner), then remat success / CoS clear revokes:
 *
 * 1. Edit repo-root `data/ops/nfl-inactive-suppress.json` (Product SoT)
 *    and mirror the same object to `apps/web/lib/ops/nfl-inactive-suppress.json`
 *    (Vercel packaged copy — CI asserts the two stay in sync).
 * 2. Or env `NFL_INACTIVE_SUPPRESS_JSON` (inline store JSON)
 * 3. Or env `NFL_INACTIVE_SUPPRESS` (comma-separated gameIds / AWAY@HOME aliases)
 * 4. Or env `NFL_INACTIVE_SUPPRESS_PATH` (alternate JSON file)
 *
 * Canonical gameId: NFL fair-lines / schedule `game_id` (e.g. `2026-W01-ATL@PIT`).
 * Revoke: set `rematRunId` to the remat receipt, or `clearedBy: "cos"`.
 *
 * Vercel: Root Directory is `apps/web`. `../../data/ops/**` NFT includes land
 * outside `{cwd}/data/ops` on `/var/task`, so `findRepoRoot()` misses the
 * repo-root file. The in-app packaged copy + static import survive that layout.
 * Do not place a copy at `apps/web/data/ops/` — other loaders treat `data/ops`
 * as the monorepo marker and would stop at the Next app root.
 */

import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import {
  emptyNflInactiveSuppressStore,
  NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS,
  NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
  type NflInactiveSuppressFlag,
  type NflInactiveSuppressStore,
} from "@/lib/nfl-inactive-fair-suppress";
import packagedStoreJson from "@/lib/ops/nfl-inactive-suppress.json";

export const NFL_INACTIVE_SUPPRESS_FILENAME = "nfl-inactive-suppress.json";

/** Inside the Next app (Vercel / `next start` cwd). */
export const NFL_INACTIVE_SUPPRESS_IN_APP_REL = path.join(
  "lib",
  "ops",
  NFL_INACTIVE_SUPPRESS_FILENAME,
);

/** Repo-root Product SoT (local monorepo). */
export const NFL_INACTIVE_SUPPRESS_REPO_REL = path.join(
  "data",
  "ops",
  NFL_INACTIVE_SUPPRESS_FILENAME,
);

export type ResolveNflInactiveSuppressStorePathOptions = {
  cwd?: string;
  exists?: (filePath: string) => boolean;
};

export type LoadNflInactiveSuppressStoreOptions =
  ResolveNflInactiveSuppressStorePathOptions & {
    env?: NodeJS.ProcessEnv;
    readJson?: (filePath: string) => unknown | null;
  };

/**
 * FS candidates for the durable JSON store (no env).
 * In-app packaged copy first so Vercel `{cwd}/lib/ops/...` wins over a
 * repo-root `data/ops` that NFT cannot place next to `/var/task`.
 */
export function resolveNflInactiveSuppressStoreCandidates(
  cwd: string = process.cwd(),
): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const add = (filePath: string) => {
    const resolved = path.resolve(filePath);
    if (seen.has(resolved)) return;
    seen.add(resolved);
    out.push(resolved);
  };

  add(path.join(cwd, NFL_INACTIVE_SUPPRESS_IN_APP_REL));

  let current = cwd;
  for (let depth = 0; depth < 6; depth += 1) {
    add(path.join(current, NFL_INACTIVE_SUPPRESS_IN_APP_REL));
    add(path.join(current, "apps", "web", NFL_INACTIVE_SUPPRESS_IN_APP_REL));
    add(path.join(current, NFL_INACTIVE_SUPPRESS_REPO_REL));
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }

  return out;
}

export function resolveNflInactiveSuppressStorePath(
  options: ResolveNflInactiveSuppressStorePathOptions = {},
): string | null {
  const cwd = options.cwd ?? process.cwd();
  const exists = options.exists ?? existsSync;
  for (const candidate of resolveNflInactiveSuppressStoreCandidates(cwd)) {
    if (exists(candidate)) return candidate;
  }
  return null;
}

function asRecord(raw: unknown): Record<string, unknown> | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

function parseFlag(raw: unknown): NflInactiveSuppressFlag | null {
  const o = asRecord(raw);
  if (!o) return null;
  const markets = Array.isArray(o.markets)
    ? o.markets.map((m) => String(m))
    : undefined;
  const players = Array.isArray(o.players)
    ? o.players.map((p) => String(p))
    : undefined;
  const classes = Array.isArray(o.classes)
    ? o.classes.map((c) => String(c))
    : undefined;
  const aliases = Array.isArray(o.aliases)
    ? o.aliases.map((a) => String(a))
    : undefined;
  return {
    markets,
    reason: typeof o.reason === "string" ? o.reason : undefined,
    players,
    classes,
    setBy: typeof o.setBy === "string" ? o.setBy : undefined,
    setAt: typeof o.setAt === "string" ? o.setAt : undefined,
    ttl:
      typeof o.ttl === "string" || typeof o.ttl === "number"
        ? o.ttl
        : undefined,
    ttlUntil: typeof o.ttlUntil === "string" ? o.ttlUntil : undefined,
    rematRunId:
      o.rematRunId === null
        ? null
        : typeof o.rematRunId === "string"
          ? o.rematRunId
          : undefined,
    clearedBy:
      o.clearedBy === null
        ? null
        : typeof o.clearedBy === "string"
          ? o.clearedBy
          : undefined,
    state:
      o.state === "CLEAR" || o.state === "SUPPRESSED" ? o.state : undefined,
    aliases,
  };
}

function parseGames(raw: unknown): Record<string, NflInactiveSuppressFlag> {
  const o = asRecord(raw);
  if (!o) return {};
  const out: Record<string, NflInactiveSuppressFlag> = {};
  for (const [key, value] of Object.entries(o)) {
    const flag = parseFlag(value);
    if (flag) out[String(key)] = flag;
  }
  return out;
}

export function parseNflInactiveSuppressStore(
  raw: unknown,
): NflInactiveSuppressStore {
  const o = asRecord(raw);
  if (!o) return emptyNflInactiveSuppressStore();
  const games = parseGames(o.games ?? o.nfl_inactive_suppress);
  return {
    version: typeof o.version === "number" ? o.version : 1,
    gameIdConvention: "nfl_fair_line_game_id",
    kickoffBufferMs:
      typeof o.kickoffBufferMs === "number" &&
      Number.isFinite(o.kickoffBufferMs)
        ? o.kickoffBufferMs
        : NFL_INACTIVE_SUPPRESS_KICKOFF_BUFFER_MS,
    games,
  };
}

function storeFromIdList(csv: string): NflInactiveSuppressStore {
  const store = emptyNflInactiveSuppressStore();
  const now = new Date().toISOString();
  for (const token of csv.split(",")) {
    const gameId = token.trim();
    if (!gameId) continue;
    store.games![gameId] = {
      reason: NFL_INACTIVE_SUPPRESS_REASON_MAJOR,
      classes: ["MAJOR"],
      setBy: "product",
      setAt: now,
      rematRunId: null,
    };
  }
  return store;
}

function readJsonFile(filePath: string): unknown | null {
  try {
    return JSON.parse(readFileSync(filePath, "utf8")) as unknown;
  } catch {
    return null;
  }
}

function envOf(
  options: LoadNflInactiveSuppressStoreOptions,
): NodeJS.ProcessEnv {
  return options.env ?? process.env;
}

/**
 * Load the durable per-game flag store.
 * Precedence: inline JSON env → comma-id env → path env → in-app packaged
 * file → repo-root ops JSON → bundled JSON import (always present in the
 * serverless module graph).
 */
export function loadNflInactiveSuppressStore(
  options: LoadNflInactiveSuppressStoreOptions = {},
): NflInactiveSuppressStore {
  const env = envOf(options);
  const inline = env.NFL_INACTIVE_SUPPRESS_JSON?.trim();
  if (inline) {
    try {
      return parseNflInactiveSuppressStore(JSON.parse(inline));
    } catch {
      return emptyNflInactiveSuppressStore();
    }
  }

  const ids = env.NFL_INACTIVE_SUPPRESS?.trim();
  if (ids) return storeFromIdList(ids);

  const exists = options.exists ?? existsSync;
  const readJson = options.readJson ?? readJsonFile;
  const pathOverride = env.NFL_INACTIVE_SUPPRESS_PATH?.trim();
  const filePath =
    pathOverride ||
    resolveNflInactiveSuppressStorePath({
      cwd: options.cwd,
      exists,
    });
  if (filePath && exists(filePath)) {
    const parsed = readJson(filePath);
    if (parsed != null) return parseNflInactiveSuppressStore(parsed);
  }

  return parseNflInactiveSuppressStore(packagedStoreJson);
}
