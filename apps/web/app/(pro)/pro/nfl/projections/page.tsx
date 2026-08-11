import Link from "next/link";
import AutoSubmitForm from "@/components/pro/AutoSubmitForm";
import {
  CurrentYtdHint,
  PlayerFutureColumnHeaders,
  PlayerFutureTripleCell,
} from "@/components/pro/nfl/PlayerFutureTripleColumns";
import {
  loadLatestNflPreseasonBundle2026,
  type PlayerProjectionTotalsRow,
  type TeamProjectionRow,
} from "@/lib/nfl-preseason-artifacts";
import {
  loadNflProjectionActualsAsync,
  playerActualsFor,
  teamActualWins,
} from "@/lib/nfl-projection-actuals";
import {
  formatCurrentOdds,
  formatCurrentYtd,
  formatProjectedValue,
  sumNullable,
} from "@/lib/nfl-player-futures";
import {
  leaderOddsForPlayer,
  loadNflFuturesOdds,
  superBowlOddsForTeam,
  type NflFuturesOddsBundle,
} from "@/lib/nfl-futures-odds";

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

function totalTds(player: PlayerProjectionTotalsRow): number {
  return player.passTdsTotal + player.rushTdsTotal + player.recTdsTotal;
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
    sortable.sort((a, b) => totalTds(b) - totalTds(a));
    return sortable;
  }
  if (key === "receptions") {
    sortable.sort((a, b) => b.receptionsTotal - a.receptionsTotal);
    return sortable;
  }
  sortable.sort((a, b) => totalYards(b) - totalYards(a));
  return sortable;
}

type PlayerRaceKey = "yards" | "tds" | "receptions";

function playerRaceMeta(key: string): {
  id: PlayerRaceKey;
  title: string;
  unit: string;
  digits: number;
  projectedOf: (row: PlayerProjectionTotalsRow) => number;
  currentOf: (
    a: ReturnType<typeof playerActualsFor>,
  ) => number | null;
} {
  if (key === "tds") {
    return {
      id: "tds",
      title: "TD leaders",
      unit: "TDs",
      digits: 1,
      projectedOf: totalTds,
      currentOf: (a) => sumNullable(a.passTds, a.rushTds, a.recTds),
    };
  }
  if (key === "receptions") {
    return {
      id: "receptions",
      title: "Reception leaders",
      unit: "rec",
      digits: 0,
      projectedOf: (row) => row.receptionsTotal,
      currentOf: (a) => a.receptions,
    };
  }
  return {
    id: "yards",
    title: "Yardage leaders",
    unit: "yds",
    digits: 0,
    projectedOf: totalYards,
    currentOf: (a) =>
      sumNullable(a.passYards, a.rushYards, a.receivingYards),
  };
}

