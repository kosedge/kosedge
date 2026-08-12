import TruthStateBadge, {
  TruthStateBadges,
} from "@/components/pro/TruthStateBadge";
import type { NflTruthUiState } from "@/lib/nfl-truth-label";

export default function NflTruthStateBadge({
  state,
  className = "",
}: {
  state: NflTruthUiState;
  className?: string;
}) {
  return (
    <TruthStateBadge
      state={state}
      className={className}
      testId="nfl-truth-state"
    />
  );
}

export function NflTruthStateBadges({
  states,
  className = "",
}: {
  states: NflTruthUiState[];
  className?: string;
}) {
  return (
    <TruthStateBadges
      states={states}
      className={className}
      testId="nfl-truth-state"
    />
  );
}
