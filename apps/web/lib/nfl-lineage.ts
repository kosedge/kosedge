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
};

export type NflWebLaunchPointerLike = {
  active_run_id?: string;
  bundle_id?: string;
  engine_version?: string;
  generated_at_utc?: string;
  locked_at_utc?: string;
  kind?: NflProjectionKind;
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
  };
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
