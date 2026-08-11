import {
  EDITORIAL_SNAPSHOT_NOTE,
  lineageAsOfDate,
  shortEngineVersion,
  truncateRunId,
  type NflLineage,
} from "@/lib/nfl-lineage";

/**
 * Quiet lineage chip for NFL projection surfaces.
 * Dark-board friendly; wraps under titles on mobile.
 */
export default function NflLineageBadge({
  lineage,
  className = "",
}: {
  lineage: NflLineage | null | undefined;
  className?: string;
}) {
  if (!lineage) return null;

  if (lineage.kind === "Editorial") {
    const asOf = lineageAsOfDate(lineage.generated_at);
    const label = asOf ? `Editorial · ${asOf}` : "Editorial";
    return (
      <span
        className={`inline-flex max-w-full flex-wrap items-center gap-x-1.5 gap-y-0.5 rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] leading-snug text-kos-text/55 ${className}`}
        title={EDITORIAL_SNAPSHOT_NOTE}
        data-testid="nfl-lineage-badge"
        data-lineage-kind="Editorial"
      >
        <span className="font-semibold uppercase tracking-[0.1em] text-kos-text/45">
          Editorial
        </span>
        {asOf ? (
          <span className="tabular-nums text-kos-text/50">{asOf}</span>
        ) : null}
        <span className="sr-only">{label}</span>
      </span>
    );
  }

  const engine = shortEngineVersion(lineage.engine_version);
  const asOf = lineageAsOfDate(lineage.generated_at);
  const runShort = truncateRunId(lineage.run_id);
  const titleParts = [
    lineage.kind,
    `run ${lineage.run_id}`,
    lineage.engine_version ? `engine ${lineage.engine_version}` : null,
    asOf ? `as of ${asOf}` : null,
  ].filter(Boolean);

  return (
    <span
      className={`inline-flex max-w-full flex-wrap items-center gap-x-1.5 gap-y-0.5 rounded-md border border-white/10 bg-black/40 px-2 py-0.5 text-[10px] leading-snug text-kos-text/55 ${className}`}
      title={titleParts.join(" · ")}
      data-testid="nfl-lineage-badge"
      data-lineage-kind={lineage.kind}
      data-run-id={lineage.run_id}
    >
      <span className="font-semibold uppercase tracking-[0.1em] text-kos-text/40">
        {lineage.kind}
      </span>
      <span className="min-w-0 break-all font-mono tabular-nums text-kos-text/60">
        {runShort}
      </span>
      {engine ? (
        <>
          <span className="text-kos-text/25" aria-hidden>
            ·
          </span>
          <span className="text-kos-text/55">{engine}</span>
        </>
      ) : null}
      {asOf ? (
        <>
          <span className="text-kos-text/25" aria-hidden>
            ·
          </span>
          <span className="tabular-nums text-kos-text/45">{asOf}</span>
        </>
      ) : null}
    </span>
  );
}
