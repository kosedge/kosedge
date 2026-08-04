import SportProShell from "@/components/pro/SportProShell";

/**
 * Wraps static /pro/cfb/* routes (season model desks) with shared Pro chrome.
 */
export default function CfbProLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <SportProShell sport="cfb">{children}</SportProShell>;
}
