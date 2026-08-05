"use client";

import Link from "next/link";
import { useMemo, useState, useTransition } from "react";
import { valueLabel } from "@/lib/fantasy/adp-proxy";
import {
  notableValueNotes,
  tierCliffNote,
} from "@/lib/fantasy/expert";
import {
  bestAvailableByNeed,
  bestAvailableByValue,
  rosterNeeds,
  teamGrade,
} from "@/lib/fantasy/team-builder";
import type { FantasyDeskBoard, FantasyDeskRow } from "@/lib/fantasy/types";
import {
  draftPositionBadgeClass,
  draftTierBadgeClass,
  draftTierLabel,
  FANTASY_DRAFT_POSITIONS,
  FANTASY_SCORING_PROFILES,
  type FantasyScoringProfile,
} from "@/lib/nfl-fantasy-draft";

const POSITION_TABS = ["ALL", ...FANTASY_DRAFT_POSITIONS] as const;

type Props = {
  board: FantasyDeskBoard;
  initialPosition?: string;
  initialScoring?: FantasyScoringProfile;
  initialTab?: "board" | "value" | "builder";
};

function buildHref(base: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(base)) {
    if (value) params.set(key, value);
  }
  const query = params.toString();
  return query ? `/pro/nfl/fantasy?${query}` : "/pro/nfl/fantasy";
}

