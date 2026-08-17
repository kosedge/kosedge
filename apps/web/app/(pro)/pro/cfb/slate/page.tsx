import Link from "next/link";
import SportHubShell from "@/components/pro/SportHubShell";
import { fetchCfbSeasonEngineStatus } from "@/lib/cfb-season-engine";
import {
  gamesForWeek,
  resolveWeekBoard,
} from "@/lib/cfb-official-slate";
import {
  cfbModelDeskHonestyNote,
  cfbModelDeskTruthStates,
} from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";
export const maxDuration = 20;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function projectHref(row: {
  home: string;
  away: string;
  week: number;
  neutral_site?: boolean;
}): string {
  const q = new URLSearchParams({
    home: row.home,
    away: row.away,
    week: String(row.week),
  });
  if (row.neutral_site) q.set("neutral", "1");
  return `/pro/cfb/project-game?${q.toString()}`;
}

function kickoffLabel(raw?: string): string {
  if (!raw) return "—";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw.slice(0, 16);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    weekday: "short",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
  });
}

export default async function CfbOfficialSlatePage({
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
  const weekRaw = Number(firstValue(sp.week) ?? 0);
  const week = weekRaw === 1 ? 1 : 0;

  const status = await fetchCfbSeasonEngineStatus();
  const board = resolveWeekBoard(status.desk?.week_board);
  const games = gamesForWeek(board, week);
  const fbs = games.filter((g) => g.fbs_vs_fbs).length;
  const usedPackaged = (status.desk?.week_board?.games?.length ?? 0) === 0;

  return (
    <SportHubShell
      sportKey="cfb"
      sportName="CFB"
      base="/pro/cfb"
      title="Official slate"
      summary="Week 0 and Week 1 from the official 2026 ESPN FBS schedule. Open a row for research-fair project-game numbers. This is not a betting board and does not claim KEI."
      truthStates={cfbModelDeskTruthStates()}
      truthTestId="cfb-truth-state"
      honestyNote={cfbModelDeskHonestyNote()}
      primaryHref="/pro/cfb/project-game"
      primaryLabel="Project Game"
      secondaryHref="/edge-board/cfb"
      secondaryLabel="Edge Board (markets)"
    >
      <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="CFB official week">
        {[0, 1].map((w) => (
          <Link
            key={w}
            href={w === 0 ? "/pro/cfb/slate" : "/pro/cfb/slate?week=1"}
            role="tab"
            aria-selected={week === w}
            className={`min-h-11 inline-flex items-center rounded-xl px-4 py-2 text-sm font-semibold transition ${
              week === w
                ? "border border-kos-gold/40 bg-kos-gold/15 text-kos-gold"
                : "border border-white/12 bg-black/30 text-kos-text/70 hover:border-kos-gold/30"
            }`}
          >
            Week {w}
          </Link>
        ))}
      </div>

      <p className="mt-3 text-xs text-kos-text/55">
        Official {board.official ? "yes" : "no"} · slate_complete{" "}
        {status.slate_complete || board.slate_complete ? "true" : "false"} ·{" "}
        {games.length} Week {week} games ({fbs} FBS–FBS) · model used_in_spread=false · KEI on Edge Board
        {usedPackaged ? " · packaged ESPN slate (model status unreachable)" : ""}
        {status.schedule_as_of || board.as_of
          ? ` · as_of ${status.schedule_as_of || board.as_of}`
          : ""}
      </p>

      {status.error ? (
        <p className="mt-4 rounded-lg border border-amber-400/25 bg-amber-400/8 px-3 py-2 text-xs text-kos-text/70">
          Model unreachable ({status.error}). Showing packaged official slate —
          research slate only. KEI lives on Edge Board when the model is up.
        </p>
      ) : null}

      {games.length === 0 ? (
        <p className="mt-4 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-kos-text/70">
          No official Week {week} games in the packaged slate.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-white/10 bg-black/30">
          <table className="w-full min-w-[36rem] text-left text-sm text-kos-text/80">
            <thead>
              <tr className="border-b border-white/10 text-[11px] uppercase tracking-[0.1em] text-kos-text/45">
                <th className="px-3 py-2">Matchup</th>
                <th className="px-3 py-2">Kickoff (ET)</th>
                <th className="px-3 py-2">Site</th>
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
                    {kickoffLabel(g.kickoff)}
                  </td>
                  <td className="px-3 py-2.5 text-xs">
                    {g.neutral_site ? "Neutral" : "Home"}
                  </td>
                  <td className="px-3 py-2.5 text-xs text-kos-text/65">
                    {g.fbs_vs_fbs ? "FBS–FBS" : "FBS–FCS"}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <Link
                      href={projectHref(g)}
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
      )}
    </SportHubShell>
  );
}
