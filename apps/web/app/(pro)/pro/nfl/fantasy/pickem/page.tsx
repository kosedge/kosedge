import Link from "next/link";
import { HonestStatusBanner } from "@/components/pro/HonestStatusBanner";
import ModelTransparencyLink from "@/components/pro/ModelTransparencyLink";
import { FantasyDeskNav } from "@/components/pro/nfl/fantasy/FantasyDeskNav";
import {
  fetchNflFairLines,
  formatKickoff,
  formatSpread,
  formatWinProb,
} from "@/lib/nfl-fair-lines";
import {
  buildNflAtsPickemCard,
  buildNflPickemCard,
  filterPickemWeekLines,
  PICKEM_REG_WEEK_CHIPS,
  parsePickemTab,
  resolvePickemDefaultWeek,
  type NflAtsPickemPick,
  type NflPickemPick,
  type NflPickemTab,
  type NflPickemTag,
} from "@/lib/nfl-pickem";
import {
  honestEmptySlateCopy,
  modelUnreachableCopy,
  shouldShowModelUnreachableBanner,
} from "@/lib/model-service-status";
import {
  fetchNflProductionReadiness,
  readinessBlocksPlay,
} from "@/lib/nfl-production-readiness";

export const dynamic = "force-dynamic";

const DEFAULT_SEASON = 2026;

type SearchValue = string | string[] | undefined;

function firstValue(value: SearchValue): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

function parseWeek(raw: string | undefined, fallback: number): number {
  const n = Number(raw);
  if (!Number.isFinite(n) || n < 1 || n > 22) return fallback;
  return Math.floor(n);
}

function tagChipClass(tag: "PLAY" | "LEAN", researchOnly: boolean): string {
  if (researchOnly) {
    return "border-white/20 bg-white/5 text-kos-text/70";
  }
  if (tag === "PLAY") {
    return "border-edge-green/40 bg-edge-green/10 text-edge-green";
  }
  return "border-kos-gold/40 bg-kos-gold/10 text-kos-gold";
}

function displayTag(tag: NflPickemTag): "PLAY" | "LEAN" | null {
  if (tag === "PLAY" || tag === "LEAN") return tag;
  return null;
}

function pickemHref(tab: NflPickemTab, week: number): string {
  return `/pro/nfl/fantasy/pickem?tab=${tab}&week=${week}`;
}

function formatAtsEdge(edge: number | null): string {
  if (edge == null || !Number.isFinite(edge)) return "—";
  const abs = Math.abs(Math.round(edge * 100) / 100);
  return abs.toFixed(2);
}

