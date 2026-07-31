import NflProShell from "@/components/pro/nfl/NflProShell";

/**
 * Wraps all static /pro/nfl/* routes with the shared NFL Pro chrome.
 * Dynamic [sport] NFL routes (overview historically, standings, etc.) use
 * [sport]/layout which also mounts NflProShell for sport === "nfl".
 */
export default function NflProLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <NflProShell>{children}</NflProShell>;
}
