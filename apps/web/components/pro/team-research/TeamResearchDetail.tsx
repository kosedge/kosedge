import Link from "next/link";
import TeamPreviewSlot from "@/components/pro/team-research/TeamPreviewSlot";
import TeamResearchSection from "@/components/pro/team-research/TeamResearchSection";
import {
  assignTeamPreviewWriter,
  parkFactorForTeam,
  teamResearchIndexHref,
  type TeamDirectoryEntry,
  type TeamResearchSportConfig,
} from "@/lib/team-research";

export default function TeamResearchDetail({
  sportName,
  config,
  team,
}: {
  sportName: string;
  config: TeamResearchSportConfig;
  team: TeamDirectoryEntry;
}) {
  const assignment = assignTeamPreviewWriter(config.sportKey, team);
  const conferenceLine = team.division
    ? `${team.conference} ${team.division}`
    : team.conference;
  const parkFactor = parkFactorForTeam(config.sportKey, team.code);
  const indexHref = teamResearchIndexHref(config.sportKey);
  const hubHref = `/pro/${config.sportKey}/overview`;

  const sectionByKey = Object.fromEntries(
    config.sections.map((section) => [section.key, section]),
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-3 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href={hubHref} className="hover:text-kos-gold">
          {sportName} Overview
        </Link>
        <span>/</span>
        <Link href={indexHref} className="hover:text-kos-gold">
          Teams
        </Link>
        <span>/</span>
        <span className="text-kos-text">{team.name}</span>
      </nav>

      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/45 to-black/65 p-5 sm:p-6">
        <p className="text-xs uppercase tracking-[0.15em] text-kos-gold">
          Team research
        </p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-kos-text">
              {team.name}
            </h1>
            <p className="mt-2 text-sm text-kos-text/75">
              {team.code} · {conferenceLine}
            </p>
          </div>
          <div className="grid gap-2 text-right text-sm text-kos-text/80">
            <p>
              <span className="text-kos-text/55">Record</span> · data pending
            </p>
            <p>
              <span className="text-kos-text/55">Next game</span> · data pending
            </p>
          </div>
        </div>
        <p className="mt-3 max-w-3xl text-sm text-kos-text/70">
          Handicapping research shell for {sportName}. Live sections show wired
          data only; everything else stays explicitly pending.
        </p>
      </section>

      <div className="mt-5 grid gap-4">
        {sectionByKey.preview ? (
          <TeamPreviewSlot
            teamName={team.name}
            teamCode={config.sportKey === "nfl" ? team.code : undefined}
            writer={assignment.writer}
            assignmentNote={assignment.note}
            provisional={assignment.provisional}
          />
        ) : null}

        <div className="grid gap-4 xl:grid-cols-2">
          {config.sections
            .filter((s) => s.key !== "preview" && s.key !== "market_links")
            .map((section) => {
              if (section.key === "park_factors" && parkFactor) {
                return (
                  <TeamResearchSection key={section.key} config={section}>
                    <dl className="grid gap-2 sm:grid-cols-2">
                      <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                        <dt className="text-[11px] uppercase tracking-wide text-kos-text/60">
                          Runs factor
                        </dt>
                        <dd className="mt-1 text-sm font-semibold text-kos-text">
                          {parkFactor}
                        </dd>
                      </div>
                      <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                        <dt className="text-[11px] uppercase tracking-wide text-kos-text/60">
                          Source
                        </dt>
                        <dd className="mt-1 text-sm text-kos-text/80">
                          Model park prior (static reference)
                        </dd>
                      </div>
                    </dl>
                  </TeamResearchSection>
                );
              }

              if (section.key === "stats") {
                return (
                  <TeamResearchSection key={section.key} config={section}>
                    <ul className="grid gap-2 sm:grid-cols-2">
                      {config.statsLabels.map((label) => (
                        <li
                          key={label}
                          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/75"
                        >
                          {label}
                          <span className="mt-1 block text-xs text-kos-text/50">
                            Data pending
                          </span>
                        </li>
                      ))}
                    </ul>
                  </TeamResearchSection>
                );
              }

              if (section.key === "coaching") {
                return (
                  <TeamResearchSection key={section.key} config={section}>
                    <p className="text-xs uppercase tracking-wide text-kos-text/55">
                      {config.coachingLabel}
                    </p>
                    <p className="mt-2 text-sm text-kos-text/70">
                      {section.emptyCopy}
                    </p>
                  </TeamResearchSection>
                );
              }

              if (section.key === "depth") {
                return (
                  <TeamResearchSection key={section.key} config={section}>
                    <p className="text-xs uppercase tracking-wide text-kos-text/55">
                      {config.depthLabel}
                    </p>
                    <p className="mt-2 text-sm text-kos-text/70">
                      {section.emptyCopy}
                    </p>
                  </TeamResearchSection>
                );
              }

              return <TeamResearchSection key={section.key} config={section} />;
            })}
        </div>

        {sectionByKey.market_links ? (
          <TeamResearchSection config={sectionByKey.market_links}>
            <div className="flex flex-wrap gap-2">
              {config.marketLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="inline-flex rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
                >
                  {link.label} →
                </Link>
              ))}
            </div>
          </TeamResearchSection>
        ) : null}
      </div>
    </main>
  );
}