export default async function NflProjectionsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const bundle = loadLatestNflPreseasonBundle2026();
  const [actuals, oddsBundle] = await Promise.all([
    loadNflProjectionActualsAsync(2026),
    loadNflFuturesOdds(),
  ]);
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

  const tabRaw = (firstValue(search.tab) ?? "team").toLowerCase();
  const tab = tabRaw === "player" ? "player" : "team";
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

  const race = playerRaceMeta(playerSort);
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
              2026 Futures · Research desk
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Futures
            </h1>
            <p className="mt-3 text-sm text-kos-text/80 sm:text-base">
              Team and player futures from the Kos Edge sim — every player
              future row shows Projected · Current (2026 YTD) · Current odds.
            </p>
            <p className="mt-2 text-xs text-kos-text/65">
              Source: {bundle.bundleDirName}
              {bundle.generatedAtUtc
                ? ` • Generated ${new Date(bundle.generatedAtUtc).toLocaleString()}`
                : ""}
              {actuals.asOfUtc
                ? ` • Actuals as of ${new Date(actuals.asOfUtc).toLocaleString()}`
                : " • Actuals: awaiting Week 1+"}
              {oddsBundle.asOfUtc
                ? ` • Odds as of ${new Date(oddsBundle.asOfUtc).toLocaleString()}`
                : ""}
            </p>
            <CurrentYtdHint className="mt-1" />
          </div>
          <div className="grid gap-2 sm:min-w-48">
            <Link
              href="/pro/nfl/overview"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              NFL Overview
            </Link>
            <Link
              href="/edge-board/nfl"
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
            >
              Edge Board →
            </Link>
            <Link
              href="/pro/nfl/awards"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/40"
            >
              Awards
            </Link>
          </div>
        </div>
        <nav className="mt-5 flex flex-wrap gap-2" aria-label="Futures tabs">
          <Link
            href="/pro/nfl/projections?tab=team"
            className={
              tab === "team"
                ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            Team
          </Link>
          <Link
            href="/pro/nfl/projections?tab=player"
            className={
              tab === "player"
                ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                : "rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-kos-text/70"
            }
          >
            Player
          </Link>
        </nav>
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
            {percentage(favorite?.superBowlWinProb ?? 0, 2)} proj ·{" "}
            {formatCurrentOdds(
              favorite
                ? superBowlOddsForTeam(oddsBundle, favorite.team)
                : null,
            )}{" "}
            odds
          </p>
        </article>
        <article className="rounded-2xl border border-white/10 bg-black/30 p-4">
          <p className="text-xs uppercase tracking-wide text-kos-text/60">
            Wins Leader (Projected)
          </p>
          <p className="mt-2 text-2xl font-semibold text-kos-text">
            {winsLeader?.team ?? "N/A"}
          </p>
          <p className="text-sm text-kos-gold">
            {formatProjectedValue(winsLeader?.expectedWins ?? 0, {
              digits: 2,
            })}{" "}
            proj ·{" "}
            {formatCurrentYtd(
              winsLeader ? teamActualWins(actuals, winsLeader.team) : null,
              "counting",
              0,
            )}{" "}
            current
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
            {formatProjectedValue(
              fantasyLeader ? totalYards(fantasyLeader) : 0,
              { digits: 0, unit: "yds" },
            )}{" "}
            ·{" "}
            {formatCurrentYtd(
              fantasyLeader
                ? sumNullable(
                    playerActualsFor(actuals, fantasyLeader.playerKey)
                      .passYards,
                    playerActualsFor(actuals, fantasyLeader.playerKey)
                      .rushYards,
                    playerActualsFor(actuals, fantasyLeader.playerKey)
                      .receivingYards,
                  )
                : null,
              "counting",
              0,
            )}{" "}
            current
          </p>
        </article>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <AutoSubmitForm
          action="/pro/nfl/projections"
          className="grid gap-3 md:grid-cols-2 xl:grid-cols-6"
        >
          <input type="hidden" name="tab" value={tab} />
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
            Player race
            <select
              name="playerSort"
              defaultValue={playerSort}
              className="mt-1 w-full rounded-lg border border-white/15 bg-black/40 p-2 text-sm"
            >
              <option value="yards">Yardage leaders</option>
              <option value="tds">TD leaders</option>
              <option value="receptions">Reception leaders</option>
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
        </AutoSubmitForm>
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-2">
        {tab === "team" ? (
          <TeamFuturesBoard
            rows={teamRows.slice(0, 32)}
            actuals={actuals}
            oddsBundle={oddsBundle}
          />
        ) : null}

        {tab === "player" ? (
          <PlayerFuturesBoard
            title={`Player · ${race.title}`}
            subtitle={`${phase === "playoff" ? "Playoff" : "Regular season"} ${race.unit} — Projected · Current (2026 YTD) · Current odds.`}
            race={race}
            rows={players.slice(0, 40)}
            actuals={actuals}
            oddsBundle={oddsBundle}
          />
        ) : null}
      </section>

      <p className="mt-4 text-[11px] text-kos-text/40">{oddsBundle.note}</p>
    </main>
  );
}

