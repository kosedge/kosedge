import SportProShell from "@/components/pro/SportProShell";

/** Shared Pro chrome for static /pro/wnba/* routes (fair-lines). */
export default function WnbaProLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SportProShell sport="wnba">{children}</SportProShell>;
}
