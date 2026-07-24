import Link from "next/link";
import {
  loadLatestNflPreseasonBundle2026,
  type PlayerProjectionTotalsRow,
  type TeamProjectionRow,
} from "@/lib/nfl-preseason-artifacts";

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function percentage(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function totalYards(player: PlayerProjectionTotalsRow): number {
  return (
    player.passYardsTotal + player.rushYardsTotal + player.receivingYardsTotal
  );
}

function sortTeamRows(
  rows: TeamProjectionRow[],
  key: string,
): TeamProjectionRow[] {
  const sortable = [...rows];
  if (key === "sb") {
    sortable.sort((a, b) => b.superBowlWinProb - a.superBowlWinProb);
    return sortable;
  }
  if (key === "wins") {
    sortable.sort((a, b) => b.expectedWins - a.expectedWins);
    return sortable;
  }
  sortable.sort((a, b) => b.playoffProb - a.playoffProb);
  return sortable;
}

function sortPlayerRows(
  rows: PlayerProjectionTotalsRow[],
  key: string,
): PlayerProjectionTotalsRow[] {
  const sortable = [...rows];
  if (key === "tds") {
    sortable.sort(
      (a, b) =>
        b.passTdsTotal +
        b.rushTdsTotal +
        b.recTdsTotal -
        (a.passTdsTotal + a.rushTdsTotal + a.recTdsTotal),
    );
    return sortable;
  }
  if (key === "receptions") {
    sortable.sort((a, b) => b.receptionsTotal - a.receptionsTotal);
    return sortable;
  }
  sortable.sort((a, b) => totalYards(b) - totalYards(a));
  return sortable;
}

export default async function NflProjectionsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const bundle = loadLatestNflPreseasonBundle2026();
  if (!bundle) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
        <section className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-amber-100">
          <h1 className="text-2xl font-semibold">NFL Projections Hub</h1>
          <p className="mt-2 text-sm text-amber-100/90">
            No 2026 preseason simulation bundle was found yet. Run the
            simulation export and reload this page.
          </p>
        </section>
      </main>
    );
  }

  const team = (firstValue(search.team) ?? "").toUpperCase();
  const position = (firstValue(search.position) ?? "").toUpperCase();
  const playerSearch = (firstValue(search.player) ?? "").trim().toLowerCase();
  const teamSort = firstValue(search.teamSort) ?? "playoff";
  const playerSort = firstValue(search.playerSort) ?? "yards";
  const phase = firstValue(search.phase) === "playoff" ? "playoff" : "regular";

  const uniqueTeams = [
    ...new Set(bundle.teamRows.map((row) => row.team)),
  ].sort();
  const phaseRows =
    phase === "playoff"
      ? bundle.playerTotalsPlayoff
      : bundle.playerTotalsRegular;
  const uniquePositions = [
    ...new Set(phaseRows.map((row) => row.position)),
  ].sort();

  const teamRows = sortTeamRows(
    bundle.teamRows.filter((row) => (team ? row.team === team : true)),
    teamSort,
  );
  const players = sortPlayerRows(
    phaseRows.filter((row) => {
      if (team && row.team !== team) return false;
      if (position && row.position !== position) return false;
      if (playerSearch && !row.playerName.toLowerCase().includes(playerSearch))
        return false;
      return true;
    }),
    playerSort,
  );

  const favorite = sortTeamRows(bundle.teamRows, "sb")[0];
  const winsLeader = sortTeamRows(bundle.teamRows, "wins")[0];
  const playoffLeader = sortTeamRows(bundle.teamRows, "playoff")[0];
  const fantasyLeader = sortPlayerRows(bundle.playerTotalsRegular, "yards")[0];

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
      <section className="rounded-3xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-4xl">
            <p className="inline-flex items-center rounded-full border border-kos-gold/35 bg-kos-gold/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-kos-gold">
              2026 NFL Projections Hub
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Betting + Fantasy Decision Center
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Browse projected wins, playoff/Super Bowl probabilities, and
              player totals in one place. Filters keep the view focused for bet
              prep and fantasy drafting.
            </p>
            <p className="mt-2 text-xs text-kos-text/65">
              Source: {bundle.bundleDirName}
              {bundle.generatedAtUtc
                ? ` • Generated ${new Date(bundle.generatedAtUtc).toLocaleString()}`
                : ""}
            </p>
          </div>
          <Link
            href="/pro/nfl/overview"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
          >
            Back to NFL Overview
          </Link>
        </div>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-wide text-kos-text/60">
            Super Bowl Favorite
          </p>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {favorite?.team ?? "N/A"}
          </p>
          <p className="text-sm text-kos-gold">
            {percentage(favorite?.superBowlWinProb ?? 0, 2)} title probability
          </p>
        </article>
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-wide text-kos-text/60">
            Wins Leader
          </p>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {winsLeader?.team ?? "N/A"}
          </p>
          <p className="text-sm text-kos-gold">
            {(winsLeader?.expectedWins ?? 0).toFixed(2)} projected wins
          </p>
        </article>
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-wide text-kos-text/60">
            Highest Playoff Odds
          </p>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {playoffLeader?.team ?? "N/A"}
          </p>
          <p className="text-sm text-kos-gold">
            {percentage(playoffLeader?.playoffProb ?? 0, 2)} to qualify
          </p>
        </article>
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-wide text-kos-text/60">
            Fantasy Yards Leader
          </p>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {fantasyLeader?.playerName ?? "N/A"}
          </p>
          <p className="text-sm text-kos-gold">
            {totalYards(
              fantasyLeader ?? ({} as PlayerProjectionTotalsRow),
            ).toFixed(1)}{" "}
            combined yards
          </p>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <form className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <label className="text-xs text-kos-text/70">
            Team
            <select
              name="team"
              defaultValue={team}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 p-2 text-sm"
            >
              <option value="">All teams</option>
              {uniqueTeams.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-kos-text/70">
            Position
            <select
              name="position"
              defaultValue={position}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 p-2 text-sm"
            >
              <option value="">All positions</option>
              {uniquePositions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-kos-text/70">
            Season phase
            <select
              name="phase"
              defaultValue={phase}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 p-2 text-sm"
            >
              <option value="regular">Regular season</option>
              <option value="playoff">Playoff</option>
            </select>
          </label>
          <label className="text-xs text-kos-text/70">
            Team table sort
            <select
              name="teamSort"
              defaultValue={teamSort}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 p-2 text-sm"
            >
              <option value="playoff">Playoff probability</option>
              <option value="wins">Expected wins</option>
              <option value="sb">Super Bowl probability</option>
            </select>
          </label>
          <label className="text-xs text-kos-text/70">
            Player table sort
            <select
              name="playerSort"
              defaultValue={playerSort}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 p-2 text-sm"
            >
              <option value="yards">Total yards</option>
              <option value="tds">Total TDs</option>
              <option value="receptions">Total receptions</option>
            </select>
          </label>
          <label className="text-xs text-kos-text/70">
            Player search
            <input
              type="search"
              name="player"
              defaultValue={playerSearch}
              placeholder="Search player name"
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 p-2 text-sm"
            />
          </label>
          <button
            type="submit"
            className="rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/50"
          >
            Apply filters
          </button>
        </form>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-2">
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <h2 className="text-xl font-semibold text-kos-text">
            Team Betting Outlook
          </h2>
          <p className="mt-1 text-sm text-kos-text/70">
            Projected wins and futures probabilities for market framing.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0">
              <thead>
                <tr>
                  {[
                    "Team",
                    "Expected W",
                    "P10-P90",
                    "Playoff",
                    "Division",
                    "Super Bowl",
                  ].map((label) => (
                    <th
                      key={label}
                      className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65"
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {teamRows.slice(0, 24).map((row) => (
                  <tr key={row.team} className="odd:bg-white/3">
                    <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-text">
                      {row.team}
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                      {row.expectedWins.toFixed(2)}
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                      {row.winsP10}-{row.winsP90}
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                      {percentage(row.playoffProb, 2)}
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                      {percentage(row.divisionTitleProb, 2)}
                    </td>
                    <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-gold">
                      {percentage(row.superBowlWinProb, 2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
          <h2 className="text-xl font-semibold text-kos-text">
            {phase === "playoff"
              ? "Playoff Fantasy Totals"
              : "Regular Season Fantasy Totals"}
          </h2>
          <p className="mt-1 text-sm text-kos-text/70">
            Use totals to compare volume tiers for draft, props, and ladder
            ideas.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0">
              <thead>
                <tr>
                  {[
                    "Player",
                    "Tm",
                    "Pos",
                    "Games",
                    "Yards",
                    "Rec",
                    "TDs",
                    "ATD",
                  ].map((label) => (
                    <th
                      key={label}
                      className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65"
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {players.slice(0, 40).map((row) => {
                  const touchdowns =
                    row.passTdsTotal + row.rushTdsTotal + row.recTdsTotal;
                  return (
                    <tr
                      key={`${row.playerKey}-${row.team}`}
                      className="odd:bg-white/3"
                    >
                      <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-text">
                        {row.playerName}
                      </td>
                      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                        {row.team}
                      </td>
                      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                        {row.position}
                      </td>
                      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                        {row.gamesProjected}
                      </td>
                      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-gold">
                        {totalYards(row).toFixed(1)}
                      </td>
                      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                        {row.receptionsTotal.toFixed(1)}
                      </td>
                      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                        {touchdowns.toFixed(1)}
                      </td>
                      <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                        {row.anytimeTdProbTotal.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/25 p-4 text-sm text-kos-text/75">
        <p>
          Sanity checks: SB sum{" "}
          {bundle.qualityChecks.sumSuperBowlProb?.toFixed(4) ?? "n/a"} ·
          Division sum{" "}
          {bundle.qualityChecks.sumDivisionTitleProb?.toFixed(4) ?? "n/a"} ·
          Playoff sum {bundle.qualityChecks.sumPlayoffProb?.toFixed(4) ?? "n/a"}
        </p>
      </section>
    </main>
  );
}
