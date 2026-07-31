import SportProShell from "@/components/pro/SportProShell";

/**
 * Wraps all static /pro/nfl/* routes with the shared Pro chrome.
 */
export default function NflProLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SportProShell sport="nfl">{children}</SportProShell>;
}
