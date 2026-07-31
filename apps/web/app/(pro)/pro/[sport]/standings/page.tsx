import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchNflIntel } from "@/lib/nfl-intel";
import { fetchEspnNflStandings } from "@/lib/nfl-espn-schedule";
import {
  NFL_TEAM_DIRECTORY,
  resolveConferenceDivision,
  teamDisplayName,
} from "@/lib/nfl-team-intel";
import { loadLatestNflPreseasonBundle2026 } from "@/lib/nfl-preseason-artifacts";

export const dynamic = "force-dynamic";

type ViewMode = "division" | "conference" | "league";

type StandingRow = {
  team: string;
  wins: number | null;
  losses: number | null;
  ties: number | null;
  winPct: number | null;
  pointDiff: number | null;
  streak: string | null;
  last5: string | null;
  conference: string;
  division: string;
  keiProjWins: number | null;
  playoffProb: number | null;
};

function firstValue(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function recordLabel(row: StandingRow): string {
  if (row.wins == null || row.losses == null) return "—";
  if (row.ties && row.ties > 0) return `${row.wins}-${row.losses}-${row.ties}`;
  return `${row.wins}-${row.losses}`;
}

function groupKey(row: StandingRow, view: ViewMode): string {
  if (view === "league") return "League";
  if (view === "conference") return row.conference || "Conference";
  return `${row.conference} ${row.division}`.trim() || "Division";
}

export default async function StandingsPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { sport } = await params;
  const filters = await searchParams;
  if (sport !== "nfl") notFound();

  const viewRaw = (firstValue(filters.view) ?? "division").toLowerCase();
  const view: ViewMode =
    viewRaw === "conference" || viewRaw === "league" ? viewRaw : "division";
  const confFilter = firstValue(filters.conf)?.toUpperCase();

  const bundle = loadLatestNflPreseasonBundle2026();
  const projByTeam = new Map(
    (bundle?.teamRows ?? []).map(
      (r) =>
        [
          r.team,
          { wins: r.expectedWins, playoff: r.playoffProb },
        ] as const,
    ),
  );

  const intel = await fetchNflIntel("standings", {});
  let rows: StandingRow[] = [];

  if (intel.count > 0) {
    rows = intel.rows
      .filter((r) => typeof r.team === "string")
      .map((r) => {
        const team = String(r.team);
        const resolved = resolveConferenceDivision(team);
        const proj = projByTeam.get(team);
        return {
          team,
          wins: typeof r.wins === "number" ? r.wins : null,
          losses: typeof r.losses === "number" ? r.losses : null,
          ties: typeof r.ties === "number" ? r.ties : null,
          winPct: typeof r.win_pct === "number" ? r.win_pct : null,
          pointDiff: typeof r.point_diff === "number" ? r.point_diff : null,
          streak: typeof r.streak === "string" ? r.streak : null,
          last5: typeof r.last_5 === "string" ? r.last_5 : null,
          conference: resolved?.conference ?? String(r.conference ?? ""),
          division: resolved?.division ?? String(r.division ?? ""),
          keiProjWins: proj?.wins ?? null,
          playoffProb: proj?.playoff ?? null,
        };
      });
  } else {
    const espnRows = await fetchEspnNflStandings(2025);
    rows = espnRows.map((r) => {
      const resolved = resolveConferenceDivision(r.team);
      const proj = projByTeam.get(r.team);
      return {
        team: r.team,
        wins: r.wins ?? null,
        losses: r.losses ?? null,
        ties: r.ties ?? null,
        winPct: r.win_pct ?? null,
        pointDiff: r.point_diff ?? null,
        streak: null,
        last5: null,
        conference: resolved?.conference ?? r.conference ?? "",
        division: resolved?.division ?? r.division ?? "",
        keiProjWins: proj?.wins ?? null,
        playoffProb: proj?.playoff ?? null,
      };
    });
  }

  // Ensure all 32 teams appear even if a source misses one.
  if (rows.length < 32) {
    const have = new Set(rows.map((r) => r.team));
    for (const entry of NFL_TEAM_DIRECTORY) {
      if (have.has(entry.code)) continue;
      const proj = projByTeam.get(entry.code);
      rows.push({
        team: entry.code,
        wins: null,
        losses: null,
        ties: null,
        winPct: null,
        pointDiff: null,
        streak: null,
        last5: null,
        conference: entry.conference,
        division: entry.division,
        keiProjWins: proj?.wins ?? null,
        playoffProb: proj?.playoff ?? null,
      });
    }
  }

  if (confFilter === "AFC" || confFilter === "NFC") {
    rows = rows.filter((r) => r.conference === confFilter);
  }

  rows.sort((a, b) => {
    const aw = a.winPct ?? -1;
    const bw = b.winPct ?? -1;
    if (bw !== aw) return bw - aw;
    return (b.keiProjWins ?? 0) - (a.keiProjWins ?? 0);
  });

  const groups = new Map<string, StandingRow[]>();
  for (const row of rows) {
    const key = groupKey(row, view);
    const list = groups.get(key) ?? [];
    list.push(row);
    groups.set(key, list);
  }

  const bubble = [...rows]
    .filter((r) => (r.playoffProb ?? 0) > 0.2 && (r.playoffProb ?? 0) < 0.55)
    .sort((a, b) => (b.playoffProb ?? 0) - (a.playoffProb ?? 0))
    .slice(0, 6);
  const clinched = [...rows]
    .filter((r) => (r.playoffProb ?? 0) >= 0.85)
    .sort((a, b) => (b.playoffProb ?? 0) - (a.playoffProb ?? 0))
    .slice(0, 6);

  const sourceNote =
    intel.count > 0
      ? "Live intel standings"
      : "2025 final standings (labeled fallback) + KEI 2026 projections";

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
            NFL Standings · Research
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-kos-text">
            Standings
          </h1>
          <p className="mt-2 text-sm text-kos-text/70">{sourceNote}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/pro/nfl/overview"
            className="rounded-xl border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text"
          >
            NFL Overview
          </Link>
          <Link
            href="/edge-board/nfl"
            className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-3 py-1.5 text-xs font-semibold text-kos-gold"
          >
            Edge Board
          </Link>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {(
          [
            ["division", "Division"],
            ["conference", "Conference"],
            ["league", "League"],
          ] as const
        ).map(([id, label]) => (
          <Link
            key={id}
            href={`/pro/nfl/standings?view=${id}${confFilter ? `&conf=${confFilter}` : ""}`}
            className={
              view === id
                ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            {label}
          </Link>
        ))}
        <span className="mx-1 text-kos-text/25">|</span>
        {(["", "AFC", "NFC"] as const).map((c) => (
          <Link
            key={c || "all"}
            href={`/pro/nfl/standings?view=${view}${c ? `&conf=${c}` : ""}`}
            className={
              (confFilter ?? "") === c
                ? "rounded-md border border-edge-green/40 bg-edge-green/10 px-3 py-1.5 text-xs font-semibold text-edge-green"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            {c || "All"}
          </Link>
        ))}
      </div>

      <section className="mt-6 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">
            At a Glance · High playoff probability
          </h2>
          <ul className="mt-3 space-y-1.5 text-sm">
            {clinched.length === 0 ? (
              <li className="text-kos-text/55">No clinch signals yet.</li>
            ) : (
              clinched.map((r) => (
                <li key={r.team} className="flex justify-between gap-2">
                  <Link
                    href={`/pro/nfl/teams/${r.team}/overview`}
                    className="text-kos-text hover:text-kos-gold"
                  >
                    {r.team}
                  </Link>
                  <span className="text-kos-text/60">
                    {((r.playoffProb ?? 0) * 100).toFixed(0)}%
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/35 p-4">
          <h2 className="text-sm font-semibold text-kos-gold">
            At a Glance · Bubble
          </h2>
          <ul className="mt-3 space-y-1.5 text-sm">
            {bubble.length === 0 ? (
              <li className="text-kos-text/55">No bubble cluster yet.</li>
            ) : (
              bubble.map((r) => (
                <li key={r.team} className="flex justify-between gap-2">
                  <Link
                    href={`/pro/nfl/teams/${r.team}/overview`}
                    className="text-kos-text hover:text-kos-gold"
                  >
                    {r.team}
                  </Link>
                  <span className="text-kos-text/60">
                    {((r.playoffProb ?? 0) * 100).toFixed(0)}%
                  </span>
                </li>
              ))
            )}
          </ul>
        </div>
      </section>

      <div className="mt-6 space-y-8">
        {Array.from(groups.entries()).map(([group, groupRows]) => (
          <section key={group}>
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
              {group}
            </h2>
            <div className="mt-3 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-xs uppercase tracking-wide text-kos-text/55">
                    <th className="px-3 py-3">Team</th>
                    <th className="px-3 py-3">W-L</th>
                    <th className="px-3 py-3">Win%</th>
                    <th className="px-3 py-3">Div</th>
                    <th className="px-3 py-3">PD</th>
                    <th className="px-3 py-3">Streak</th>
                    <th className="px-3 py-3">Last 5</th>
                    <th className="px-3 py-3">KEI Proj Wins</th>
                    <th className="px-3 py-3">Playoff Prob</th>
                  </tr>
                </thead>
                <tbody>
                  {groupRows.map((row) => (
                    <tr
                      key={row.team}
                      className="border-b border-white/5 odd:bg-white/[0.02]"
                    >
                      <td className="px-3 py-2.5">
                        <Link
                          href={`/pro/nfl/teams/${row.team}/overview`}
                          className="font-medium text-kos-text hover:text-kos-gold"
                        >
                          {row.team}{" "}
                          <span className="text-kos-text/45">
                            {teamDisplayName(row.team)}
                          </span>
                        </Link>
                      </td>
                      <td className="px-3 py-2.5">{recordLabel(row)}</td>
                      <td className="px-3 py-2.5">
                        {row.winPct != null
                          ? (row.winPct * 100).toFixed(1) + "%"
                          : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-kos-text/70">
                        {row.division || "—"}
                      </td>
                      <td className="px-3 py-2.5">
                        {row.pointDiff != null
                          ? `${row.pointDiff > 0 ? "+" : ""}${row.pointDiff}`
                          : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-kos-text/70">
                        {row.streak ?? "—"}
                      </td>
                      <td className="px-3 py-2.5 text-kos-text/70">
                        {row.last5 ?? "—"}
                      </td>
                      <td className="px-3 py-2.5 font-semibold text-kos-gold">
                        {row.keiProjWins != null
                          ? row.keiProjWins.toFixed(1)
                          : "—"}
                      </td>
                      <td className="px-3 py-2.5 text-kos-text/80">
                        {row.playoffProb != null
                          ? `${(row.playoffProb * 100).toFixed(1)}%`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