function TeamFuturesBoard({
  rows,
  actuals,
  oddsBundle,
}: {
  rows: TeamProjectionRow[];
  actuals: Awaited<ReturnType<typeof loadNflProjectionActualsAsync>>;
  oddsBundle: NflFuturesOddsBundle;
}) {
  return (
    <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5 xl:col-span-2">
      <h2 className="text-xl font-semibold text-kos-text">
        Team · Wins / Div / Conf / SB
      </h2>
      <p className="mt-1 text-sm text-kos-text/70">
        Wins use Projected · Current · odds (odds — until win-total markets
        join). Super Bowl column joins best available SB winner price.
      </p>
      <CurrentYtdHint className="mt-1" />
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-0">
          <thead>
            <tr>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                Team
              </th>
              <PlayerFutureColumnHeaders projectedLabel="Wins (proj)" />
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                P10-P90
              </th>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                Playoff
              </th>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                Division
              </th>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                SB proj
              </th>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                SB odds
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const sbOdds = superBowlOddsForTeam(oddsBundle, row.team);
              return (
                <tr key={row.team} className="odd:bg-white/3">
                  <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-text">
                    {row.team}
                  </td>
                  <PlayerFutureTripleCell
                    projected={row.expectedWins}
                    current={teamActualWins(actuals, row.team)}
                    currentKind="counting"
                    odds={null}
                    projectedDigits={1}
                    projectedSubLabel="wins"
                  />
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
                  <td className="border-b border-white/5 px-3 py-2 text-sm tabular-nums text-kos-text/85">
                    {formatCurrentOdds(sbOdds)}
                    {sbOdds?.book ? (
                      <div className="text-[11px] text-kos-text/45">
                        {sbOdds.book}
                      </div>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </article>
  );
}

function PlayerFuturesBoard({
  title,
  subtitle,
  race,
  rows,
  actuals,
  oddsBundle,
}: {
  title: string;
  subtitle: string;
  race: ReturnType<typeof playerRaceMeta>;
  rows: PlayerProjectionTotalsRow[];
  actuals: Awaited<ReturnType<typeof loadNflProjectionActualsAsync>>;
  oddsBundle: NflFuturesOddsBundle;
}) {
  return (
    <article className="rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5 xl:col-span-2">
      <h2 className="text-xl font-semibold text-kos-text">{title}</h2>
      <p className="mt-1 text-sm text-kos-text/70">{subtitle}</p>
      <CurrentYtdHint className="mt-1" />

      {/* Mobile cards */}
      <ol className="mt-4 space-y-3 sm:hidden">
        {rows.map((row, index) => {
          const a = playerActualsFor(actuals, row.playerKey);
          const odds = leaderOddsForPlayer(oddsBundle, row.playerKey);
          return (
            <li
              key={`${row.playerKey}-${row.team}`}
              className="rounded-xl border border-white/10 bg-white/3 p-3"
            >
              <div className="flex items-baseline justify-between gap-2">
                <p className="font-semibold text-kos-text">
                  <span className="text-kos-gold">#{index + 1}</span>{" "}
                  {row.playerName}
                </p>
                <span className="text-[11px] text-kos-text/55">
                  {row.team} · {row.position}
                </span>
              </div>
              <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
                <div>
                  <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
                    Projected
                  </dt>
                  <dd className="mt-0.5 text-sm font-semibold tabular-nums text-kos-gold">
                    {formatProjectedValue(race.projectedOf(row), {
                      digits: race.digits,
                      unit: race.unit,
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
                    Current
                  </dt>
                  <dd className="mt-0.5 text-sm tabular-nums text-kos-text/85">
                    {formatCurrentYtd(race.currentOf(a), "counting", race.digits)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
                    Odds
                  </dt>
                  <dd className="mt-0.5 text-sm tabular-nums text-kos-text/85">
                    {formatCurrentOdds(odds)}
                  </dd>
                </div>
              </dl>
            </li>
          );
        })}
      </ol>

      {/* Desktop */}
      <div className="mt-4 hidden overflow-x-auto sm:block">
        <table className="min-w-full border-separate border-spacing-0">
          <thead>
            <tr>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                #
              </th>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                Player
              </th>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                Tm
              </th>
              <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
                Pos
              </th>
              <PlayerFutureColumnHeaders
                projectedLabel="Projected"
                projectedTitle={`Season ${race.unit}`}
              />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const a = playerActualsFor(actuals, row.playerKey);
              const odds = leaderOddsForPlayer(oddsBundle, row.playerKey);
              return (
                <tr
                  key={`${row.playerKey}-${row.team}`}
                  className="odd:bg-white/3"
                >
                  <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-gold">
                    {index + 1}
                  </td>
                  <td className="border-b border-white/5 px-3 py-2 text-sm font-semibold text-kos-text">
                    {row.playerName}
                  </td>
                  <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                    {row.team}
                  </td>
                  <td className="border-b border-white/5 px-3 py-2 text-sm text-kos-text/85">
                    {row.position}
                  </td>
                  <PlayerFutureTripleCell
                    projected={race.projectedOf(row)}
                    current={race.currentOf(a)}
                    currentKind="counting"
                    odds={odds}
                    projectedDigits={race.digits}
                    currentDigits={race.digits}
                    projectedUnit={race.unit}
                  />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </article>
  );
}
