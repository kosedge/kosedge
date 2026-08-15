import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import type { CfbTeamDnaRow } from "@/lib/cfb-season-engine";
import { fetchCfbSeasonEngineStatus } from "@/lib/cfb-season-engine";
import {
  formatIndex,
  formatQbClassLabel,
} from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";
export const maxDuration = 20;

type SearchValue = string | string[] | undefined;
type SortKey =
  | "power"
  | "offense"
  | "defense"
  | "uncertainty"
  | "team"
  | "conf"
  | "qb";

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function sortRows(rows: CfbTeamDnaRow[], key: SortKey): CfbTeamDnaRow[] {
  const copy = [...rows];
  copy.sort((a, b) => {
    if (key === "team") return a.team.localeCompare(b.team);
    if (key === "conf")
      return (a.conference ?? "").localeCompare(b.conference ?? "") ||
        a.team.localeCompare(b.team);
    if (key === "qb")
      return (a.qb_class ?? "").localeCompare(b.qb_class ?? "") ||
        a.team.localeCompare(b.team);
    const av =
      key === "offense"
        ? a.offense_index
        : key === "defense"
          ? a.defense_index
          : key === "uncertainty"
            ? a.early_season_uncertainty
            : a.power_index;
    const bv =
      key === "offense"
        ? b.offense_index
        : key === "defense"
          ? b.defense_index
          : key === "uncertainty"
            ? b.early_season_uncertainty
            : b.power_index;
    return (bv ?? -999) - (av ?? -999);
  });
  return copy;
}

function projectNext(row: CfbTeamDnaRow): string | null {
  const next = row.next;
  if (!next?.opponent) return null;
  const home = next.home ? row.team : next.opponent;
  const away = next.home ? next.opponent : row.team;
  const q = new URLSearchParams({
    home,
    away,
    week: String(next.week ?? 0),
  });
  if (next.neutral_site) q.set("neutral", "1");
  return `/pro/cfb/project-game?${q.toString()}`;
}

