import FootballNumbersUnavailable from "@/components/FootballNumbersUnavailable";

/**
 * Fail-closed CFB Edge Board chrome. Same copy on the board page,
 * homepage hero, and pro edges entry.
 */
export default function CfbEdgeBoardUnavailable({
  showSelector = false,
  compact = false,
}: {
  showSelector?: boolean;
  compact?: boolean;
}) {
  return (
    <FootballNumbersUnavailable
      sport="cfb"
      showSelector={showSelector}
      compact={compact}
      title="CFB Edge Board"
    />
  );
}
