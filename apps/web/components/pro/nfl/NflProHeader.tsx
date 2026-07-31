"use client";

import SportProHeader from "@/components/pro/SportProHeader";

/** NFL header — thin wrapper over SportProHeader for backwards compatibility. */
export default function NflProHeader({
  activeSport = "nfl",
  showSportsNav = true,
}: {
  activeSport?: string;
  showSportsNav?: boolean;
}) {
  return (
    <SportProHeader activeSport={activeSport} showSportsNav={showSportsNav} />
  );
}