export default async function CfbTeamDnaPage({
  searchParams,
}: {
  searchParams?:
    | Promise<Record<string, SearchValue>>
    | Record<string, SearchValue>;
}) {
  const sp =
    searchParams && typeof (searchParams as Promise<unknown>).then === "function"
      ? await (searchParams as Promise<Record<string, SearchValue>>)
      : ((searchParams as Record<string, SearchValue>) ?? {});
  const sortRaw = firstValue(sp.sort) ?? "power";
  const sort: SortKey = (
    ["power", "offense", "defense", "uncertainty", "team", "conf", "qb"] as const
  ).includes(sortRaw as SortKey)
    ? (sortRaw as SortKey)
    : "power";
  const q = (firstValue(sp.q) ?? "").trim().toUpperCase();

  const status = await fetchCfbSeasonEngineStatus();
  const dna = status.desk?.team_dna;
  const ladderFallback: CfbTeamDnaRow[] = (
    status.power_style_ladder?.top ?? []
  ).map((row) => ({
    team: row.team,
    conference: row.conference,
    offense_index: row.offense_index,
    defense_index: row.defense_index,
    power_index: row.power_index,
    early_season_uncertainty: row.early_season_uncertainty,
  }));
  const codeFallback: CfbTeamDnaRow[] = (status.team_codes ?? []).map(
    (team) => ({ team }),
  );
  const raw =
    dna?.teams && dna.teams.length > 0
      ? dna.teams
      : ladderFallback.length > 0
        ? ladderFallback
        : codeFallback;
  const filtered = q
    ? raw.filter(
        (r) =>
          r.team.includes(q) ||
          (r.conference ?? "").toUpperCase().includes(q) ||
          (r.qb_name ?? "").toUpperCase().includes(q),
      )
    : raw;
  const rows = sortRows(filtered, sort);
  const warehouse = raw.filter((r) => r.efficiency_fill === "warehouse").length;

  const sorts: { key: SortKey; label: string }[] = [
    { key: "power", label: "Power" },
    { key: "offense", label: "Offense" },
    { key: "defense", label: "Defense" },
    { key: "uncertainty", label: "σ" },
    { key: "qb", label: "QB" },
    { key: "conf", label: "Conf" },
    { key: "team", label: "A–Z" },
  ];

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Team DNA"
      summary="Official 136 FBS rows — power, OFF/DEF, early-season uncertainty, QB class, and efficiency source. Warehouse-fill teams are labeled, not silent 50/50. Research only."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/project-game"
      primaryLabel="Project Game"
      secondaryHref="/pro/cfb/projections"
      secondaryLabel="Win totals"
    >
      <p className="mt-3 text-xs text-kos-text/55">
        {dna?.n ?? rows.length} / {dna?.official_fbs ?? 136} official FBS ·
        warehouse fills {warehouse} · used_in_spread=false
        {status.as_of || status.roster_as_of
          ? ` · roster as_of ${status.as_of || status.roster_as_of}`
          : ""}
      </p>

      <form className="mt-3 flex flex-wrap items-end gap-2" method="get">
        <label className="text-xs text-kos-text/60">
          Filter
          <input
            name="q"
            defaultValue={q}
            placeholder="Team / conf / QB"
            className="mt-1 block min-h-11 w-44 rounded-lg border border-white/15 bg-black/40 px-3 text-sm text-kos-text"
          />
        </label>
        <input type="hidden" name="sort" value={sort} />
        <button
          type="submit"
          className="min-h-11 rounded-lg border border-white/15 px-3 text-xs font-semibold text-kos-text/80"
        >
          Apply
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        {sorts.map((s) => (
          <Link
            key={s.key}
            href={`/pro/cfb/teams?sort=${s.key}${q ? `&q=${encodeURIComponent(q)}` : ""}`}
            className={`min-h-11 inline-flex items-center rounded-lg px-3 text-xs font-semibold ${
              sort === s.key
                ? "border border-kos-gold/40 bg-kos-gold/15 text-kos-gold"
                : "border border-white/12 text-kos-text/65"
            }`}
          >
            {s.label}
          </Link>
        ))}
      </div>

      {status.error ? (
        <p className="mt-4 rounded-lg border border-amber-400/25 bg-amber-400/8 px-3 py-2 text-sm text-kos-text/70">
          Model unreachable ({status.error}).
          {rows.length > 0
            ? " Showing the last usable team list — research only, used_in_spread=false."
            : " Team DNA unavailable."}
        </p>
      ) : null}

      {rows.length === 0 ? (
        <p className="mt-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/70">
          No team rows yet. Open Project Game with an FBS code, or retry when
          the model is reachable.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="w-full min-w-[44rem] text-left text-sm text-kos-text/80">
            <thead>
              <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                <th className="px-3 py-2">Team</th>
                <th className="px-3 py-2">Conf</th>
                <th className="px-3 py-2">Power</th>
                <th className="px-3 py-2">O / D</th>
                <th className="px-3 py-2">σ</th>
                <th className="px-3 py-2">QB</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">Next</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const nextHref = projectNext(row);
                const fill = row.efficiency_fill ?? "";
                return (
                  <tr
                    key={row.team}
                    className="border-b border-white/5 last:border-0"
                  >
                    <td className="px-3 py-1.5 font-medium text-kos-text">
                      {row.team}
                    </td>
                    <td className="px-3 py-1.5 text-xs">
                      {row.conference ?? "—"}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums">
                      {formatIndex(row.power_index, 3)}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums text-xs">
                      {formatIndex(row.offense_index, 2)} /{" "}
                      {formatIndex(row.defense_index, 2)}
                    </td>
                    <td className="px-3 py-1.5 tabular-nums text-xs">
                      {formatIndex(row.early_season_uncertainty, 2)}
                    </td>
                    <td className="px-3 py-1.5 text-xs">
                      {formatQbClassLabel(row.qb_class)}
                      {row.open_qb ? (
                        <span className="ml-1 text-amber-200/80">open</span>
                      ) : null}
                    </td>
                    <td className="px-3 py-1.5 text-[11px] text-kos-text/60">
                      {fill === "warehouse" ? (
                        <span className="text-sky-300/90">warehouse fill</span>
                      ) : fill === "thin" ? (
                        <span className="text-amber-200/80">thin sample</span>
                      ) : fill === "league_avg" ? (
                        <span className="text-kos-text/45">league avg</span>
                      ) : (
                        fill.replace(/_/g, " ") || "—"
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-xs">
                      {nextHref && row.next ? (
                        <Link
                          href={nextHref}
                          className="font-semibold text-kos-gold hover:underline"
                        >
                          W{row.next.week} {row.next.opponent}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </SportHubShell>
  );
}
