"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import { FantasyDeskNav } from "@/components/pro/nfl/fantasy/FantasyDeskNav";
import { AdpQaFlagChip } from "@/components/pro/nfl/fantasy/AdpQaFlagChip";
import { PlayerCombobox } from "@/components/pro/nfl/fantasy/PlayerCombobox";
import { formatAdp, valueLabel } from "@/lib/fantasy/adp-proxy";
import {
  notableValueNotes,
  tierCliffNote,
} from "@/lib/fantasy/expert";
import {
  bestAvailableByNeed,
  bestAvailableByValue,
  rosterNeeds,
  teamGrade,
  type ValueAwareSuggestion,
} from "@/lib/fantasy/team-builder";
import { draftAdviceClass } from "@/lib/fantasy/value-aware-recs";
import type { FantasyDeskBoard, FantasyDeskRow } from "@/lib/fantasy/types";
import {
  draftPositionBadgeClass,
  draftTierBadgeClass,
  draftTierLabel,
  FANTASY_DRAFT_POSITIONS,
  FANTASY_SCORING_PROFILES,
  type FantasyScoringProfile,
} from "@/lib/nfl-fantasy-draft-shared";

const POSITION_TABS = ["ALL", ...FANTASY_DRAFT_POSITIONS] as const;
const ROSTER_STORAGE_KEY = "kosedge.fantasy.draftDesk.roster.v1";
const TRUE_VALUE_THRESHOLD = 8;

type Props = {
  board: FantasyDeskBoard;
  initialPosition?: string;
  initialScoring?: FantasyScoringProfile;
  initialTab?: "board" | "value" | "builder";
  /** When true, hide the big hero (builder route already has a page title). */
  compactHero?: boolean;
  /** Rankings vs builder route — scoring links stay on this path. */
  basePath?: string;
};

function buildHref(
  basePath: string,
  base: Record<string, string | undefined>,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(base)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `${basePath}?${query}` : basePath;
}

function readStoredRoster(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(ROSTER_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((id): id is string => typeof id === "string");
  } catch {
    return [];
  }
}

