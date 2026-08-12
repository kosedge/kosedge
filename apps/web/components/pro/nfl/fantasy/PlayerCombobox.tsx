"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { formatAdp } from "@/lib/fantasy/adp-proxy";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

type Props = {
  players: FantasyDeskRow[];
  rosterSet: Set<string>;
  onToggle: (playerId: string) => void;
  positionFilter?: string;
};

const LIST_LIMIT = 40;

export function PlayerCombobox({
  players,
  rosterSet,
  onToggle,
  positionFilter = "ALL",
}: Props) {
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pos = positionFilter.toUpperCase();
    return players
      .filter((row) => {
        if (pos !== "ALL" && row.position.toUpperCase() !== pos) return false;
        if (!q) return true;
        return (
          row.playerName.toLowerCase().includes(q) ||
          row.team.toLowerCase().includes(q) ||
          row.position.toLowerCase().includes(q)
        );
      })
      .slice(0, LIST_LIMIT);
  }, [players, query, positionFilter]);

  useEffect(() => {
    setHighlight(0);
  }, [query, positionFilter]);

  const selected = matches[highlight] ?? null;

  function addHighlighted() {
    if (!selected) return;
    if (!rosterSet.has(selected.playerId)) onToggle(selected.playerId);
    setQuery("");
    setOpen(false);
    inputRef.current?.focus();
  }

  return (
    <div className="relative z-20">
      <label className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.12em] text-kos-text/55">
        Add player
      </label>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listId}
          aria-activedescendant={
            open && selected ? `${listId}-${selected.playerId}` : undefined
          }
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            window.setTimeout(() => setOpen(false), 120);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setHighlight((h) => Math.min(matches.length - 1, h + 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setHighlight((h) => Math.max(0, h - 1));
            } else if (e.key === "Enter") {
              e.preventDefault();
              addHighlighted();
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder="Search name / team"
          className="min-h-11 min-w-0 flex-1 rounded-lg border border-white/15 bg-black/40 px-3 py-2 text-sm text-kos-text placeholder:text-kos-text/40 outline-none focus:border-kos-gold/50"
        />
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={addHighlighted}
          disabled={!selected || rosterSet.has(selected.playerId)}
          className="min-h-11 shrink-0 rounded-lg border border-kos-gold/40 bg-kos-gold/15 px-3 text-sm font-semibold text-kos-gold disabled:cursor-not-allowed disabled:opacity-40 active:scale-[0.98]"
        >
          Add to builder
        </button>
      </div>
      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute left-0 right-0 top-full z-40 mt-1 max-h-64 overflow-y-auto rounded-xl border border-white/15 bg-[#10131a] shadow-xl shadow-black/50"
        >
          {matches.length === 0 ? (
            <li className="px-3 py-3 text-sm text-kos-text/55">
              No players match this search.
            </li>
          ) : (
            matches.map((row, idx) => {
              const onRoster = rosterSet.has(row.playerId);
              return (
                <li
                  key={row.playerId}
                  id={`${listId}-${row.playerId}`}
                  role="option"
                  aria-selected={idx === highlight}
                  className={`flex cursor-pointer items-center justify-between gap-2 px-3 py-2.5 text-sm ${
                    idx === highlight ? "bg-kos-gold/15" : ""
                  }`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setHighlight(idx);
                    if (!onRoster) onToggle(row.playerId);
                    setQuery("");
                    setOpen(false);
                  }}
                  onMouseEnter={() => setHighlight(idx)}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-semibold text-kos-text">
                      {row.playerName}
                    </span>
                    <span className="text-[11px] text-kos-text/50">
                      {row.position}
                      {row.rankPosition} · {row.team} · #{row.rankOverall} · ADP{" "}
                      {formatAdp(row.adp, 0)}
                    </span>
                  </span>
                  <span
                    className={`shrink-0 text-[11px] font-semibold ${
                      onRoster ? "text-edge-green" : "text-kos-gold"
                    }`}
                  >
                    {onRoster ? "Rostered" : "Add"}
                  </span>
                </li>
              );
            })
          )}
        </ul>
      ) : null}
    </div>
  );
}
