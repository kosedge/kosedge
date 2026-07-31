import SportProShell from "@/components/pro/SportProShell";

/** Shared Pro chrome for static /pro/mlb/* routes (fair-lines, edges). */
export default function MlbProLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SportProShell sport="mlb">{children}</SportProShell>;
}
