import type { ReactNode } from "react";
import SportProShell from "@/components/pro/SportProShell";

/**
 * NFL Pro chrome — thin wrapper over SportProShell for backwards compatibility.
 */
export default function NflProShell({
  children,
  showFreshness = true,
  pageTitle,
  pageSubtitle,
  actions,
}: {
  children: ReactNode;
  showFreshness?: boolean;
  pageTitle?: string;
  pageSubtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <SportProShell
      sport="nfl"
      showFreshness={showFreshness}
      pageTitle={pageTitle}
      pageSubtitle={pageSubtitle}
      actions={actions}
    >
      {children}
    </SportProShell>
  );
}
