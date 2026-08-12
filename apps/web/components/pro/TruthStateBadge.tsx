import type { TruthUiState } from "@/lib/truth-ui-state";

const STATE_CLASS: Record<TruthUiState, string> = {
  LIVE: "border-edge-green/40 bg-edge-green/10 text-edge-green",
  MODEL: "border-kos-gold/40 bg-kos-gold/10 text-kos-gold",
  PRESEASON: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  ARCHIVE: "border-white/20 bg-white/5 text-kos-text/70",
};

export default function TruthStateBadge({
  state,
  className = "",
  testId = "truth-state",
}: {
  state: TruthUiState;
  className?: string;
  testId?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] ${STATE_CLASS[state]} ${className}`}
      data-testid={testId}
      data-truth-state={state}
    >
      {state}
    </span>
  );
}

export function TruthStateBadges({
  states,
  className = "",
  testId = "truth-state",
}: {
  states: TruthUiState[];
  className?: string;
  testId?: string;
}) {
  const unique = [...new Set(states)];
  if (unique.length === 0) return null;
  return (
    <span className={`inline-flex flex-wrap items-center gap-1.5 ${className}`}>
      {unique.map((state) => (
        <TruthStateBadge key={state} state={state} testId={testId} />
      ))}
    </span>
  );
}
