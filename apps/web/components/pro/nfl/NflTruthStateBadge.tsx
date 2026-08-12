import type { NflTruthUiState } from "@/lib/nfl-truth-label";

const STATE_CLASS: Record<NflTruthUiState, string> = {
  LIVE: "border-edge-green/40 bg-edge-green/10 text-edge-green",
  MODEL: "border-kos-gold/40 bg-kos-gold/10 text-kos-gold",
  PRESEASON: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  ARCHIVE: "border-white/20 bg-white/5 text-kos-text/70",
};

export default function NflTruthStateBadge({
  state,
  className = "",
}: {
  state: NflTruthUiState;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${STATE_CLASS[state]} ${className}`}
      data-testid="nfl-truth-state"
      data-truth-state={state}
    >
      {state}
    </span>
  );
}

export function NflTruthStateBadges({
  states,
  className = "",
}: {
  states: NflTruthUiState[];
  className?: string;
}) {
  const unique = [...new Set(states)];
  if (unique.length === 0) return null;
  return (
    <span className={`inline-flex flex-wrap items-center gap-1.5 ${className}`}>
      {unique.map((state) => (
        <NflTruthStateBadge key={state} state={state} />
      ))}
    </span>
  );
}
