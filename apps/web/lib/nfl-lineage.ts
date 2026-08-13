/**
 * NFL Truth Layer lineage stamps.
 * Multiple numbers are OK when kind/run lineage is explicit.
 */

export type NflProjectionKind =
  | "Model"
  | "KEI"
  | "Market"
  | "Editorial"
  | "Scenario";

export type NflLineage = {
  run_id: string;
  engine_version: string | null;
  generated_at: string | null;
  kind: NflProjectionKind;
  lockTag?: string | null;
  nTeamSims?: number | null;
};

export type NflWebLaunchPointerLike = {
  active_run_id?: string;
  bundle_id?: string;
  engine_version?: string;
  generated_at_utc?: string;
  locked_at_utc?: string;
  kind?: NflProjectionKind;
  lock_tag?: string;
  n_team_sims?: number;
  identity?: string;
};

/** Production NFL projection set pointer → lineage for Model surfaces. */
export function lineageFromActiveRun(
  pointer: NflWebLaunchPointerLike | null | undefined,
  kind: NflProjectionKind = "Model",
): NflLineage | null {
  if (!pointer) return null;
  const runId = pointer.active_run_id || pointer.bundle_id;
  if (!runId) return null;
  return {
    run_id: runId,
    engine_version: pointer.engine_version ?? null,
    generated_at: pointer.generated_at_utc ?? pointer.locked_at_utc ?? null,
    kind: pointer.kind ?? kind,
    lockTag: pointer.lock_tag ?? null,
    nTeamSims:
      typeof pointer.n_team_sims === "number" ? pointer.n_team_sims : null,
  };
}

/** Overlay live desk engine_version when status is available (do not invent run_id). */
export function withEngineVersionOverride(
  lineage: NflLineage | null | undefined,
  engineVersion: string | null | undefined,
): NflLineage | null {
  if (!lineage) return null;
  const next = engineVersion?.trim();
  if (!next) return lineage;
  return { ...lineage, engine_version: next };
}

/** Team previews / copy that are not tied to the active run. */
export function editorialSnapshotLineage(asOf: string | null): NflLineage {
  return {
    run_id: "editorial-snapshot",
    engine_version: null,
    generated_at: asOf,
    kind: "Editorial",
  };
}

export const EDITORIAL_SNAPSHOT_NOTE =
  "editorial snapshot — not active run";

/** Readable truncate for compact chips; full string stays on title/hover. */
export function truncateRunId(runId: string, maxLen = 28): string {
  const s = runId.trim();
  if (s.length <= maxLen) return s;
  const head = Math.max(8, Math.floor((maxLen - 1) / 2));
  const tail = Math.max(6, maxLen - head - 1);
  return `${s.slice(0, head)}…${s.slice(-tail)}`;
}

/** Prefer short engine label (e.g. v1.27-kicker-layer). */
export function shortEngineVersion(version: string | null | undefined): string | null {
  if (!version?.trim()) return null;
  const v = version.trim();
  const stripped = v.replace(/^nfl-season-engine-/i, "");
  return stripped || v;
}

/** YYYY-MM-DD from ISO / date string when parseable. */
export function lineageAsOfDate(generatedAt: string | null | undefined): string | null {
  if (!generatedAt?.trim()) return null;
  const raw = generatedAt.trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
  const ms = Date.parse(raw);
  if (!Number.isFinite(ms)) return null;
  return new Date(ms).toISOString().slice(0, 10);
}