export function FantasyDraftDeskClient({
  board,
  initialPosition = "ALL",
  initialScoring = "half_ppr",
  initialTab = "board",
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(
    board.rows[0]?.playerId ?? null,
  );
  const [rosterIds, setRosterIds] = useState<string[]>([]);
  const [tab, setTab] = useState<"board" | "value" | "builder">(initialTab);
  const [query, setQuery] = useState("");
  const [, startTransition] = useTransition();

  const selected = board.rows.find((r) => r.playerId === selectedId) ?? null;
  const roster = useMemo(
    () => board.rows.filter((r) => rosterIds.includes(r.playerId)),
    [board.rows, rosterIds],
  );
  const rosterSet = useMemo(() => new Set(rosterIds), [rosterIds]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let rows = board.rows;
    if (tab === "value") {
      rows = [...rows].sort((a, b) => b.valueDelta - a.valueDelta);
    }
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.playerName.toLowerCase().includes(q) ||
        r.team.toLowerCase().includes(q) ||
        r.position.toLowerCase().includes(q),
    );
  }, [board.rows, query, tab]);

  const expertNotes = useMemo(() => {
    const notes = notableValueNotes(board.rows, 3);
    for (const pos of ["RB", "WR", "TE", "QB"] as const) {
      const cliff = tierCliffNote(board.rows, pos);
      if (cliff) notes.push(cliff);
    }
    return notes.slice(0, 5);
  }, [board.rows]);

  const grade = teamGrade(roster);
  const needs = rosterNeeds(roster);
  const byValue = bestAvailableByValue(board.rows, rosterSet, 5);
  const byNeed = bestAvailableByNeed(board.rows, roster, 5);

  function toggleRoster(playerId: string) {
    startTransition(() => {
      setRosterIds((prev) =>
        prev.includes(playerId)
          ? prev.filter((id) => id !== playerId)
          : [...prev, playerId],
      );
    });
  }

  return (
    <div className="fantasy-desk space-y-5">
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
              Model-backed {board.season} rankings from the season engine —
              value vs ADP, floor/median/ceiling, schedule context, and a
              manual team builder. Not a consensus copy board.
            </p>
            <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-kos-text/45">
              Source · {board.source} · {board.adpSourceLabel}
            </p>
          </div>
          <div className="grid min-w-44 gap-2">
            <Link
              href="/pro/nfl/fantasy/builder"
              className="rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-center text-sm font-semibold text-kos-gold transition hover:bg-kos-gold/25"
            >
              Open Team Builder
            </Link>
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              NFL Overview
            </Link>
          </div>
        </div>
      </section>

      {board.error ? (
        <section className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
          {board.error}
        </section>
      ) : null}

      {expertNotes.length > 0 ? (
        <section className="rounded-2xl border border-white/10 bg-black/35 p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
              Fantasy Expert
            </h2>
            <span className="text-[11px] text-kos-text/50">
              Sharp notes · model vs ADP
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

      <section className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav className="flex flex-wrap gap-2" aria-label="Position filter">
            {POSITION_TABS.map((tabPos) => {
              const active = (initialPosition || "ALL") === tabPos;
              return (
                <Link
                  key={tabPos}
                  href={buildHref({
                    scoring: initialScoring,
                    position: tabPos === "ALL" ? undefined : tabPos,
                  })}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                    active
                      ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                      : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25"
                  }`}
                >
                  {tabPos}
                </Link>
              );
            })}
          </nav>
          <nav className="flex flex-wrap gap-2" aria-label="Scoring format">
            {FANTASY_SCORING_PROFILES.map((profile) => {
              const active = initialScoring === profile.value;
              return (
                <Link
                  key={profile.value}
                  href={buildHref({
                    scoring: profile.value,
                    position:
                      initialPosition === "ALL" ? undefined : initialPosition,
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
              ["board", "Rankings"],
              ["value", "Value board"],
              ["builder", "Team builder"],
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
            </button>
          ))}
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search player / team"
            className="ml-auto min-w-44 flex-1 rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 text-sm text-kos-text placeholder:text-kos-text/40 focus:border-kos-gold/40 focus:outline-none sm:max-w-xs"
          />
        </div>
      </section>

      {tab === "builder" ? (
        <TeamBuilderPanel
          roster={roster}
          grade={grade}
          needs={needs}
          byValue={byValue}
          byNeed={byNeed}
          onSelect={setSelectedId}
          onToggle={toggleRoster}
        />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <section className="overflow-hidden rounded-2xl border border-white/10 bg-black/30">
            <div className="flex items-baseline justify-between gap-3 border-b border-white/10 px-4 py-3">
              <h2 className="text-lg font-semibold text-kos-text">
                {tab === "value" ? "Value Board" : "Draft Rankings"}
              </h2>
              <p className="text-xs text-kos-text/55">
                {filtered.length} players
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-[920px] w-full border-separate border-spacing-0">
                <thead>
                  <tr>
                    {[
                      "Rk",
                      "Player",
                      "Pos",
                      "Team",
                      "Model",
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
                    return (
                      <tr
                        key={row.playerId}
                        className={`cursor-pointer transition ${
                          selectedId === row.playerId
                            ? "bg-kos-gold/10"
                            : idx % 2
                              ? "bg-white/[0.02]"
                              : ""
                        } hover:bg-white/[0.04]`}
                        onClick={() => setSelectedId(row.playerId)}
                      >
                        <td className="border-b border-white/5 px-2.5 py-2 text-sm font-semibold text-kos-text">
                          {row.rankOverall}
                        </td>
                        <td className="border-b border-white/5 px-2.5 py-2 text-sm font-semibold text-kos-text">
                          {row.playerName}
                          {row.isRookie ? (
                            <span className="ml-1.5 rounded border border-kos-gold/40 px-1 text-[10px] text-kos-gold">
                              R
                            </span>
                          ) : null}
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
                          #{row.rankOverall}
                        </td>
                        <td className="border-b border-white/5 px-2.5 py-2 text-sm text-kos-text/80">
                          {row.adp.toFixed(1)}
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
          </section>

          <PlayerCard
            row={selected}
            onRoster={selected ? rosterSet.has(selected.playerId) : false}
            onToggle={toggleRoster}
          />
        </div>
      )}

      <section className="rounded-2xl border border-white/10 bg-black/25 p-4 text-xs text-kos-text/55">
        <p className="font-semibold uppercase tracking-[0.12em] text-kos-text/40">
          Methods & limitations
        </p>
        <ul className="mt-2 list-disc space-y-1 pl-4">
          {board.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
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
      <aside className="rounded-2xl border border-white/10 bg-black/30 p-5 text-sm text-kos-text/60">
        Select a player to open the card.
      </aside>
    );
  }

  return (
    <aside className="fantasy-player-card rounded-2xl border border-kos-gold/25 bg-linear-to-b from-kos-gold/10 via-black/50 to-black/80 p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-kos-gold">
            Player card
          </p>
          <h3 className="mt-1 text-xl font-semibold text-kos-text">
            {row.playerName}
          </h3>
          <p className="text-sm text-kos-text/65">
            {row.team} · {row.position}
            {row.rankPosition} · {draftTierLabel(row.tier)}
          </p>
        </div>
        <span
          className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${draftTierBadgeClass(row.tier)}`}
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
            #{row.rankOverall} / {row.adp.toFixed(1)}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/30 p-3">
          <p className="text-[10px] uppercase text-kos-text/45">Value Δ</p>
          <p
            className={`mt-1 font-semibold ${
              row.valueDelta >= 8
                ? "text-edge-green"
                : row.valueDelta <= -8
                  ? "text-rose-300"
                  : "text-kos-text"
            }`}
          >
            {row.valueDelta >= 0 ? "+" : ""}
            {row.valueDelta.toFixed(1)}
          </p>
        </div>
      </div>

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
          className={`flex-1 rounded-xl border px-3 py-2 text-sm font-semibold transition ${
            onRoster
              ? "border-edge-green/40 bg-edge-green/15 text-edge-green"
              : "border-kos-gold/40 bg-kos-gold/15 text-kos-gold hover:bg-kos-gold/25"
          }`}
        >
          {onRoster ? "Remove from roster" : "Add to roster"}
        </button>
        <Link
          href={`/pro/nfl/fantasy/player/${encodeURIComponent(row.playerId)}?scoring=${row.scoringProfile}`}
          className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
        >
          Detail
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
  onSelect,
  onToggle,
}: {
  roster: FantasyDeskRow[];
  grade: ReturnType<typeof teamGrade>;
  needs: Record<string, number>;
  byValue: FantasyDeskRow[];
  byNeed: FantasyDeskRow[];
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  return (
    <section className="grid gap-5 lg:grid-cols-2">
      <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-kos-text">Your roster</h2>
            <p className="text-sm text-kos-text/60">
              Manual builder · no CPU mock yet
            </p>
          </div>
          <div className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-3 py-2 text-center">
            <p className="text-[10px] uppercase text-kos-gold/80">Grade</p>
            <p className="font-bebas text-3xl text-kos-gold">{grade.grade}</p>
          </div>
        </div>
        <p className="mt-2 text-sm text-kos-text/70">{grade.detail}</p>
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
              Add players from the rankings board to start building.
            </li>
          ) : (
            roster.map((row) => (
              <li
                key={row.playerId}
                className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2"
              >
                <button
                  type="button"
                  className="text-left"
                  onClick={() => onSelect(row.playerId)}
                >
                  <p className="text-sm font-semibold text-kos-text">
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
                  className="text-xs font-semibold text-rose-300"
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
          title="Best available by value"
          rows={byValue}
          onSelect={onSelect}
          onToggle={onToggle}
        />
        <SuggestBlock
          title="Best available by need"
          rows={byNeed}
          onSelect={onSelect}
          onToggle={onToggle}
        />
      </div>
    </section>
  );
}

function SuggestBlock({
  title,
  rows,
  onSelect,
  onToggle,
}: {
  title: string;
  rows: FantasyDeskRow[];
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
      <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-text/55">
        {title}
      </h3>
      <ul className="mt-3 space-y-2">
        {rows.map((row) => (
          <li
            key={row.playerId}
            className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2"
          >
            <button
              type="button"
              className="text-left"
              onClick={() => onSelect(row.playerId)}
            >
              <p className="text-sm font-semibold text-kos-text">
                {row.playerName}
              </p>
              <p className="text-xs text-kos-text/55">
                #{row.rankOverall} · ADP {row.adp.toFixed(0)} ·{" "}
                {valueLabel(row.valueDelta).text}
              </p>
            </button>
            <button
              type="button"
              onClick={() => onToggle(row.playerId)}
              className="rounded-md border border-kos-gold/35 px-2 py-1 text-[11px] font-semibold text-kos-gold"
            >
              Add
            </button>
          </li>
        ))}
      </ul>
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
