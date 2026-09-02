import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { fetchNhlFantasyBoard } from "@/lib/nhl-fantasy-board";

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

export default async function NhlFantasyPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const viewRaw = (firstValue(search.view) ?? "season").toLowerCase();
  const view = viewRaw === "slate" ? "slate" : "season";
  const board = await fetchNhlFantasyBoard({ view, limit: 120 });

  return (
    <SportHubShell
      sportKey="nhl"
      sportName="NHL"
      base="/pro/nhl"
      badge="NHL Fantasy Desk"
      title="NHL Fantasy"
      summary="Season ranks and slate from PlayerProjection — same means as props. Scoring only; no second scorer."
      primaryHref="/pro/nhl/props"
      primaryLabel="Props (dark) →"
      secondaryHref="/edge-board/nhl"
      secondaryLabel="Edge board →"
    >
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6 sm:p-8">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm font-semibold text-kos-gold">
            Chapter 7 · {view === "slate" ? "Slate" : "Season"} board
          </p>
          <div className="flex gap-2 text-xs">
            <Link
              href="/pro/nhl/fantasy?view=season"
              className={`rounded-lg border px-3 py-1.5 ${
                view === "season"
                  ? "border-kos-gold/50 bg-kos-gold/10 text-kos-gold"
                  : "border-white/15 text-kos-text/70"
              }`}
            >
              Season
            </Link>
            <Link
              href="/pro/nhl/fantasy?view=slate"
              className={`rounded-lg border px-3 py-1.5 ${
                view === "slate"
                  ? "border-kos-gold/50 bg-kos-gold/10 text-kos-gold"
                  : "border-white/15 text-kos-text/70"
              }`}
            >
              Slate
            </Link>
          </div>
        </div>
        <p className="mt-2 text-sm text-kos-text/70">
          Profile <span className="text-kos-text">{board.scoringProfile}</span>{" "}
          · {board.fantasyVersion}. Box stats are Ch5 fields; fantasy_pts
          applies the published map only (G/A/SOG skaters · SAVES goalies).
        </p>
        {Object.keys(board.scoringMap).length > 0 ? (
          <p className="mt-2 text-xs text-kos-text/50">
            Map:{" "}
            {Object.entries(board.scoringMap)
              .map(([k, v]) => `${k}=${v}`)
              .join(" · ")}
          </p>
        ) : null}
        <p className="mt-3 text-sm text-kos-text/60">
          {board.error
            ? `Board unavailable: ${board.error}`
            : board.count > 0
              ? `${board.count} players · max team ΣG drift ${board.maxTeamGDrift ?? "—"} (cap ${board.residualCap ?? 0.15})${board.goalieStartShareOk === false ? " · start_share warn" : ""}`
              : board.message || "No fantasy rows — PlayerProjection required."}
        </p>

        {board.rows.length > 0 ? (
          <div className="mt-4 overflow-x-auto rounded-xl border border-white/10">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-white/5 text-xs uppercase tracking-wide text-kos-text/50">
                <tr>
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Player</th>
                  <th className="px-3 py-2">TOI</th>
                  <th className="px-3 py-2">G</th>
                  <th className="px-3 py-2">A</th>
                  <th className="px-3 py-2">SOG</th>
                  <th className="px-3 py-2">SAVES</th>
                  <th className="px-3 py-2">FP/G</th>
                  {view === "season" ? (
                    <th className="px-3 py-2">FP/Szn</th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {board.rows.slice(0, 60).map((row) => (
                  <tr
                    key={`${row.playerId}-${row.team}-${row.playerType}`}
                    className="border-t border-white/5"
                  >
                    <td className="px-3 py-2 tabular-nums text-kos-text/50">
                      {row.rank}
                    </td>
                    <td className="px-3 py-2">
                      <div className="font-medium text-kos-text">
                        {row.playerName}
                      </div>
                      <div className="text-xs text-kos-text/45">
                        {row.team}
                        {row.playerType === "goalie" ? " · G" : ""}
                      </div>
                    </td>
                    <td className="px-3 py-2 tabular-nums text-kos-text/70">
                      {row.toi != null
                        ? row.toi.toFixed(1)
                        : row.startShare != null
                          ? `${(row.startShare * 100).toFixed(0)}%`
                          : "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-kos-text/80">
                      {row.g?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-kos-text/70">
                      {row.a?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-kos-text/70">
                      {row.sog?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-kos-text/70">
                      {row.saves?.toFixed(1) ?? "—"}
                    </td>
                    <td className="px-3 py-2 tabular-nums font-medium text-kos-gold">
                      {row.fantasyPts?.toFixed(2) ?? "—"}
                    </td>
                    {view === "season" ? (
                      <td className="px-3 py-2 tabular-nums text-kos-text/70">
                        {row.seasonFantasyPts?.toFixed(0) ?? "—"}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </SportHubShell>
  );
}
