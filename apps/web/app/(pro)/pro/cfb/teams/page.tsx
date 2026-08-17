import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import {
  CFB_CONFERENCE_FILTERS,
  cfbTeamDisplayName,
  conferencePreviewHrefForFilter,
  displayCfbConference,
  parseCfbConferenceFilter,
  teamMatchesConferenceFilter,
  type CfbConferenceFilter,
} from "@/lib/cfb-conferences";
import { findCfbTeamPreview } from "@/lib/cfb-previews";
import {
  cfbPowerTeams,
  cfbResearchVersionStrip,
  projectGameHref,
  type CfbPowerSotTeam,
} from "@/lib/cfb-research-artifacts";
import {
  formatIndex,
  formatQbClassLabel,
} from "@/lib/cfb-season-engine-format";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

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

function sortRows(rows: CfbPowerSotTeam[], key: SortKey): CfbPowerSotTeam[] {
  const copy = [...rows];
  copy.sort((a, b) => {
    if (key === "team") return a.team.localeCompare(b.team);
    if (key === "conf") {
      const ac = displayCfbConference(a.team, a.conference);
      const bc = displayCfbConference(b.team, b.conference);
      return ac.localeCompare(bc) || a.team.localeCompare(b.team);
    }
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

function querySuffix(sort: SortKey, q: string, conf: CfbConferenceFilter): string {
  const p = new URLSearchParams();
  if (sort !== "power") p.set("sort", sort);
  if (q) p.set("q", q);
  if (conf !== "all") p.set("conf", conf);
  const s = p.toString();
  return s ? `?${s}` : "";
}

export default async function CfbTeamsPowerPage({
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
  const conf = parseCfbConferenceFilter(firstValue(sp.conf));
  const version = cfbResearchVersionStrip();
  const raw = cfbPowerTeams();
  const filtered = raw.filter((r) => {
    if (!teamMatchesConferenceFilter(r.team, r.conference, conf)) return false;
    if (!q) return true;
    const display = displayCfbConference(r.team, r.conference).toUpperCase();
    const name = cfbTeamDisplayName(r.team).toUpperCase();
    return (
      r.team.includes(q) ||
      display.includes(q) ||
      name.includes(q) ||
      (r.qb_name ?? "").toUpperCase().includes(q)
    );
  });
  const rows = sortRows(filtered, sort);
  const warehouse = raw.filter((r) => r.efficiency_fill === "warehouse").length;
  const overlayCount = raw.filter(
    (r) => displayCfbConference(r.team, r.conference) !== (r.conference || "—"),
  ).length;

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
      title="Power + Teams"
      summary="Single power source — 136 official FBS rows. Sortable, conference-filtered, warehouse-fill labeled. Next opponent opens Project Game when the game is on the W0/W1 slate. Research only."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/projections"
      primaryLabel="Win totals"
      secondaryHref="/pro/cfb/previews"
      secondaryLabel="Previews"
    >
      <p className="mt-3 text-xs text-kos-text/55">
        {raw.length} / 136 official FBS · showing {rows.length}
        {conf !== "all" ? ` · ${conf}` : ""} · warehouse fills {warehouse} ·
        affiliation overlay {overlayCount} · {version.power_version} · as_of{" "}
        {version.as_of} · used_in_spread=false
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
        {conf !== "all" ? <input type="hidden" name="conf" value={conf} /> : null}
        <button
          type="submit"
          className="min-h-11 rounded-lg border border-white/15 px-3 text-xs font-semibold text-kos-text/80"
        >
          Apply
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        {CFB_CONFERENCE_FILTERS.map((f) => (
          <Link
            key={f.key}
            href={`/pro/cfb/teams${querySuffix(sort, q, f.key)}`}
            className={`min-h-11 inline-flex items-center rounded-lg px-3 text-xs font-semibold ${
              conf === f.key
                ? "border border-kos-gold/40 bg-kos-gold/15 text-kos-gold"
                : "border border-white/12 text-kos-text/65"
            }`}
          >
            {f.label}
          </Link>
        ))}
        {conferencePreviewHrefForFilter(conf) ? (
          <Link
            href={conferencePreviewHrefForFilter(conf)!}
            className="min-h-11 inline-flex items-center rounded-lg border border-kos-gold/25 px-3 text-xs font-semibold text-kos-gold"
          >
            Conference preview →
          </Link>
        ) : (
          <Link
            href="/pro/cfb/conferences"
            className="min-h-11 inline-flex items-center rounded-lg border border-white/12 px-3 text-xs font-semibold text-kos-text/65"
          >
            Conference previews
          </Link>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {sorts.map((s) => (
          <Link
            key={s.key}
            href={`/pro/cfb/teams${querySuffix(s.key, q, conf)}`}
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

      {rows.length === 0 ? (
        <p className="mt-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/70">
          No teams match that filter.
        </p>
      ) : (
        <>
          <div className="mt-4 grid gap-3 sm:hidden">
            {rows.map((row) => {
              const nextHref = projectGameHref({
                team: row.team,
                next: row.next,
              });
              const preview = findCfbTeamPreview(row.team);
              const display = displayCfbConference(row.team, row.conference);
              const fill = row.efficiency_fill ?? "";
              return (
                <article
                  key={row.team}
                  className="rounded-xl border border-white/10 bg-black/35 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <Link
                      href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                      className="font-semibold text-kos-text hover:text-kos-gold"
                    >
                      <span className="mr-2 text-kos-text/40">
                        {row.rank ?? "—"}
                      </span>
                      {cfbTeamDisplayName(row.team)}
                    </Link>
                    <span className="text-xs text-kos-text/55">{display}</span>
                  </div>
                  <p className="mt-1 text-xs tabular-nums text-kos-text/70">
                    Power {formatIndex(row.power_index, 3)} · O/D{" "}
                    {formatIndex(row.offense_index, 2)} /{" "}
                    {formatIndex(row.defense_index, 2)} · σ{" "}
                    {formatIndex(row.early_season_uncertainty, 2)}
                  </p>
                  <p className="mt-1 text-xs text-kos-text/60">
                    {formatQbClassLabel(row.qb_class)}
                    {row.qb_name ? ` · ${row.qb_name}` : ""}
                    {row.open_qb ? " · open" : ""}
                    {fill === "warehouse" ? " · warehouse fill" : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    {nextHref && row.next ? (
                      <Link
                        href={nextHref}
                        className="font-semibold text-kos-gold hover:underline"
                      >
                        W{row.next.week} {row.next.opponent} → Project
                      </Link>
                    ) : null}
                    {preview ? (
                      <Link
                        href={`/pro/cfb/previews/${preview.slug}`}
                        className="text-kos-text/70 hover:text-kos-gold"
                      >
                        Preview
                      </Link>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>

          <div className="mt-4 hidden overflow-x-auto rounded-2xl border border-white/10 bg-black/30 sm:block">
            <table className="w-full min-w-[48rem] text-left text-sm text-kos-text/80">
              <thead>
                <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                  <th className="px-3 py-2">#</th>
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
                  const nextHref = projectGameHref({
                    team: row.team,
                    next: row.next,
                  });
                  const fill = row.efficiency_fill ?? "";
                  const display = displayCfbConference(row.team, row.conference);
                  const overlay =
                    display !== (row.conference || "—") ? display : null;
                  return (
                    <tr
                      key={row.team}
                      className="border-b border-white/5 last:border-0"
                    >
                      <td className="px-3 py-1.5 text-kos-text/45">
                        {row.rank ?? "—"}
                      </td>
                      <td className="px-3 py-1.5 font-medium text-kos-text">
                        <Link
                          href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                          className="hover:text-kos-gold"
                        >
                          {row.team}
                        </Link>
                        {findCfbTeamPreview(row.team) ? (
                          <Link
                            href={`/pro/cfb/previews/${findCfbTeamPreview(row.team)!.slug}`}
                            className="ml-2 text-[11px] text-kos-gold/80 hover:underline"
                          >
                            preview
                          </Link>
                        ) : null}
                      </td>
                      <td className="px-3 py-1.5 text-xs">
                        {overlay ? (
                          <span title={`SoT said ${row.conference}`}>
                            {overlay}
                            <span className="ml-1 text-kos-text/35">*</span>
                          </span>
                        ) : (
                          display
                        )}
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
          {overlayCount > 0 ? (
            <p className="mt-2 text-[11px] text-kos-text/45">
              * Display affiliation overlay on {overlayCount} SoT Independent
              leftovers. Power index is unchanged.
            </p>
          ) : null}
        </>
      )}
    </SportHubShell>
  );
}
