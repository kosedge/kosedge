import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import { fetchNbaPropsBoard } from "@/lib/nba-props-board";
import { fetchNhlPropsBoard } from "@/lib/nhl-props-board";
import { fetchWnbaPropsBoard } from "@/lib/wnba-props-board";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  resolveSportKey,
  sportDisplayLabel,
  supportsPropsFantasy,
} from "@/lib/sports";

const SPORT_PROPS_COPY: Record<string, string> = {
  nba: "NBA player props from PlayerProjection (Ch5) vs trusted Best. Chapter 6 dark — proj, Best, edge, σ; zero PLAY / LEAN.",
  nhl: "NHL player props from PlayerProjection (Ch5) vs trusted Best. Chapter 6 dark — proj, Best, edge, σ; zero PLAY / LEAN. Odds-backed goals/assists/pts/sog; starter-unknown goalie SAVES stay —.",
  wnba: "WNBA player props from PlayerProjection (Ch5) vs trusted Best. Chapter 6 dark — proj, Best, edge, σ; zero PLAY / LEAN. Odds-backed pts/reb/ast/threes only.",
  mlb: "MLB props models exist server-side; play-stake eligibility stays gated off for soft launch. Use Fair Lines and Edges for game-level research.",
  cfb: "College football props remain data-pending for soft launch.",
  ncaam: "College basketball props remain data-pending for soft launch.",
};

