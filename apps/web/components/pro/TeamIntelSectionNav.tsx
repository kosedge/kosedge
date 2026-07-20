import Link from "next/link";
import type { NflTeamIntelView, TeamIntelFilters } from "@/lib/nfl-team-intel";
import { buildTeamIntelHref } from "@/lib/nfl-team-intel";

const VIEW_META: Array<{ key: NflTeamIntelView; label: string }> = [
  { key: "overview", label: "Overview" },
  { key: "stats", label: "Stats" },
  { key: "depth-chart", label: "Depth Chart" },
  { key: "injuries", label: "Injuries" },
  { key: "splits", label: "Splits" },
  { key: "tendencies", label: "Tendencies" },
];

export default function TeamIntelSectionNav({
  activeView,
  team,
  filters,
}: {
  activeView: NflTeamIntelView;
  team: string;
  filters: Pick<TeamIntelFilters, "season" | "week">;
}) {
  return (
    <nav className="mt-4 overflow-x-auto pb-1" aria-label="Team Intel sections">
      <div className="inline-flex min-w-full gap-2 rounded-xl border border-white/10 bg-black/30 p-1">
        {VIEW_META.map((view) => {
          const isActive = view.key === activeView;
          return (
            <Link
              key={view.key}
              href={buildTeamIntelHref(team, view.key, filters)}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                isActive
                  ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                  : "border border-transparent text-kos-text/80 hover:border-kos-gold/25 hover:text-kos-text"
              }`}
            >
              {view.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
