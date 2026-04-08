"use client";

import { useMemo, useState } from "react";
import {
  formatDateKeyET,
  formatGameDateET,
  formatGameTimeET,
  getDateKeyET,
  todayET,
} from "@/lib/date-format";

type Game = {
  id?: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime?: string;
  projSpreadHome: number | null;
  projTotal: number | null;
};

export function NcaamKeiLinesClient({
  games,
  sportName,
}: {
  games: Game[];
  sportName: string;
}) {
  const today = todayET();

  const dateOptions = useMemo(() => {
    const keys = new Set<string>();
    for (const g of games) {
      if (g.commenceTime) keys.add(getDateKeyET(g.commenceTime));
    }
    const sorted = [...keys].sort().reverse();
    return sorted.slice(0, 60).map((value) => ({
      value,
      label: formatDateKeyET(value),
    }));
  }, [games]);

  const [selectedDate, setSelectedDate] = useState(() => {
    const keys = new Set<string>();
    for (const g of games) {
      if (g.commenceTime) keys.add(getDateKeyET(g.commenceTime));
    }
    const sorted = [...keys].sort().reverse();
    return sorted.includes(today) ? today : (sorted[0] ?? today);
  });

  const filtered = useMemo(() => {
    return games
      .filter(
        (g) => g.commenceTime && getDateKeyET(g.commenceTime) === selectedDate,
      )
      .sort((a, b) => {
        const t1 = a.commenceTime ? new Date(a.commenceTime).getTime() : 0;
        const t2 = b.commenceTime ? new Date(b.commenceTime).getTime() : 0;
        return t1 - t2;
      });
  }, [games, selectedDate]);

  if (games.length === 0) {
    return (
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-8 text-center">
        <p className="text-kos-text/60">
          No KEI lines for {sportName} yet. Run the pipeline export to generate{" "}
          <code className="text-kos-gold/80">
            data/processed/kei_lines_*.json
          </code>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <label
          htmlFor="ncaam-date"
          className="text-sm font-medium text-kos-text/80"
        >
          Game date
        </label>
        <select
          id="ncaam-date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="rounded-xl border border-kos-border bg-kos-surface/50 px-4 py-2.5 text-kos-text focus:border-kos-gold/50 focus:outline-none focus:ring-2 focus:ring-kos-gold/30"
        >
          {dateOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.value === today ? `${opt.label} (Today)` : opt.label}
            </option>
          ))}
        </select>
        <span className="text-sm text-kos-text/60">
          {filtered.length} game{filtered.length !== 1 ? "s" : ""} on this date
        </span>
      </div>

      <div className="overflow-hidden rounded-2xl border border-kos-border bg-kos-surface/30">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-kos-border bg-kos-surface/50">
              <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
                Date
              </th>
              <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
                Time
              </th>
              <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
                Away
              </th>
              <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
                Home
              </th>
              <th className="px-4 py-3 text-sm font-semibold text-kos-gold">
                Proj line (H)
              </th>
              <th className="px-4 py-3 text-sm font-semibold text-kos-gold">
                Proj O/U
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-kos-text/60"
                >
                  No games on this date.
                </td>
              </tr>
            ) : (
              filtered.map((g, i) => (
                <tr
                  key={g.id ?? i}
                  className="border-b border-kos-border/50 hover:bg-kos-surface/40"
                >
                  <td className="px-4 py-3 text-sm text-kos-text/80">
                    {g.commenceTime ? formatGameDateET(g.commenceTime) : "—"}
                  </td>
                  <td className="px-4 py-3 text-sm text-kos-text/80 tabular-nums">
                    {g.commenceTime ? formatGameTimeET(g.commenceTime) : "—"}
                  </td>
                  <td className="px-4 py-3 font-medium text-kos-text">
                    {g.awayTeam}
                  </td>
                  <td className="px-4 py-3 font-medium text-kos-text">
                    {g.homeTeam}
                  </td>
                  <td className="px-4 py-3 text-kos-gold">
                    {g.projSpreadHome != null
                      ? g.projSpreadHome > 0
                        ? `+${g.projSpreadHome.toFixed(1)}`
                        : g.projSpreadHome.toFixed(1)
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-kos-gold">
                    {g.projTotal != null ? g.projTotal.toFixed(1) : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