export default async function PropsPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  if (sportKey === "nfl") redirect("/pro/nfl/props");
  // College sports: no props desk — send researchers to Tempo / Fair Lines.
  if (sportKey === "ncaam" || sportKey === "cfb") {
    redirect(`/pro/${sportKey}/tempo`);
  }

  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;
  const desk = getSportDeskConfig(sportKey);
  const propsEnabled = supportsPropsFantasy(sportKey);
  const detail =
    (sportKey ? SPORT_PROPS_COPY[sportKey] : undefined) ??
    `${sportName} props are staged for this hub pending model feed validation.`;

  const boardGames =
    sportKey === "mlb" ||
    sportKey === "nba" ||
    sportKey === "wnba" ||
    sportKey === "nhl"
      ? []
      : await getTonightGames(sportKey || "nba");
  const mlbBoard = sportKey === "mlb" ? await fetchMlbFairLines() : null;
  const nbaBoard =
    sportKey === "nba" ? await fetchNbaPropsBoard({ limit: 120 }) : null;
  const wnbaBoard =
    sportKey === "wnba" ? await fetchWnbaPropsBoard({ limit: 120 }) : null;
  const nhlBoard =
    sportKey === "nhl" ? await fetchNhlPropsBoard({ limit: 120 }) : null;

  return (
    <SportHubShell
      sportKey={sportKey}
      sportName={sportName}
      base={base}
      badge={`${sportName} Betting Desk`}
      title={`${sportName} Props`}
      summary={
        propsEnabled
          ? `Prop analyzer and edge screens for ${sportName}. Desk path: ${desk.pathLabel}. Research only — you make the picks.`
          : `Props are not part of this sport’s soft-launch desk.`
      }
      primaryHref={`/edge-board/${sportKey}`}
      primaryLabel="Open edge board →"
      secondaryHref="/pro/props-center"
      secondaryLabel="Props center →"
    >
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-6 sm:p-8">
        <p className="text-sm font-semibold text-kos-gold">
          {sportKey === "nba"
            ? "NBA props dark board (Ch6)"
            : sportKey === "wnba"
              ? "WNBA props dark board (Ch6)"
              : sportKey === "nhl"
                ? "NHL props dark board (Ch6)"
                : propsEnabled
                  ? "Props board pending"
                  : "Coming soon"}
        </p>
        <p className="mt-2 text-sm text-kos-text/70 sm:text-base">{detail}</p>
        {sportKey === "mlb" && mlbBoard ? (
          <p className="mt-3 text-sm text-kos-text/60">
            {mlbBoard.count > 0
              ? `${mlbBoard.count} MLB fair-line games available for game-level research (${mlbBoard.modelVersion || "model"}). Player props stay research-gated — no invented prop cards.`
              : "No MLB fair-line games on the model board for this date yet."}
          </p>
        ) : null}
        {sportKey === "nba" && nbaBoard ? (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-kos-text/60">
              {nbaBoard.error
                ? `Board unavailable: ${nbaBoard.error}`
                : nbaBoard.count > 0
                  ? `${nbaBoard.count} prop rows · ${nbaBoard.modelVersion} · dark (zero PLAY / LEAN) · PlayerProjection means`
                  : nbaBoard.message ||
                    "No Ch6 dark prop rows yet — PlayerProjection pack required."}
            </p>
            {nbaBoard.phase === "ch6_dark" || nbaBoard.darkOnly ? (
              <p className="text-xs text-kos-text/50">
                Tags: PASS only · Best cleared when untrusted · edge = proj −
                Best
              </p>
            ) : nbaBoard.ouBalance ? (
              <p className="text-xs text-kos-text/50">
                PLAY balance: {nbaBoard.ouBalance.play_over ?? 0} Over /{" "}
                {nbaBoard.ouBalance.play_under ?? 0} Under
                {nbaBoard.ouBalance.play_under_pct != null
                  ? ` (${Math.round(nbaBoard.ouBalance.play_under_pct * 100)}% Under)`
                  : ""}
                {nbaBoard.ouBalance.balanced === false
                  ? " · imbalance flag"
                  : ""}
              </p>
            ) : null}
            {nbaBoard.lines.length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-white/5 text-xs uppercase tracking-wide text-kos-text/50">
                    <tr>
                      <th className="px-3 py-2">Player</th>
                      <th className="px-3 py-2">Mkt</th>
                      <th className="px-3 py-2">Proj</th>
                      <th className="px-3 py-2">Best</th>
                      <th className="px-3 py-2">Edge</th>
                      <th className="px-3 py-2">σ</th>
                      <th className="px-3 py-2">Tag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nbaBoard.lines.slice(0, 40).map((row) => (
                      <tr
                        key={`${row.playerId}-${row.marketKey}`}
                        className="border-t border-white/5"
                      >
                        <td className="px-3 py-2">
                          <div className="font-medium text-kos-text">
                            {row.playerName}
                          </div>
                          <div className="text-xs text-kos-text/45">
                            {row.team}
                          </div>
                        </td>
                        <td className="px-3 py-2 uppercase text-kos-text/70">
                          {row.marketKey}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/80">
                          {row.modelMean?.toFixed(1) ?? "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/70">
                          {row.best != null ? row.best.toFixed(1) : "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/70">
                          {row.edge != null
                            ? `${row.edge > 0 ? "+" : ""}${row.edge.toFixed(1)}`
                            : "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/50">
                          {row.modelStd?.toFixed(1) ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-kos-gold">PASS</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
        {sportKey === "wnba" && wnbaBoard ? (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-kos-text/60">
              {wnbaBoard.error
                ? `Board unavailable: ${wnbaBoard.error}`
                : wnbaBoard.count > 0
                  ? `${wnbaBoard.count} prop rows · ${wnbaBoard.modelVersion} · dark (zero PLAY / LEAN) · PlayerProjection means`
                  : wnbaBoard.message ||
                    "No Ch6 dark prop rows yet — PlayerProjection pack required."}
            </p>
            {wnbaBoard.phase === "ch6_dark" || wnbaBoard.darkOnly ? (
              <p className="text-xs text-kos-text/50">
                Tags: PASS only · Best cleared when untrusted · edge = proj −
                Best · PRA/PR/RA missing (Odds has no key)
              </p>
            ) : null}
            {wnbaBoard.lines.length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-white/5 text-xs uppercase tracking-wide text-kos-text/50">
                    <tr>
                      <th className="px-3 py-2">Player</th>
                      <th className="px-3 py-2">Mkt</th>
                      <th className="px-3 py-2">Proj</th>
                      <th className="px-3 py-2">Best</th>
                      <th className="px-3 py-2">Edge</th>
                      <th className="px-3 py-2">σ</th>
                      <th className="px-3 py-2">Tag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wnbaBoard.lines.slice(0, 40).map((row) => (
                      <tr
                        key={`${row.playerId}-${row.marketKey}`}
                        className="border-t border-white/5"
                      >
                        <td className="px-3 py-2">
                          <div className="font-medium text-kos-text">
                            {row.playerName}
                          </div>
                          <div className="text-xs text-kos-text/45">
                            {row.team}
                          </div>
                        </td>
                        <td className="px-3 py-2 uppercase text-kos-text/70">
                          {row.marketKey}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/80">
                          {row.modelMean?.toFixed(1) ?? "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/70">
                          {row.best != null ? row.best.toFixed(1) : "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/70">
                          {row.edge != null
                            ? `${row.edge > 0 ? "+" : ""}${row.edge.toFixed(1)}`
                            : "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/50">
                          {row.modelStd?.toFixed(1) ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-kos-gold">PASS</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
        {sportKey === "nhl" && nhlBoard ? (
          <div className="mt-4 space-y-3">
            <p className="text-sm text-kos-text/60">
              {nhlBoard.error
                ? `Board unavailable: ${nhlBoard.error}`
                : nhlBoard.count > 0
                  ? `${nhlBoard.count} prop rows · ${nhlBoard.modelVersion} · dark (zero PLAY / LEAN) · PlayerProjection means`
                  : nhlBoard.message ||
                    "No Ch6 dark prop rows yet — PlayerProjection pack required."}
            </p>
            {nhlBoard.phase === "ch6_dark" || nhlBoard.darkOnly ? (
              <p className="text-xs text-kos-text/50">
                Tags: PASS only · Best cleared when untrusted · starter-unknown
                goalie SAVES stay — · edge = proj − Best · Odds-backed
                goals/assists/pts/sog
              </p>
            ) : null}
            {nhlBoard.lines.length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-white/10">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-white/5 text-xs uppercase tracking-wide text-kos-text/50">
                    <tr>
                      <th className="px-3 py-2">Player</th>
                      <th className="px-3 py-2">Mkt</th>
                      <th className="px-3 py-2">Proj</th>
                      <th className="px-3 py-2">Best</th>
                      <th className="px-3 py-2">Edge</th>
                      <th className="px-3 py-2">σ</th>
                      <th className="px-3 py-2">Tag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nhlBoard.lines.slice(0, 40).map((row) => (
                      <tr
                        key={`${row.playerId}-${row.marketKey}-${row.playerType}`}
                        className="border-t border-white/5"
                      >
                        <td className="px-3 py-2">
                          <div className="font-medium text-kos-text">
                            {row.playerName}
                          </div>
                          <div className="text-xs text-kos-text/45">
                            {row.team}
                            {row.playerType === "goalie" ? " · G" : ""}
                          </div>
                        </td>
                        <td className="px-3 py-2 uppercase text-kos-text/70">
                          {row.marketKey}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/80">
                          {row.modelMean?.toFixed(1) ?? "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/70">
                          {row.best != null ? row.best.toFixed(1) : "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/70">
                          {row.edge != null
                            ? `${row.edge > 0 ? "+" : ""}${row.edge.toFixed(1)}`
                            : "—"}
                        </td>
                        <td className="px-3 py-2 tabular-nums text-kos-text/50">
                          {row.modelStd?.toFixed(1) ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-kos-gold">PASS</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
        <p className="mt-4 text-sm text-kos-text/60">
          NFL props are live under the NFL hub. This surface stays
          sport-specific — it will not redirect you into NFL language or
          markets.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href={
              sportKey === "mlb" ? "/pro/mlb/fair-lines" : `${base}/fair-lines`
            }
            className="inline-flex rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
          >
            Fair lines path →
          </Link>
          <Link
            href={`${base}/overview`}
            className="inline-flex rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text transition hover:border-kos-gold/35"
          >
            Hub overview →
          </Link>
        </div>
      </div>

      {boardGames.length > 0 ? (
        <section className="mt-6">
          <h2 className="text-lg font-semibold text-kos-text">
            Slate context (not props)
          </h2>
          <p className="mt-1 text-sm text-kos-text/65">
            Live board matchups while player-prop feeds finish validation. No
            fabricated prop numbers.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {boardGames.slice(0, 9).map((g) => (
              <div
                key={g.slug}
                className="rounded-xl border border-white/10 bg-black/35 p-4"
              >
                <div className="text-sm font-semibold text-kos-text">
                  {g.row.teamA?.name ?? "Away"} @ {g.row.teamB?.name ?? "Home"}
                </div>
                <p className="mt-2 text-xs text-kos-text/60">
                  Total{" "}
                  {g.row.bestOU?.top?.label ?? g.row.keiOU?.top?.label ?? "—"}
                </p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {sportKey === "mlb" && mlbBoard && mlbBoard.lines.length > 0 ? (
        <section className="mt-6">
          <h2 className="text-lg font-semibold text-kos-text">
            Game slate (fair lines)
          </h2>
          <p className="mt-1 text-sm text-kos-text/65">
            Model game baselines — use Fair Lines / Run Line desks for depth.
            Props stay gated.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {mlbBoard.lines.slice(0, 9).map((line) => (
              <Link
                key={line.gameId}
                href="/pro/mlb/fair-lines"
                className="rounded-xl border border-white/10 bg-black/35 p-4 transition hover:border-kos-gold/40"
              >
                <div className="text-sm font-semibold text-kos-text">
                  {line.awayTeam} @ {line.homeTeam}
                </div>
                <p className="mt-2 text-xs text-kos-text/60">
                  Fair total{" "}
                  <span className="tabular-nums text-kos-gold">
                    {line.fairTotal ?? line.totalMean ?? "—"}
                  </span>
                </p>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </SportHubShell>
  );
}
