import Link from "next/link";
import {
  gamesForWeek,
  kickoffEtLabel,
  matchupLabel,
  officialSlateAttribution,
  officialSlateWeeks,
  packagedOfficialWeekBoard,
  projectGameHref,
  type CfbWeekBoardGame,
} from "@/lib/cfb-official-slate";

function siteLabel(row: CfbWeekBoardGame): string {
  if (row.neutral_site) return "Neutral";
  return "Home";
}

function typeLabel(row: CfbWeekBoardGame): string {
  return row.fbs_vs_fbs ? "FBS–FBS" : "FBS–FCS";
}

function scoreLabel(row: CfbWeekBoardGame): string {
  if (row.away_score == null || row.home_score == null) return "—";
  return `${row.away_score}–${row.home_score}`;
}

function statusLabel(row: CfbWeekBoardGame): string {
  if (row.status === "final") return "Final";
  if (row.status === "accepted") return "Scheduled";
  if (row.status === "needs_review") return "Needs review";
  if (row.status === "unconfirmed_secondary") return "Unconfirmed";
  return row.status || "—";
}

export default function CfbOfficialSlatePanel({
  week,
  hrefForWeek,
}: {
  week: number;
  hrefForWeek: (week: number) => string;
}) {
  const board = packagedOfficialWeekBoard();
  const weeks = officialSlateWeeks();
  const games = gamesForWeek(board, week);
  const fbs = games.filter((g) => g.fbs_vs_fbs).length;
  const finals = games.filter((g) => g.status === "final").length;
  const confirmed = games.filter(
    (g) => g.status === "accepted" || g.status === "final",
  ).length;

  return (
    <section className="mt-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-kos-text">
            Official Slate
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-kos-text/60">
            {officialSlateAttribution(board)}
          </p>
          <p className="mt-1 text-xs text-kos-text/50">
            {board.slate_version} · {games.length} Week {week} games ({fbs}{" "}
            FBS–FBS)
            {finals ? ` · ${finals} final` : ""} · {confirmed} desk-confirmed ·
            missing book listings show as unconfirmed, not invented
          </p>
        </div>
        <div
          className="flex flex-wrap gap-2"
          role="tablist"
          aria-label="CFB official week"
        >
          {weeks.map((w) => (
            <Link
              key={w}
              href={hrefForWeek(w)}
              role="tab"
              aria-selected={week === w}
              className={`min-h-11 inline-flex items-center rounded-xl px-4 py-2 text-sm font-semibold transition ${
                week === w
                  ? "border border-kos-gold/40 bg-kos-gold/15 text-kos-gold"
                  : "border border-white/12 bg-black/30 text-kos-text/70 hover:border-kos-gold/30"
              }`}
            >
              Week {w}
              {w === 0 ? " (finals)" : ""}
            </Link>
          ))}
        </div>
      </div>

      {games.length === 0 ? (
        <p className="mt-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/70">
          No official Week {week} games in the KosEdge slate yet.
        </p>
      ) : (
        <>
          <ol className="mt-4 space-y-2 sm:hidden">
            {games.map((g) => (
              <li
                key={g.game_id || `${g.away}@${g.home}-${g.week}`}
                className="rounded-xl border border-white/10 bg-black/30 px-3 py-2.5"
              >
                <p className="font-semibold text-kos-text">{matchupLabel(g)}</p>
                <p className="mt-1 text-xs text-kos-text/60">
                  {g.status === "final"
                    ? `Final ${scoreLabel(g)}`
                    : `${kickoffEtLabel(g.kickoff)} ET`}{" "}
                  · {siteLabel(g)}
                  {g.conference ? ` · ${g.conference}` : ""} · {typeLabel(g)}
                </p>
                {g.venue ? (
                  <p className="text-[11px] text-kos-text/45">{g.venue}</p>
                ) : null}
                <Link
                  href={projectGameHref(g)}
                  className="mt-2 inline-flex min-h-11 items-center text-xs font-semibold text-kos-gold hover:underline"
                >
                  Project →
                </Link>
              </li>
            ))}
          </ol>

          <div className="mt-4 hidden overflow-x-auto rounded-2xl border border-white/10 bg-black/30 sm:block">
            <table className="w-full min-w-[44rem] text-left text-sm text-kos-text/80">
              <thead>
                <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                  <th className="px-3 py-2">Matchup</th>
                  <th className="px-3 py-2">Kickoff (ET)</th>
                  <th className="px-3 py-2">Score</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Site</th>
                  <th className="px-3 py-2">Conf</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {games.map((g) => (
                  <tr
                    key={g.game_id || `${g.away}@${g.home}-${g.week}`}
                    className="border-b border-white/5 last:border-0"
                  >
                    <td className="px-3 py-2.5 font-medium text-kos-text">
                      {g.away} @ {g.home}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-kos-text/70">
                      {kickoffEtLabel(g.kickoff)}
                    </td>
                    <td className="px-3 py-2.5 text-xs font-semibold text-kos-text">
                      {scoreLabel(g)}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-kos-text/65">
                      {statusLabel(g)}
                    </td>
                    <td className="px-3 py-2.5 text-xs">
                      {siteLabel(g)}
                      {g.venue ? (
                        <span className="block text-[11px] text-kos-text/45">
                          {g.venue}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-kos-text/65">
                      {g.conference ?? "—"}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-kos-text/65">
                      {typeLabel(g)}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <Link
                        href={projectGameHref(g)}
                        className="inline-flex min-h-11 items-center text-xs font-semibold text-kos-gold hover:underline sm:min-h-0"
                      >
                        Project →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
