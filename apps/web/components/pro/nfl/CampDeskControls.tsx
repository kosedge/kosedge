"use client";

import { useRouter } from "next/navigation";
import { NFL_TEAM_DIRECTORY } from "@/lib/nfl-team-intel";
import { formatCampDeskDayLabel } from "@/lib/nfl-camp-desk-daily";

type CampDeskControlsProps = {
  team: string | null;
  date: string | null;
  latestDeskDate: string | null;
  deskDates: string[];
};

function buildCampHref(
  team: string | null,
  date: string | null,
  latest: string | null,
) {
  const params = new URLSearchParams();
  if (team) params.set("team", team);
  if (date && latest && date !== latest) params.set("date", date);
  const qs = params.toString();
  return qs ? `/pro/nfl/camp?${qs}` : "/pro/nfl/camp";
}

export default function CampDeskControls({
  team,
  date,
  latestDeskDate,
  deskDates,
}: CampDeskControlsProps) {
  const router = useRouter();
  const activeDate = date ?? latestDeskDate ?? "";

  return (
    <div
      className="mt-5 flex flex-wrap items-end gap-3 rounded-2xl border border-white/10 bg-black/25 p-3 sm:p-4"
      data-testid="camp-desk-controls"
    >
      <label className="text-sm text-kos-text/70">
        Team
        <select
          value={team ?? ""}
          aria-label="Team"
          className="mt-1 block min-h-11 min-w-[12rem] rounded-lg border border-white/15 bg-black/50 px-3 text-sm text-kos-text"
          onChange={(event) => {
            const next = event.target.value.trim().toUpperCase() || null;
            router.push(
              buildCampHref(next, activeDate || null, latestDeskDate),
            );
          }}
        >
          <option value="">All teams with notes</option>
          {NFL_TEAM_DIRECTORY.map((row) => (
            <option key={row.code} value={row.code}>
              {row.code} · {row.name}
            </option>
          ))}
        </select>
      </label>

      {deskDates.length > 1 ? (
        <label className="text-sm text-kos-text/70">
          Desk day
          <select
            value={activeDate}
            aria-label="Desk day"
            className="mt-1 block min-h-11 min-w-[12rem] rounded-lg border border-white/15 bg-black/50 px-3 text-sm text-kos-text"
            onChange={(event) => {
              const next = event.target.value.trim() || null;
              router.push(buildCampHref(team, next, latestDeskDate));
            }}
          >
            {deskDates.map((deskDate) => (
              <option key={deskDate} value={deskDate}>
                {formatCampDeskDayLabel(deskDate)}
                {deskDate === latestDeskDate ? " · today" : ""}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {team || (date && latestDeskDate && date !== latestDeskDate) ? (
        <button
          type="button"
          className="min-h-11 text-sm text-kos-text/60 hover:text-kos-text"
          onClick={() => router.push("/pro/nfl/camp")}
        >
          Clear
        </button>
      ) : null}
    </div>
  );
}
