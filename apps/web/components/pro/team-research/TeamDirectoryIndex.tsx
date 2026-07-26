import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import {
  assignTeamPreviewWriter,
  groupTeamsByConference,
  teamResearchHref,
  type TeamDirectoryEntry,
  type TeamResearchSportConfig,
} from "@/lib/team-research";

export default function TeamDirectoryIndex({
  sportName,
  base,
  config,
  teams,
}: {
  sportName: string;
  base: string;
  config: TeamResearchSportConfig;
  teams: TeamDirectoryEntry[];
}) {
  const groups = groupTeamsByConference(teams);
  const liveCount = config.sections.filter((s) => s.status === "live").length;
  const pendingCount = config.sections.filter(
    (s) => s.status === "pending",
  ).length;

  return (
    <SportHubShell
      sportName={sportName}
      base={base}
      badge={`${sportName} League Intel`}
      title={config.directoryLabel}
      summary={config.summary}
      primaryHref={`/edge-board/${config.sportKey}`}
      primaryLabel="Edge board →"
      secondaryHref={`/pro/power-ratings/${config.sportKey}`}
      secondaryLabel="Power ratings →"
    >
      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.14em] text-kos-gold">
              Team directory
            </p>
            <p className="mt-1 text-sm text-kos-text/75">
              {teams.length} teams · {liveCount} live section types ·{" "}
              {pendingCount} pending section types
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px]">
            <span className="rounded-full border border-emerald-400/35 bg-emerald-400/10 px-2 py-1 text-emerald-200">
              Live where wired
            </span>
            <span className="rounded-full border border-amber-400/35 bg-amber-400/10 px-2 py-1 text-amber-100">
              Honest empty states
            </span>
          </div>
        </div>
      </section>

      <div className="mt-6 space-y-8">
        {groups.map((group) => (
          <section key={group.conference}>
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
              {group.conference}
            </h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {group.teams.map((team) => {
                const assignment = assignTeamPreviewWriter(
                  config.sportKey,
                  team,
                );
                return (
                  <Link
                    key={team.slug}
                    href={teamResearchHref(config.sportKey, team.slug)}
                    className="group rounded-2xl border border-white/10 bg-black/35 p-4 transition hover:border-kos-gold/45 hover:bg-black/45"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-kos-gold">
                          {team.code}
                        </p>
                        <h3 className="mt-1 text-lg font-semibold text-kos-text">
                          {team.name}
                        </h3>
                      </div>
                      <span className="rounded-full border border-white/15 bg-white/5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-kos-text/70">
                        Research
                      </span>
                    </div>
                    <p className="mt-3 text-xs text-kos-text/60">
                      Preview by {assignment.writer.name}
                      {assignment.provisional ? " · provisional" : ""}
                    </p>
                    <p className="mt-1 text-xs text-kos-text/50">
                      Record · data pending · Next game · data pending
                    </p>
                  </Link>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </SportHubShell>
  );
}