function persistRoster(ids: string[]) {
  try {
    sessionStorage.setItem(ROSTER_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // ignore quota / private mode
  }
}

export function FantasyDraftDeskClient({
  board,
  initialPosition = "ALL",
  initialScoring = "half_ppr",
  initialTab = "board",
  compactHero = false,
  basePath = "/pro/nfl/fantasy",
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(
    board.rows[0]?.playerId ?? null,
  );
  const [rosterIds, setRosterIds] = useState<string[]>(readStoredRoster);
  const [tab, setTab] = useState<"board" | "value" | "builder">(initialTab);
  const [query, setQuery] = useState("");
  const [trueValuesOnly, setTrueValuesOnly] = useState(true);
  const [posFilter, setPosFilter] = useState(
    (initialPosition || "ALL").toUpperCase(),
  );

  const selected = board.rows.find((r) => r.playerId === selectedId) ?? null;
  const validIds = useMemo(
    () => new Set(board.rows.map((r) => r.playerId)),
    [board.rows],
  );
  const activeRosterIds = useMemo(
    () => rosterIds.filter((id) => validIds.has(id)),
    [rosterIds, validIds],
  );
  const roster = useMemo(
    () => board.rows.filter((r) => activeRosterIds.includes(r.playerId)),
    [board.rows, activeRosterIds],
  );
  const rosterSet = useMemo(() => new Set(activeRosterIds), [activeRosterIds]);

  const unmatchedCount = useMemo(
    () => board.rows.filter((r) => r.adp == null || r.valueDelta == null).length,
    [board.rows],
  );

  const valueMatched = useMemo(
    () =>
      board.rows.filter((r) => r.adp != null && r.valueDelta != null).length,
    [board.rows],
  );

  const trueValueCount = useMemo(
    () =>
      board.rows.filter(
        (r) =>
          r.valueDelta != null &&
          Math.abs(r.valueDelta) >= TRUE_VALUE_THRESHOLD,
      ).length,
    [board.rows],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pos = posFilter.toUpperCase();
    let rows = board.rows;
    if (pos !== "ALL") {
      rows = rows.filter((r) => r.position.toUpperCase() === pos);
    }
    if (tab === "value") {
      // Real market edge only — drop unmatched ADP so proxy distortion can't leak in.
      rows = [...rows]
        .filter((r) => r.adp != null && r.valueDelta != null)
        .sort((a, b) => (b.valueDelta ?? 0) - (a.valueDelta ?? 0));
      if (trueValuesOnly) {
        rows = rows.filter(
          (r) => Math.abs(r.valueDelta ?? 0) >= TRUE_VALUE_THRESHOLD,
        );
      }
    }
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.playerName.toLowerCase().includes(q) ||
        r.team.toLowerCase().includes(q) ||
        r.position.toLowerCase().includes(q),
    );
  }, [board.rows, query, tab, trueValuesOnly, posFilter]);

  const expertNotes = useMemo(() => {
    const notes = notableValueNotes(board.rows, 3);
    for (const pos of ["RB", "WR", "TE", "QB"] as const) {
      const cliff = tierCliffNote(board.rows, pos);
      if (cliff) notes.push(cliff);
    }
    return notes.slice(0, 5);
  }, [board.rows]);

  const grade = teamGrade(roster, board.rows);
  const needs = rosterNeeds(roster, board.rows);
  const byValue = bestAvailableByValue(board.rows, rosterSet, 5, { roster });
  const byNeed = bestAvailableByNeed(board.rows, roster, 5);

  /** Sync update — Add/Remove must paint immediately. */
  function toggleRoster(playerId: string) {
    setRosterIds((prev) => {
      const next = prev.includes(playerId)
        ? prev.filter((id) => id !== playerId)
        : [...prev, playerId];
      persistRoster(next);
      return next;
    });
  }

  const isEmpty = board.rows.length === 0;
  const isPreseason = board.source === "preseason-fallback";
  const kdFilter = posFilter === "K" || posFilter === "DST";

  const hasKd = board.rows.some((r) =>
    ["K", "DST"].includes(r.position.toUpperCase()),
  );
  // Only offer K/DST filters when the board actually has those positions.
  const positionTabs = hasKd
    ? POSITION_TABS
    : POSITION_TABS.filter((p) => p !== "K" && p !== "DST");
  const kdUnavailable = !hasKd;

  return (
    <div className="fantasy-desk space-y-5">
      {!compactHero ? (
        <section className="relative overflow-hidden rounded-3xl border border-kos-gold/30 bg-[radial-gradient(ellipse_at_top_left,_rgba(212,175,55,0.18),_transparent_55%),linear-gradient(145deg,#0b0d10_0%,#12151c_45%,#0a0c10_100%)] p-6 sm:p-8">
          <div className="pointer-events-none absolute -right-16 top-0 h-56 w-56 rounded-full bg-kos-gold/10 blur-3xl" />
          <div className="relative flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <p className="font-bebas text-5xl leading-none tracking-[0.04em] text-kos-gold sm:text-6xl">
                KOSEDGE
              </p>
              <h1 className="mt-2 font-bebas text-3xl tracking-wide text-kos-text sm:text-4xl">
                Fantasy Draft Desk
              </h1>
              <p className="mt-3 max-w-2xl text-sm text-kos-text/75 sm:text-base">
                Board order is <span className="text-kos-text/90">Model rank</span>
                — projection order, not recommended pick order. ADP and Value Δ
                stay beside it. Builder and Mock use the same projections with
                ADP-aware take / wait / reach advice.
              </p>
              <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-kos-text/45">
                Source · {board.source} · {board.adpSourceLabel}
              </p>
              <p className="mt-1 text-[11px] text-kos-text/40">
                ADP {board.adpFreshnessLabel} · matched {board.adpMatchedCount}/
                {board.count} ({board.adpMatchedHighCount} high for Value Δ
                {board.adpMatchedCrossFormatCount > 0
                  ? ` · ${board.adpMatchedCrossFormatCount} cross-format`
                  : ""}
                )
              </p>
            </div>
            <div className="grid min-w-44 gap-2">
              <Link
                href={`/pro/nfl/fantasy/builder?scoring=${board.scoringProfile}`}
                className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold transition hover:bg-kos-gold/25 active:scale-[0.98]"
              >
                Open Builder
              </Link>
              <Link
                href={`/pro/nfl/fantasy/mock?scoring=${board.scoringProfile}`}
                className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40 active:scale-[0.98]"
              >
                Start Mock
              </Link>
            </div>
          </div>
        </section>
      ) : null}

      {!compactHero ? (
        <FantasyDeskNav
          active={tab === "builder" ? "builder" : "rankings"}
          scoring={board.scoringProfile}
        />
      ) : null}

      {isPreseason ? (
        <HonestStatusBanner title="Preseason fantasy board" tone="sky">
          <p>
            Regular-season draft rankings aren&apos;t posted yet — this desk
            uses the season-engine preseason sim for skill positions (QB / RB /
            WR / TE). Market ADP is still FantasyPros; unmatched names show ADP
            as —. That is camp-season honesty, not an unfinished page. Start
            Mock still works on this board.
          </p>
        </HonestStatusBanner>
      ) : null}

      {kdUnavailable ? (
        <HonestStatusBanner title="K / DST unavailable" tone="amber">
          <p>
            Kickers and defenses are not on this board. Preseason player totals
            are QB / RB / WR / TE only — named K/DST rankings wait until{" "}
            <code className="text-amber-50">nfl_kicker_dst_projections</code>{" "}
            materializes into{" "}
            <code className="text-amber-50">/nfl/fantasy/draft-rankings</code>{" "}
            (and the preseason bundle). Until then mocks skip those roster slots
            and grades do not ding missing K/DST. No invented projections.
          </p>
          {kdFilter ? (
            <p className="mt-2">
              <button
                type="button"
                onClick={() => setPosFilter("ALL")}
                className="font-semibold text-amber-50 underline underline-offset-2"
              >
                Clear {posFilter} filter →
              </button>
            </p>
          ) : null}
        </HonestStatusBanner>
      ) : null}

      {board.adpOrigin === "none" ? (
        <HonestStatusBanner title="Market ADP unavailable" tone="amber">
          <p>
            FantasyPros ADP isn&apos;t loaded — Model vs ADP stays blank until
            the live feed or a saved snapshot returns.
          </p>
        </HonestStatusBanner>
      ) : null}

      {board.error && !isPreseason && board.source !== "empty" ? (
        <HonestStatusBanner title="Desk note" tone="amber">
          <p>{board.error}</p>
        </HonestStatusBanner>
      ) : null}

      {isEmpty && !kdFilter ? (
        <HonestStatusBanner title="No players for this view" tone="neutral">
          <p>
            Nothing matched this scoring / position filter. Clear filters, or
            wait for draft rankings / the preseason sim board to load.
          </p>
          {posFilter !== "ALL" ? (
            <p className="mt-2">
              <button
                type="button"
                onClick={() => setPosFilter("ALL")}
                className="font-semibold text-kos-text underline underline-offset-2"
              >
                Show all positions →
              </button>
            </p>
          ) : null}
        </HonestStatusBanner>
      ) : null}

      {!isEmpty && expertNotes.length > 0 ? (
        <section className="rounded-2xl border border-white/10 bg-black/35 p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
              Fantasy Expert
            </h2>
            <span className="text-[11px] text-kos-text/50">
              Rank vs ADP · yards / role
            </span>
          </div>
          <ul className="mt-3 space-y-2">
            {expertNotes.map((note) => (
              <li
                key={note}
                className="border-l-2 border-kos-gold/40 pl-3 text-sm text-kos-text/80"
              >
                {note}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {!isEmpty ? (
        <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <nav
              className="flex max-w-full gap-2 overflow-x-auto pb-1"
              aria-label="Position filter"
            >
              {positionTabs.map((tabPos) => {
                const active = posFilter === tabPos;
                return (
                  <button
                    key={tabPos}
                    type="button"
                    onClick={() => setPosFilter(tabPos)}
                    className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-semibold transition active:scale-[0.98] ${
                      active
                        ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                        : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25"
                    }`}
                  >
                    {tabPos}
                  </button>
                );
              })}
            </nav>
            <nav className="flex flex-wrap gap-2" aria-label="Scoring format">
              {FANTASY_SCORING_PROFILES.map((profile) => {
                const active = initialScoring === profile.value;
                return (
                  <Link
                    key={profile.value}
                    href={buildHref(basePath, {
                      scoring: profile.value,
                    })}
                    className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                      active
                        ? "border border-edge-green/45 bg-edge-green/15 text-edge-green"
                        : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-edge-green/25"
                    }`}
                  >
                    {profile.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {(
              [
                ["board", "Model rank"],
                ["value", "Value"],
                ["builder", "Builder"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  tab === id
                    ? "border border-white/25 bg-white/15 text-kos-text"
                    : "border border-white/10 bg-white/5 text-kos-text/65 hover:text-kos-text"
                }`}
              >
                {label}
                {id === "builder" && activeRosterIds.length > 0
                  ? ` (${activeRosterIds.length})`
                  : ""}
              </button>
            ))}
            {tab !== "builder" ? (
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search player / team"
                className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-sm text-kos-text placeholder:text-kos-text/40 focus:border-kos-gold/40 focus:outline-none sm:ml-auto sm:max-w-xs"
              />
            ) : null}
          </div>
          {tab !== "builder" ? (
            <div className="mt-3 md:hidden">
              <PlayerCombobox
                players={board.rows}
                rosterSet={rosterSet}
                onToggle={toggleRoster}
                positionFilter={posFilter}
              />
            </div>
          ) : null}
        </section>
      ) : null}

      {!isEmpty && tab === "builder" ? (
        <TeamBuilderPanel
          roster={roster}
          grade={grade}
          needs={needs}
          byValue={byValue}
          byNeed={byNeed}
          rosterSet={rosterSet}
          scoring={board.scoringProfile}
          onSelect={(id) => setSelectedId(id)}
          onToggle={toggleRoster}
          onBrowse={() => setTab("board")}
          boardRows={board.rows}
          posFilter={posFilter}
        />
      ) : null}

      {!isEmpty && tab !== "builder" ? (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <section className="overflow-hidden rounded-2xl border border-white/10 bg-black/30">
            <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-white/10 px-4 py-3">
              <div>
                <h2 className="text-lg font-semibold text-kos-text">
                  {tab === "value" ? "Value Board" : "Model rank"}
                </h2>
                {tab === "value" ? (
                  <p className="mt-0.5 text-[11px] text-kos-text/50">
                    {board.adpSourceLabel} · {board.adpFreshnessLabel} · Value Δ
                    only on high-confidence same-format matches
                  </p>
                ) : (
                  <p className="mt-0.5 text-[11px] text-kos-text/50">
                    Projection order — not recommended pick order
                  </p>
                )}
              </div>
              <p className="text-xs text-kos-text/55">
                {filtered.length} players
              </p>
            </div>

            {tab === "value" ? (
              <div className="flex flex-wrap items-center gap-2 border-b border-white/10 px-4 py-2.5">
                <button
                  type="button"
                  onClick={() => setTrueValuesOnly(true)}
                  className={`min-h-9 rounded-lg border px-3 py-1.5 text-xs font-semibold active:scale-[0.98] ${
                    trueValuesOnly
                      ? "border-edge-green/40 bg-edge-green/15 text-edge-green"
                      : "border-white/10 text-kos-text/60"
                  }`}
                >
                  True values (|Δ| ≥ {TRUE_VALUE_THRESHOLD})
                </button>
                <button
                  type="button"
                  onClick={() => setTrueValuesOnly(false)}
                  className={`min-h-9 rounded-lg border px-3 py-1.5 text-xs font-semibold active:scale-[0.98] ${
                    !trueValuesOnly
                      ? "border-white/25 bg-white/10 text-kos-text"
                      : "border-white/10 text-kos-text/60"
                  }`}
                >
                  All matched
                </button>
                <span className="text-[11px] text-kos-text/45">
                  {trueValueCount} true · {valueMatched} matched ·{" "}
                  {unmatchedCount} unmatched (—)
                </span>
              </div>
            ) : null}

            {filtered.length === 0 ? (
              <div className="p-6 text-center text-sm text-kos-text/60">
                {tab === "value"
                  ? trueValuesOnly
                    ? `No |Δ| ≥ ${TRUE_VALUE_THRESHOLD} plays for this filter — try “All matched” or switch format.`
                    : "No market-ADP values for this filter — unmatched players stay off the value board (ADP —)."
                  : "No players match this search. Clear the query or switch position."}
              </div>
            ) : (
              <>
                {/* Mobile: stacked cards — no horizontal scroll tax */}
                <ul className="divide-y divide-white/10 md:hidden">
                  {filtered.map((row) => {
                    const value = valueLabel(row.valueDelta);
                    const onRoster = rosterSet.has(row.playerId);
                    const muted =
                      tab === "value" &&
                      !trueValuesOnly &&
                      value.kind === "fair";
                    return (
                      <li
                        key={row.playerId}
                        className={`px-4 py-3.5 ${
                          selectedId === row.playerId ? "bg-kos-gold/10" : ""
                        } ${muted ? "opacity-55" : ""}`}
                      >
                        <div className="flex items-start gap-3">
                          <button
                            type="button"
                            onClick={() => setSelectedId(row.playerId)}
                            className="flex min-w-0 flex-1 items-start gap-3 text-left"
                          >
                            <span className="w-8 shrink-0 pt-0.5 text-sm font-semibold text-kos-text">
                              {row.rankOverall}
                            </span>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-sm font-semibold text-kos-text">
                                {row.playerName}
                                {row.isRookie ? (
                                  <span className="ml-1.5 rounded border border-kos-gold/40 px-1 text-[10px] text-kos-gold">
                                    R
                                  </span>
                                ) : null}
                              </p>
                              {row.adpQaFlag ? (
                                <div className="mt-1">
                                  <AdpQaFlagChip flag={row.adpQaFlag} />
                                </div>
                              ) : null}
                              <p className="mt-0.5 text-xs text-kos-text/55">
                                {row.position}
                                {row.rankPosition} · {row.team} · ADP{" "}
                                {formatAdp(row.adp, 0)} · Med{" "}
                                {row.medianPoints.toFixed(0)}
                              </p>
                              <p className="mt-1 text-[11px] text-kos-text/50">
                                {row.floorPoints.toFixed(0)}–
                                {row.ceilingPoints.toFixed(0)} ·{" "}
                                {row.schedule.label}
                              </p>
                            </div>
                          </button>
                          <div className="flex shrink-0 flex-col items-end gap-1.5">
                            <span
                              className={`text-xs font-semibold ${
                                value.kind === "value"
                                  ? "text-edge-green"
                                  : value.kind === "reach"
                                    ? "text-rose-300"
                                    : "text-kos-text/60"
                              }`}
                            >
                              {value.text}
                            </span>
                            <button
                              type="button"
                              onClick={() => toggleRoster(row.playerId)}
                              className={`min-h-9 min-w-[4.5rem] rounded-md border px-2.5 py-1.5 text-[11px] font-semibold active:scale-[0.98] ${
                                onRoster
                                  ? "border-edge-green/40 bg-edge-green/15 text-edge-green"
                                  : "border-white/15 bg-white/5 text-kos-text/70"
                              }`}
                            >
                              {onRoster ? "Rostered" : "Add"}
                            </button>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>

                {/* Desktop / tablet table */}
                <div className="hidden overflow-x-auto md:block">
                  <table className="min-w-[880px] w-full border-separate border-spacing-0">
                    <thead>
                      <tr>
                        {[
                          "Model",
                          "Player",
                          "Pos",
                          "Team",
                          "ADP",
                          "Value",
                          "Floor",
                          "Med",
                          "Ceil",
                          "Schedule",
                          "",
                        ].map((label) => (
                          <th
                            key={label || "act"}
                            className="sticky top-0 border-b border-white/10 bg-[#10131a] px-2.5 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-kos-text/55"
                          >
                            {label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((row, idx) => {
                        const value = valueLabel(row.valueDelta);
                        const onRoster = rosterSet.has(row.playerId);
                        const muted =
                          tab === "value" &&
                          !trueValuesOnly &&
                          value.kind === "fair";
                        return (
                          <tr
                            key={row.playerId}
                            className={`cursor-pointer transition ${
                              selectedId === row.playerId
                                ? "bg-kos-gold/10"
                                : idx % 2
                                  ? "bg-white/[0.02]"
                                  : ""
                            } hover:bg-white/[0.04] ${muted ? "opacity-55" : ""}`}
                            onClick={() => setSelectedId(row.playerId)}
                          >
                            <td className="border-b border-white/5 px-2.5 py-2 text-sm font-semibold text-kos-text">
                              {row.rankOverall}
                            </td>
                            <td className="sticky left-0 border-b border-white/5 bg-[#0c0f14]/px-2.5 py-2 text-sm font-semibold text-kos-text">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span>{row.playerName}</span>
                                {row.isRookie ? (
                                  <span className="rounded border border-kos-gold/40 px-1 text-[10px] text-kos-gold">
                                    R
                                  </span>
                                ) : null}
                                <AdpQaFlagChip flag={row.adpQaFlag} />
                              </div>
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2">
                              <span
                                className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold ${draftPositionBadgeClass(row.position)}`}
                              >
                                {row.position}
                                {row.rankPosition}
                              </span>
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2 text-sm text-kos-text/80">
                              {row.team}
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2 text-sm text-kos-text/80">
                              {formatAdp(row.adp)}
                            </td>
                            <td
                              className={`border-b border-white/5 px-2.5 py-2 text-sm font-semibold ${
                                value.kind === "value"
                                  ? "text-edge-green"
                                  : value.kind === "reach"
                                    ? "text-rose-300"
                                    : "text-kos-text/70"
                              }`}
                            >
                              {value.text}
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2 text-sm text-kos-text/75">
                              {row.floorPoints.toFixed(0)}
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2 text-sm text-kos-gold">
                              {row.medianPoints.toFixed(0)}
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2 text-sm text-kos-text/75">
                              {row.ceilingPoints.toFixed(0)}
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2 text-[11px] text-kos-text/65">
                              {row.schedule.label}
                            </td>
                            <td className="border-b border-white/5 px-2.5 py-2">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleRoster(row.playerId);
                                }}
                                className={`rounded-md border px-2 py-1 text-[11px] font-semibold transition ${
                                  onRoster
                                    ? "border-edge-green/40 bg-edge-green/15 text-edge-green"
                                    : "border-white/15 bg-white/5 text-kos-text/70 hover:border-kos-gold/40"
                                }`}
                              >
                                {onRoster ? "Rostered" : "Add"}
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>

          <div className="lg:sticky lg:top-24 lg:self-start">
            <div className="mb-4 hidden md:block">
              <PlayerCombobox
                players={board.rows}
                rosterSet={rosterSet}
                onToggle={toggleRoster}
                positionFilter={posFilter}
              />
            </div>
            <PlayerCard
              row={selected}
              onRoster={selected ? rosterSet.has(selected.playerId) : false}
              onToggle={toggleRoster}
            />
          </div>
        </div>
      ) : null}

      <details className="rounded-2xl border border-white/10 bg-black/25 px-3 py-2 sm:p-4 text-[11px] leading-relaxed text-kos-text/55 sm:text-xs">
        <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 font-semibold uppercase tracking-[0.12em] text-kos-text/40 marker:content-none [&::-webkit-details-marker]:hidden">
          <span>Methods</span>
          <span className="font-normal normal-case tracking-normal text-kos-text/35">
            Model rank vs draft advice
          </span>
        </summary>
        <ul className="mt-2 list-disc space-y-1.5 pl-4 pb-1 sm:mt-3">
          {board.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
    </div>
  );
}

function PlayerCard({
  row,
  onRoster,
  onToggle,
}: {
  row: FantasyDeskRow | null;
  onRoster: boolean;
  onToggle: (id: string) => void;
}) {
  if (!row) {
    return (
      <aside className="rounded-2xl border border-dashed border-white/15 bg-black/30 p-5 text-sm text-kos-text/60">
        Tap a player to open the card — projections, value vs ADP, and the
        Fantasy Expert note.
      </aside>
    );
  }

  return (
    <aside className="fantasy-player-card rounded-2xl border border-kos-gold/25 bg-linear-to-b from-kos-gold/10 via-black/50 to-black/80 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.14em] text-kos-gold">
            Player card
          </p>
          <h3 className="mt-1 truncate text-xl font-semibold text-kos-text">
            {row.playerName}
          </h3>
          <p className="text-sm text-kos-text/65">
            {row.team} · {row.position}
            {row.rankPosition} · {draftTierLabel(row.tier)}
          </p>
          {row.adpQaFlag ? (
            <div className="mt-2">
              <AdpQaFlagChip flag={row.adpQaFlag} />
            </div>
          ) : null}
        </div>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${draftTierBadgeClass(row.tier)}`}
        >
          #{row.rankOverall}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <Metric label="Floor" value={row.floorPoints.toFixed(0)} />
        <Metric label="Median" value={row.medianPoints.toFixed(0)} accent />
        <Metric label="Ceiling" value={row.ceilingPoints.toFixed(0)} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-xl border border-white/10 bg-black/30 p-3">
          <p className="text-[10px] uppercase text-kos-text/45">Model / ADP</p>
          <p className="mt-1 font-semibold text-kos-text">
            #{row.rankOverall} / {formatAdp(row.adp)}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/30 p-3">
          <p className="text-[10px] uppercase text-kos-text/45">Value Δ</p>
          <p
            className={`mt-1 font-semibold ${
              (row.valueDelta ?? 0) >= 8
                ? "text-edge-green"
                : (row.valueDelta ?? 0) <= -8
                  ? "text-rose-300"
                  : "text-kos-text"
            }`}
          >
            {row.valueDelta == null
              ? "—"
              : `${row.valueDelta >= 0 ? "+" : ""}${row.valueDelta.toFixed(1)}`}
          </p>
        </div>
      </div>

      {row.adpQaFlag ? (
        <div className="mt-4 rounded-xl border border-kos-gold/25 bg-kos-gold/8 p-3">
          <p className="text-[10px] uppercase tracking-[0.12em] text-kos-gold">
            {row.adpQaFlag.categoryLabel} · why this gap
          </p>
          <ul className="mt-2 space-y-1.5">
            {row.adpQaFlag.drivers.map((d) => (
              <li key={d} className="text-sm text-kos-text/80">
                · {d}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-4">
        <p className="text-[10px] uppercase tracking-[0.12em] text-kos-text/45">
          Why the model ranks them here
        </p>
        <ul className="mt-2 space-y-1.5">
          {row.drivers.map((d) => (
            <li key={d} className="text-sm text-kos-text/80">
              · {d}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-black/25 p-3">
        <p className="text-[10px] uppercase tracking-[0.12em] text-kos-gold">
          Fantasy Expert
        </p>
        <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
          {row.expertBlurb}
        </p>
      </div>

      <div className="mt-4">
        <p className="text-[10px] uppercase tracking-[0.12em] text-kos-text/45">
          Schedule · risk
        </p>
        <p className="mt-1 text-sm text-kos-text/75">{row.schedule.label}</p>
        <p className="text-xs text-kos-text/50">{row.schedule.detail}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {row.riskFlags.length === 0 ? (
            <span className="rounded border border-white/10 px-2 py-0.5 text-[11px] text-kos-text/50">
              No major flags
            </span>
          ) : (
            row.riskFlags.map((flag) => (
              <span
                key={flag.kind + flag.label}
                title={flag.detail}
                className="rounded border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[11px] text-amber-100"
              >
                {flag.label}
              </span>
            ))
          )}
        </div>
      </div>

      <div className="mt-5 flex gap-2">
        <button
          type="button"
          onClick={() => onToggle(row.playerId)}
          className={`flex-1 rounded-xl border px-3 py-2 text-sm font-semibold transition active:scale-[0.98] ${
            onRoster
              ? "border-edge-green/40 bg-edge-green/15 text-edge-green"
              : "border-kos-gold/40 bg-kos-gold/15 text-kos-gold hover:bg-kos-gold/25"
          }`}
        >
          {onRoster ? "Remove" : "Add to roster"}
        </button>
        <Link
          href={`/pro/nfl/fantasy/player/${encodeURIComponent(row.playerId)}?scoring=${row.scoringProfile}`}
          className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
        >
          Full card
        </Link>
      </div>
    </aside>
  );
}

function TeamBuilderPanel({
  roster,
  grade,
  needs,
  byValue,
  byNeed,
  rosterSet,
  scoring,
  onSelect,
  onToggle,
  onBrowse,
  boardRows,
  posFilter,
}: {
  roster: FantasyDeskRow[];
  grade: ReturnType<typeof teamGrade>;
  needs: Record<string, number>;
  byValue: ValueAwareSuggestion[];
  byNeed: ValueAwareSuggestion[];
  rosterSet: Set<string>;
  scoring: FantasyScoringProfile;
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
  onBrowse: () => void;
  boardRows: FantasyDeskRow[];
  posFilter: string;
}) {
  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-kos-text">Your roster</h2>
            <p className="text-sm text-kos-text/60">
              Private scratchpad — suggestions below are ADP-aware. Rankings
              stay raw Model rank. Next step is Mock.
            </p>
          </div>
          <div className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-3 py-2 text-center">
            <p className="text-[10px] uppercase text-kos-gold/80">Grade</p>
            <p className="font-bebas text-3xl text-kos-gold">{grade.grade}</p>
          </div>
        </div>
        <p className="mt-2 text-sm text-kos-text/70">{grade.detail}</p>
        <div className="mt-4">
          <PlayerCombobox
            players={boardRows}
            rosterSet={rosterSet}
            onToggle={onToggle}
            positionFilter={posFilter}
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onBrowse}
            className="min-h-10 rounded-xl border border-white/15 px-3 py-2 text-xs font-semibold text-kos-text/70 active:scale-[0.98]"
          >
            ← Rankings
          </button>
          <Link
            href={`/pro/nfl/fantasy/mock?scoring=${scoring}`}
            className="min-h-10 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-3 py-2 text-xs font-semibold text-kos-gold active:scale-[0.98]"
          >
            Start Mock →
          </Link>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {Object.entries(needs).map(([pos, n]) =>
            n > 0 ? (
              <span
                key={pos}
                className="rounded border border-rose-400/30 bg-rose-400/10 px-2 py-0.5 text-[11px] text-rose-200"
              >
                Need {pos} ×{n}
              </span>
            ) : null,
          )}
        </div>
        <ul className="mt-4 space-y-2">
          {roster.length === 0 ? (
            <li className="rounded-xl border border-dashed border-white/15 p-4 text-sm text-kos-text/55">
              <p>Empty roster — search the drop box above, then Add to builder.</p>
            </li>
          ) : (
            roster.map((row) => (
              <li
                key={row.playerId}
                className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2"
              >
                <button
                  type="button"
                  className="min-w-0 text-left"
                  onClick={() => onSelect(row.playerId)}
                >
                  <p className="truncate text-sm font-semibold text-kos-text">
                    {row.playerName}
                  </p>
                  <p className="text-xs text-kos-text/55">
                    {row.position} · {row.team} · {row.medianPoints.toFixed(0)}{" "}
                    pts
                  </p>
                </button>
                <button
                  type="button"
                  onClick={() => onToggle(row.playerId)}
                  className="shrink-0 rounded-md border border-rose-400/35 px-2 py-1 text-xs font-semibold text-rose-300 active:scale-[0.98]"
                >
                  Remove
                </button>
              </li>
            ))
          )}
        </ul>
      </div>

      <div className="space-y-5">
        <SuggestBlock
          title="ADP-aware value"
          suggestions={byValue}
          rosterSet={rosterSet}
          onSelect={onSelect}
          onToggle={onToggle}
        />
        <SuggestBlock
          title="ADP-aware need"
          suggestions={byNeed}
          rosterSet={rosterSet}
          onSelect={onSelect}
          onToggle={onToggle}
        />
      </div>
    </section>
  );
}

function SuggestBlock({
  title,
  suggestions,
  rosterSet,
  onSelect,
  onToggle,
}: {
  title: string;
  suggestions: ValueAwareSuggestion[];
  rosterSet: Set<string>;
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
        {title}
      </h3>
      {suggestions.length === 0 ? (
        <p className="mt-3 text-sm text-kos-text/50">
          No suggestions — board is empty or fully rostered.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {suggestions.map(({ row, timingHint, timing }) => {
            const onRoster = rosterSet.has(row.playerId);
            return (
              <li
                key={row.playerId}
                className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2"
              >
                <button
                  type="button"
                  className="min-w-0 text-left"
                  onClick={() => onSelect(row.playerId)}
                >
                  <p className="truncate text-sm font-semibold text-kos-text">
                    {row.playerName}
                  </p>
                  <p className="text-xs text-kos-text/55">
                    #{row.rankOverall} · ADP {formatAdp(row.adp, 0)} ·{" "}
                    {valueLabel(row.valueDelta).text}
                  </p>
                  {timingHint ? (
                    <p className={`mt-0.5 text-[11px] ${draftAdviceClass(timing)}`}>
                      {timingHint}
                    </p>
                  ) : null}
                </button>
                <button
                  type="button"
                  onClick={() => onToggle(row.playerId)}
                  className={`shrink-0 rounded-md border px-2 py-1 text-[11px] font-semibold active:scale-[0.98] ${
                    onRoster
                      ? "border-edge-green/40 bg-edge-green/15 text-edge-green"
                      : "border-kos-gold/35 text-kos-gold"
                  }`}
                >
                  {onRoster ? "Added" : "Add"}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-2 ${
        accent
          ? "border-kos-gold/35 bg-kos-gold/10"
          : "border-white/10 bg-black/30"
      }`}
    >
      <p className="text-[10px] uppercase text-kos-text/45">{label}</p>
      <p
        className={`mt-0.5 text-lg font-semibold ${accent ? "text-kos-gold" : "text-kos-text"}`}
      >
        {value}
      </p>
    </div>
  );
}
