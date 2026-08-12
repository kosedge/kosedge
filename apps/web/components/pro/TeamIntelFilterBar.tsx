"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import type { TeamIntelFilters } from "@/lib/nfl-team-intel";
import { isNflCalendarPreseason, NFL_PRODUCT_SEASON } from "@/lib/nfl-truth-label";
import {
  InstantFilterBar,
  InstantSelect,
  InstantTextInput,
} from "@/components/pro/InstantFilterBar";

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
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const season = filters.season ? String(filters.season) : "";
  const week = filters.week ? String(filters.week) : "";
  const conference = filters.conference ?? "";
  const division = filters.division ?? "";
  const query = filters.query ?? "";
  const preseasonLatest = isNflCalendarPreseason(
    filters.season ?? NFL_PRODUCT_SEASON,
  );

  function buildHref(updates: Record<string, string | null | undefined>) {
    const params = new URLSearchParams();
    const next = {
      season,
      week,
      conference: showLeagueFilters ? conference : "",
      division: showLeagueFilters ? division : "",
      q: query,
      ...updates,
    };
    for (const [key, value] of Object.entries(next)) {
      if (value) params.set(key, value);
    }
    const qs = params.toString();

    // Team changes navigate by path segment — never via ?team= (avoids Bills remap bugs).
    if (showTeamSelect && updates.team != null && updates.team !== "") {
      const viewMatch = basePath.match(
        /\/pro\/nfl\/teams\/[^/]+\/([^/?]+)/,
      );
      const view = viewMatch?.[1] ?? "overview";
      const path = `/pro/nfl/teams/${updates.team}/${view}`;
      return qs ? `${path}?${qs}` : path;
    }

    return qs ? `${basePath}?${qs}` : basePath;
  }

  function navigate(updates: Record<string, string | null | undefined>) {
    startTransition(() => {
      router.replace(buildHref(updates), { scroll: false });
    });
  }

  return (
    <InstantFilterBar>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-kos-gold">
            Research filters
          </p>
          <h2 className="mt-1 text-lg font-semibold text-kos-text">{title}</h2>
          <p className="mt-1 text-xs text-kos-text/70">{subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/pro/nfl/overview"
            className="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text transition hover:border-kos-gold/40 hover:text-kos-gold"
          >
            NFL Overview
          </Link>
          <Link
            href="/edge-board/nfl"
            className="rounded-lg border border-kos-gold/30 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold transition hover:border-kos-gold/50"
          >
            Edge Board
          </Link>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        {showTeamSelect ? (
          <InstantSelect
            name="team"
            label="Team"
            value={selectedTeam ?? ""}
            pending={pending}
            onChange={(value) => navigate({ team: value })}
            options={teamOptions.map((team) => ({
              value: team.code,
              label: `${team.code} · ${team.name}`,
            }))}
          />
        ) : null}
        <InstantSelect
          name="season"
          label="Season"
          value={season}
          pending={pending}
          onChange={(value) => navigate({ season: value || null })}
          options={[
            { value: "", label: "Latest" },
            { value: "2026", label: "2026" },
            { value: "2025", label: "2025" },
            { value: "2024", label: "2024" },
          ]}
        />
        <InstantSelect
          name="week"
          label="Week"
          value={week}
          pending={pending}
          onChange={(value) => navigate({ week: value || null })}
          options={[
            { value: "", label: preseasonLatest ? "Preseason" : "Latest" },
            ...Array.from({ length: 22 }, (_, i) => ({
              value: String(i + 1),
              label: `Week ${i + 1}`,
            })),
          ]}
        />
        {showLeagueFilters ? (
          <InstantSelect
            name="conference"
            label="Conference"
            value={conference}
            pending={pending}
            onChange={(value) => navigate({ conference: value || null })}
            options={[
              { value: "", label: "All" },
              { value: "AFC", label: "AFC" },
              { value: "NFC", label: "NFC" },
            ]}
          />
        ) : null}
        {showLeagueFilters ? (
          <InstantSelect
            name="division"
            label="Division"
            value={division}
            pending={pending}
            onChange={(value) => navigate({ division: value || null })}
            options={[
              { value: "", label: "All" },
              { value: "East", label: "East" },
              { value: "North", label: "North" },
              { value: "South", label: "South" },
              { value: "West", label: "West" },
            ]}
          />
        ) : null}
        <InstantTextInput
          name="q"
          label="Team search"
          value={query}
          placeholder="Chiefs, KC, Packers…"
          pending={pending}
          onCommit={(value) => navigate({ q: value.trim() || null })}
        />
      </div>
      {pending ? (
        <p className="mt-2 text-[11px] text-kos-text/45">Updating…</p>
      ) : null}
    </InstantFilterBar>
  );
}
