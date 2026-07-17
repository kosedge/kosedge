import Link from "next/link";
import type { TeamIntelFilters } from "@/lib/nfl-team-intel";

type TeamOption = {
  code: string;
  name: string;
};

export default function TeamIntelFilterBar({
  title,
  subtitle,
  basePath,
  filters,
  teamOptions,
  selectedTeam,
  showTeamSelect = false,
  showLeagueFilters = true,
}: {
  title: string;
  subtitle: string;
  basePath: string;
  filters: TeamIntelFilters;
  teamOptions: TeamOption[];
  selectedTeam?: string;
  showTeamSelect?: boolean;
  showLeagueFilters?: boolean;
}) {
  const season = filters.season ? String(filters.season) : "";
  const week = filters.week ? String(filters.week) : "";
  const conference = filters.conference ?? "";
  const division = filters.division ?? "";
  const query = filters.query ?? "";

  return (
    <section className="sticky top-16 z-20 rounded-2xl border border-white/10 bg-black/75 p-4 shadow-xl backdrop-blur-xl">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-kos-gold">Team Intel Controls</p>
          <h2 className="mt-1 text-lg font-semibold text-kos-text">{title}</h2>
          <p className="mt-1 text-xs text-kos-text/70">{subtitle}</p>
        </div>
        <Link
          href="/pro/nfl/overview"
          className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text transition hover:border-kos-gold/40 hover:text-kos-gold"
        >
          Back to NFL Overview
        </Link>
      </div>

      <form action={basePath} className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        {showTeamSelect ? (
          <label className="flex flex-col gap-1 text-xs text-kos-text/70">
            Team
            <select
              name="team"
              defaultValue={selectedTeam ?? ""}
              className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50"
            >
              {teamOptions.map((team) => (
                <option key={team.code} value={team.code}>
                  {team.code} · {team.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <label className="flex flex-col gap-1 text-xs text-kos-text/70">
          Season
          <input
            type="number"
            name="season"
            min={2010}
            max={2100}
            defaultValue={season}
            placeholder="Latest"
            className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-kos-text/70">
          Week
          <input
            type="number"
            name="week"
            min={1}
            max={25}
            defaultValue={week}
            placeholder="Latest"
            className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50"
          />
        </label>
        {showLeagueFilters ? (
          <label className="flex flex-col gap-1 text-xs text-kos-text/70">
            Conference
            <select
              name="conference"
              defaultValue={conference}
              className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50"
            >
              <option value="">All</option>
              <option value="AFC">AFC</option>
              <option value="NFC">NFC</option>
            </select>
          </label>
        ) : null}
        {showLeagueFilters ? (
          <label className="flex flex-col gap-1 text-xs text-kos-text/70">
            Division
            <select
              name="division"
              defaultValue={division}
              className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50"
            >
              <option value="">All</option>
              <option value="East">East</option>
              <option value="North">North</option>
              <option value="South">South</option>
              <option value="West">West</option>
            </select>
          </label>
        ) : null}
        <label className="flex flex-col gap-1 text-xs text-kos-text/70">
          Team Search
          <input
            type="text"
            name="q"
            defaultValue={query}
            placeholder="Bills, BUF, Chiefs..."
            className="rounded-lg border border-white/15 bg-black/50 px-2 py-2 text-sm text-kos-text outline-none transition focus:border-kos-gold/50"
          />
        </label>
        <button
          type="submit"
          className="rounded-lg border border-kos-gold/40 bg-kos-gold/15 px-3 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25"
        >
          Apply Filters
        </button>
      </form>
    </section>
  );
}