export default async function NflFantasyPickemPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, SearchValue>>;
}) {
  const search = await searchParams;
  const tab = parsePickemTab(firstValue(search.tab));
  const [board, readiness] = await Promise.all([
    // Match nfl-slate / working Edge Board window — 200d cold-loads time out.
    fetchNflFairLines({
      season: DEFAULT_SEASON,
      daysAhead: 120,
      includePastDays: 2,
    }),
    fetchNflProductionReadiness(),
  ]);

  const defaultWeek = resolvePickemDefaultWeek(board.lines, board.currentWeek);
  const week = parseWeek(firstValue(search.week), defaultWeek);
  const weekLines = filterPickemWeekLines(board.lines, week, {
    seasonType: "REG",
  });
  const suCard = buildNflPickemCard(weekLines);
  const atsCard = buildNflAtsPickemCard(weekLines);
  const card = tab === "su" ? suCard : atsCard;
  const researchOnlyTags = readinessBlocksPlay(readiness);
  const weekChips = PICKEM_REG_WEEK_CHIPS;
  const boardHasLines = board.lines.length > 0;
  const modelUnreachable =
    Boolean(board.error?.trim()) && !boardHasLines && card.length === 0;
  const weekFilterEmpty =
    !board.error && boardHasLines && weekLines.length === 0;
  const emptyHonest =
    !board.error &&
    !boardHasLines &&
    card.length === 0 &&
    board.slateStatus &&
    board.slateStatus !== "ok";

  const subtitle =
    tab === "ats"
      ? "Weekly ATS card ranked 1–N. PLAY / LEAN first; fill the rest vs the stake line."
      : "Weekly straight-up card ranked 1–N. PLAY / LEAN first; fill the rest of the slate.";

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="rounded-2xl border border-kos-gold/20 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Fantasy · Pick’em
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              Pick’em
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              {subtitle}
            </p>
            <p className="mt-2 text-xs text-kos-text/55">
              Week {week} · REG · {tab === "ats" ? "ATS" : "Straight up"} · rank
              is research order, not a stake
            </p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-44">
            <Link
              href="/pro/nfl/fantasy"
              className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
            >
              Draft Desk →
            </Link>
            <Link
              href="/pro/nfl/fantasy/sleepers"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text hover:border-kos-gold/35"
            >
              Sleepers
            </Link>
          </div>
        </div>
        <div className="mt-5">
          <FantasyDeskNav
            active="rankings"
            scoring="half_ppr"
            researchActive="pickem"
          />
        </div>
        <div className="mt-3">
          <ModelTransparencyLink hrefSuffix="#pickem" />
        </div>
      </section>

      {shouldShowModelUnreachableBanner({
        error: board.error,
        // Board rows mean the slate loaded — an empty week filter is not an outage.
        hasContent: boardHasLines || card.length > 0,
        slateStatus: board.slateStatus,
      }) ? (
        <div className="mt-6">
          <HonestStatusBanner title="Model unreachable" tone="amber">
            <p>{modelUnreachableCopy(board.error)}</p>
          </HonestStatusBanner>
        </div>
      ) : null}

      {emptyHonest ? (
        <div className="mt-6">
          <HonestStatusBanner title="Empty slate" tone="neutral">
            <p>{honestEmptySlateCopy(board.slateStatus)}</p>
          </HonestStatusBanner>
        </div>
      ) : null}

      {researchOnlyTags ? (
        <div className="mt-6">
          <HonestStatusBanner title="PLAY tags research-only" tone="sky">
            <p>
              Production readiness is no-go — PLAY / LEAN here are sort labels
              for the research card, not live stakes.
            </p>
          </HonestStatusBanner>
        </div>
      ) : null}

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <nav className="flex flex-wrap gap-2" aria-label="Pick’em card">
            {(
              [
                { id: "ats" as const, label: "ATS" },
                { id: "su" as const, label: "Straight up" },
              ] as const
            ).map((item) => {
              const isActive = item.id === tab;
              return (
                <Link
                  key={item.id}
                  href={pickemHref(item.id, week)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                    isActive
                      ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                      : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25 hover:text-kos-text"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <p className="text-xs text-kos-text/55">
            {card.length > 0
              ? `${card.length} game${card.length === 1 ? "" : "s"} · ranks 1–${card.length}`
              : modelUnreachable
                ? "Waiting on fair lines"
                : `No REG lines for Week ${week} yet`}
          </p>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <nav className="flex flex-wrap gap-2" aria-label="Pick’em week">
            {weekChips.map((w) => {
              const isActive = w === week;
              return (
                <Link
                  key={w}
                  href={pickemHref(tab, w)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                    isActive
                      ? "border border-kos-gold/45 bg-kos-gold/20 text-kos-gold"
                      : "border border-white/10 bg-white/5 text-kos-text/75 hover:border-kos-gold/25 hover:text-kos-text"
                  }`}
                >
                  Week {w}
                </Link>
              );
            })}
          </nav>
        </div>

        {weekFilterEmpty && !emptyHonest ? (
          <div className="mt-4">
            <HonestStatusBanner
              title="No lines for this week yet"
              tone="neutral"
            >
              <p>
                No REG lines for Week {week} yet. Near-term weeks may already be
                on the board — try Week {defaultWeek} or check back when
                fair-lines posts this slate.
              </p>
            </HonestStatusBanner>
          </div>
        ) : null}

        {card.length === 0 &&
        !board.error &&
        !boardHasLines &&
        !emptyHonest &&
        !weekFilterEmpty ? (
          <div className="mt-4">
            <HonestStatusBanner title="No pick’em slate yet" tone="neutral">
              <p>
                No REG lines for Week {week} yet. Switch weeks or check back
                when the fair-lines board posts the slate.
              </p>
            </HonestStatusBanner>
          </div>
        ) : null}

        {card.length > 0 && tab === "ats" ? (
          <>
            <div className="mt-4 hidden overflow-x-auto md:block">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                  <tr className="border-b border-white/10">
                    <th className="px-3 py-2 font-semibold">Rank</th>
                    <th className="px-3 py-2 font-semibold">Pick</th>
                    <th className="px-3 py-2 font-semibold">Line</th>
                    <th className="px-3 py-2 font-semibold">KEI</th>
                    <th className="px-3 py-2 font-semibold">Edge</th>
                    <th className="px-3 py-2 font-semibold">Tag</th>
                    <th className="px-3 py-2 font-semibold">Kickoff</th>
                  </tr>
                </thead>
                <tbody>
                  {(card as NflAtsPickemPick[]).map((pick) => (
                    <AtsPickemRow
                      key={pick.gameId}
                      pick={pick}
                      researchOnlyTags={researchOnlyTags}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="mt-4 space-y-3 md:hidden">
              {(card as NflAtsPickemPick[]).map((pick) => (
                <AtsPickemCard
                  key={pick.gameId}
                  pick={pick}
                  researchOnlyTags={researchOnlyTags}
                />
              ))}
            </ul>
          </>
        ) : null}

        {card.length > 0 && tab === "su" ? (
          <>
            <div className="mt-4 hidden overflow-x-auto md:block">
              <table className="min-w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-kos-text/55">
                  <tr className="border-b border-white/10">
                    <th className="px-3 py-2 font-semibold">Rank</th>
                    <th className="px-3 py-2 font-semibold">Pick</th>
                    <th className="px-3 py-2 font-semibold">Opp</th>
                    <th className="px-3 py-2 font-semibold">KEI</th>
                    <th className="px-3 py-2 font-semibold">Win%</th>
                    <th className="px-3 py-2 font-semibold">Tag</th>
                    <th className="px-3 py-2 font-semibold">Kickoff</th>
                  </tr>
                </thead>
                <tbody>
                  {(card as NflPickemPick[]).map((pick) => (
                    <SuPickemRow
                      key={pick.gameId}
                      pick={pick}
                      researchOnlyTags={researchOnlyTags}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="mt-4 space-y-3 md:hidden">
              {(card as NflPickemPick[]).map((pick) => (
                <SuPickemCard
                  key={pick.gameId}
                  pick={pick}
                  researchOnlyTags={researchOnlyTags}
                />
              ))}
            </ul>
          </>
        ) : null}
      </section>
    </main>
  );
}

function SuPickemRow({
  pick,
  researchOnlyTags,
}: {
  pick: NflPickemPick;
  researchOnlyTags: boolean;
}) {
  const tag = displayTag(pick.tag);
  return (
    <tr className="border-b border-white/5 hover:bg-white/5">
      <td className="px-3 py-3 text-2xl font-semibold tabular-nums text-kos-gold">
        {pick.rank}
      </td>
      <td className="px-3 py-3 text-base font-semibold text-kos-text">
        {pick.pickAbbr ?? "—"}
      </td>
      <td className="px-3 py-3 text-kos-text/75">
        {pick.oppAbbr ? `vs ${pick.oppAbbr}` : "—"}
      </td>
      <td className="px-3 py-3 tabular-nums text-kos-text/80">
        {formatSpread(pick.keiSpreadPick)}
      </td>
      <td className="px-3 py-3 tabular-nums text-kos-text/80">
        {formatWinProb(pick.winProb)}
      </td>
      <td className="px-3 py-3">
        {tag ? (
          <span
            className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${tagChipClass(tag, researchOnlyTags)}`}
          >
            {tag}
          </span>
        ) : (
          <span className="text-kos-text/40">—</span>
        )}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {formatKickoff(pick.kickoff)}
      </td>
    </tr>
  );
}

function AtsPickemRow({
  pick,
  researchOnlyTags,
}: {
  pick: NflAtsPickemPick;
  researchOnlyTags: boolean;
}) {
  const tag = displayTag(pick.tag);
  return (
    <tr className="border-b border-white/5 hover:bg-white/5">
      <td className="px-3 py-3 text-2xl font-semibold tabular-nums text-kos-gold">
        {pick.rank}
      </td>
      <td className="px-3 py-3 text-base font-semibold text-kos-text">
        {pick.pickAbbr ?? "—"}
      </td>
      <td className="px-3 py-3 tabular-nums text-kos-text/80">
        {formatSpread(pick.marketSpreadPick)}
      </td>
      <td className="px-3 py-3 tabular-nums text-kos-text/80">
        {formatSpread(pick.keiSpreadPick)}
      </td>
      <td className="px-3 py-3 tabular-nums text-kos-text/80">
        {formatAtsEdge(pick.atsEdge)}
      </td>
      <td className="px-3 py-3">
        {tag ? (
          <span
            className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${tagChipClass(tag, researchOnlyTags)}`}
          >
            {tag}
          </span>
        ) : (
          <span className="text-kos-text/40">—</span>
        )}
      </td>
      <td className="px-3 py-3 text-kos-text/70">
        {formatKickoff(pick.kickoff)}
      </td>
    </tr>
  );
}

function SuPickemCard({
  pick,
  researchOnlyTags,
}: {
  pick: NflPickemPick;
  researchOnlyTags: boolean;
}) {
  const tag = displayTag(pick.tag);
  return (
    <li className="rounded-xl border border-white/10 bg-white/3 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-2xl font-semibold tabular-nums text-kos-gold">
            {pick.rank}
          </p>
          <p className="mt-1 text-base font-semibold text-kos-text">
            {pick.pickAbbr ?? "—"}
            {pick.oppAbbr ? (
              <span className="font-normal text-kos-text/60">
                {" "}
                vs {pick.oppAbbr}
              </span>
            ) : null}
          </p>
          <p className="mt-1 text-xs text-kos-text/55">
            KEI {formatSpread(pick.keiSpreadPick)} ·{" "}
            {formatWinProb(pick.winProb)} · {formatKickoff(pick.kickoff)}
          </p>
        </div>
        {tag ? (
          <span
            className={`shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${tagChipClass(tag, researchOnlyTags)}`}
          >
            {tag}
          </span>
        ) : null}
      </div>
    </li>
  );
}

function AtsPickemCard({
  pick,
  researchOnlyTags,
}: {
  pick: NflAtsPickemPick;
  researchOnlyTags: boolean;
}) {
  const tag = displayTag(pick.tag);
  return (
    <li className="rounded-xl border border-white/10 bg-white/3 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-2xl font-semibold tabular-nums text-kos-gold">
            {pick.rank}
          </p>
          <p className="mt-1 text-base font-semibold text-kos-text">
            {pick.pickAbbr ?? "—"}{" "}
            <span className="font-normal tabular-nums text-kos-text/75">
              {formatSpread(pick.marketSpreadPick)}
            </span>
          </p>
          <p className="mt-1 text-xs text-kos-text/55">
            KEI {formatSpread(pick.keiSpreadPick)} · edge{" "}
            {formatAtsEdge(pick.atsEdge)} · {formatKickoff(pick.kickoff)}
          </p>
        </div>
        {tag ? (
          <span
            className={`shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${tagChipClass(tag, researchOnlyTags)}`}
          >
            {tag}
          </span>
        ) : null}
      </div>
    </li>
  );
}
