import SportProShell from "@/components/pro/SportProShell";

/** Shared Pro chrome for static /pro/nba/* routes (fair-lines, edges). */
export default function NbaProLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SportProShell sport="nba">{children}</SportProShell>;
}
