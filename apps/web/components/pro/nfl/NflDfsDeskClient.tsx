"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  InstantFilterBar,
  InstantSelect,
  useInstantFilters,
} from "@/components/pro/InstantFilterBar";
import {
  formatDfsNumber,
  formatSalary,
  type NflDfsBoardRow,
} from "@/lib/nfl-dfs-types";

type SortKey =
  | "playerName"
  | "position"
  | "salary"
  | "projection"
  | "floor"
  | "ceiling"
  | "value";

const WEEK_OPTIONS = Array.from({ length: 18 }, (_, i) => ({
  value: String(i + 1),
  label: `Week ${i + 1}`,
}));

const POS_OPTIONS = [
  { value: "", label: "All skill" },
  { value: "QB", label: "QB" },
  { value: "RB", label: "RB" },
  { value: "WR", label: "WR" },
  { value: "TE", label: "TE" },
];

export function NflDfsDeskControls({
  season,
  week,
  site,
  position,
  slates,
  slateId,
}: {
  season: number;
  week: number;
  site: string;
  position: string;
  slates: Array<{ slateId: string }>;
  slateId: string;
}) {
  const { setParam, setParams, pending } = useInstantFilters();
  const slateOptions =
    slates.length > 0
      ? slates.map((s) => ({ value: s.slateId, label: s.slateId }))
      : [{ value: slateId, label: slateId || "No slate" }];

  return (
    <InstantFilterBar>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <InstantSelect
          name="week"
          label="Week / Slate"
          value={String(week)}
          options={WEEK_OPTIONS}
          pending={pending}
          onChange={(value) => setParams({ week: value, slate: null })}
        />
        <InstantSelect
          name="slate"
          label="Slate"
          value={slateId}
          options={slateOptions}
          pending={pending}
          onChange={(value) => setParam("slate", value || null)}
        />
        <InstantSelect
          name="site"
          label="Site"
          value={site}
          options={[
            { value: "DK", label: "DraftKings" },
            { value: "FD", label: "FanDuel" },
          ]}
          pending={pending}
          onChange={(value) => setParam("site", value)}
        />
        <InstantSelect
          name="pos"
          label="Position"
          value={position}
          options={POS_OPTIONS}
          pending={pending}
          onChange={(value) => setParam("pos", value || null)}
        />
      </div>
      <p className="mt-3 text-[11px] text-kos-text/45">
        Season {season}. Site is a salary/scoring identity — DK and FD are
        separate boards. K/DST omitted.
      </p>
    </InstantFilterBar>
  );
}

export function NflDfsBoardTable({ rows }: { rows: NflDfsBoardRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("projection");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      const an = Number(av);
      const bn = Number(bv);
      return sortDir === "asc" ? an - bn : bn - an;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  function toggle(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(key);
    setSortDir(key === "playerName" || key === "position" ? "asc" : "desc");
  }

  if (rows.length === 0) {
    return (
      <p className="px-4 py-8 text-sm text-kos-text/60">
        No certified DFS rows for this site/slate. Failed joins are omitted —
        they do not get a value.
      </p>
    );
  }

  return (
    <table className="min-w-full text-left text-sm">
      <thead>
        <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/60">
          <SortTh
            label="Player"
            active={sortKey === "playerName"}
            onClick={() => toggle("playerName")}
          />
          <SortTh
            label="Pos"
            active={sortKey === "position"}
            onClick={() => toggle("position")}
          />
          <th className="px-3 py-3">Team/Opp</th>
          <SortTh
            label="Salary"
            active={sortKey === "salary"}
            onClick={() => toggle("salary")}
          />
          <SortTh
            label="Proj"
            active={sortKey === "projection"}
            onClick={() => toggle("projection")}
          />
          <SortTh
            label="Floor"
            active={sortKey === "floor"}
            onClick={() => toggle("floor")}
          />
          <SortTh
            label="Ceiling"
            active={sortKey === "ceiling"}
            onClick={() => toggle("ceiling")}
          />
          <SortTh
            label="Value"
            active={sortKey === "value"}
            onClick={() => toggle("value")}
          />
        </tr>
      </thead>
      <tbody>
        {sorted.map((r) => (
          <tr
            key={`${r.site}-${r.slateId}-${r.playerUid}`}
            className="border-b border-white/5 odd:bg-white/[0.02]"
          >
            <td className="px-3 py-2 font-medium text-kos-text">
              {r.playerName}
            </td>
            <td className="px-3 py-2 text-kos-text/70">{r.position}</td>
            <td className="px-3 py-2 text-kos-text/80">
              <Link
                href={`/pro/nfl/teams/${r.team}/overview`}
                className="text-kos-gold/90 hover:text-kos-gold"
              >
                {r.team}
              </Link>
              <span className="text-kos-text/40"> vs {r.opponent}</span>
              {r.gameEnv.available && r.gameEnv.total != null ? (
                <span className="mt-0.5 block text-[11px] text-kos-text/40">
                  O/U {r.gameEnv.total}
                  {r.gameEnv.impliedTeamTotal != null
                    ? ` · impl ${r.gameEnv.impliedTeamTotal.toFixed(1)}`
                    : ""}
                </span>
              ) : null}
            </td>
            <td className="px-3 py-2 text-kos-text">
              {formatSalary(r.salary)}
            </td>
            <td className="px-3 py-2 font-semibold text-kos-gold">
              {formatDfsNumber(r.projection)}
            </td>
            <td className="px-3 py-2 text-kos-text/75">
              {formatDfsNumber(r.floor)}
            </td>
            <td className="px-3 py-2 text-kos-text/75">
              {formatDfsNumber(r.ceiling)}
            </td>
            <td className="px-3 py-2 text-kos-text">
              {r.value == null ? "—" : formatDfsNumber(r.value, 2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SortTh({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <th className="px-3 py-3">
      <button
        type="button"
        onClick={onClick}
        className={
          active
            ? "font-semibold text-kos-gold"
            : "font-medium text-kos-text/60 hover:text-kos-text"
        }
      >
        {label}
      </button>
    </th>
  );
}
