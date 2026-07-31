import Link from "next/link";
import { redirect } from "next/navigation";
import SportHubShell from "@/components/pro/SportHubShell";
import { getTonightGames } from "@/lib/edge-board-tonight";
import { fetchMlbFairLines } from "@/lib/mlb-fair-lines";
import { getSportDeskConfig } from "@/lib/pro-sport-desk";
import {
  resolveSportKey,
  sportDisplayLabel,
  supportsPropsFantasy,
} from "@/lib/sports";

const SPORT_PROPS_COPY: Record<string, string> = {
  nba: "NBA player props (points, rebounds, assists, threes) stage here once a validated props board exists. Odds mainlines restore when the NBA board posts — no invented prop cards.",
  nhl: "NHL skater and goalie props stage here once shot and save feeds clear validation. Game slate below is market context only.",
  wnba: "WNBA player props stage here once usage feeds clear validation. Live game slate below is market context from Odds — not player-prop numbers.",
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
    sportKey === "mlb" ? [] : await getTonightGames(sportKey || "nba");
  const mlbBoard =
    sportKey === "mlb" ? await fetchMlbFairLines() : null;

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
          {propsEnabled ? "Props board pending" : "Coming soon"}
        </p>
        <p className="mt-2 text-sm text-kos-text/70 sm:text-base">{detail}</p>
        {sportKey === "mlb" && mlbBoard ? (
          <p className="mt-3 text-sm text-kos-text/60">
            {mlbBoard.count > 0
              ? `${mlbBoard.count} MLB fair-line games available for game-level research (${mlbBoard.modelVersion || "model"}). Player props stay research-gated — no invented prop cards.`
              : "No MLB fair-line games on the model board for this date yet."}
          </p>
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
