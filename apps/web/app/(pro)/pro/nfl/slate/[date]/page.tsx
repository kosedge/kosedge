import type { Metadata } from "next";
import Link from "next/link";
import { buildNflWeeklySlate } from "@/lib/nfl-slate";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL Weekly Slate",
  description:
    "NFL weekly slate with preseason schedule, Kos Edge fair-lines, market odds, and publish tags.",
};

function tagClass(tag: "PLAY" | "LEAN" | "PASS" | null): string {
  if (tag === "PLAY")
    return "border-edge-green/40 bg-edge-green/10 text-edge-green";
  if (tag === "LEAN")
    return "border-kos-gold/40 bg-kos-gold/10 text-kos-gold";
  if (tag === "PASS")
    return "border-white/15 bg-white/5 text-kos-text/70";
  return "border-white/10 bg-white/5 text-kos-text/55";
}

export default async function NflWeeklySlatePage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const slate = await buildNflWeeklySlate(date);
  const totalCards = slate.sections.reduce(
    (sum, section) => sum + section.cards.length,
    0,
  );

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
            NFL Pro · Weekly slate
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
            {date === "today" ? "Current board" : `Slate · ${date}`}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-kos-text/75">
            Preseason market + camp strength reference, plus regular-season
            fair-lines with market join. PRE numbers are informational —
            season PLAY tags stay blocked.
          </p>
          <p className="mt-2 text-xs text-kos-text/55">
            {totalCards} games · model {slate.modelVersion || "—"} · odds feed{" "}
            {slate.diagnostics.oddsFeedStatus}
            {slate.diagnostics.marketJoinedCount
              ? ` · ${slate.diagnostics.marketJoinedCount} market-joined`
              : ""}
            {slate.diagnostics.campRefJoinedCount
              ? ` · ${slate.diagnostics.campRefJoinedCount} camp-ref PRE`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/pro/nfl/overview"
            className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
          >
            Back to Hub
          </Link>
          <Link
            href="/pro/nfl/camp"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Camp Desk
          </Link>
          <Link
            href="/odds/nfl"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Compare Odds
          </Link>
          <Link
            href="/pro/nfl/fair-lines"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            KEI Lines
          </Link>
        </div>
      </div>

      {slate.error ? (
        <div className="mt-6 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4 text-sm text-amber-100">
          Fair-lines warning: {slate.error}. Preseason schedule may still load
          below.
        </div>
      ) : null}

      {slate.sections.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-8 text-sm text-kos-text/70">
          No games resolved for this slate token yet. Try{" "}
          <Link href="/pro/nfl/slate/today" className="text-kos-gold">
            /pro/nfl/slate/today
          </Link>{" "}
          or week tokens like{" "}
          <Link href="/pro/nfl/slate/week-1" className="text-kos-gold">
            /pro/nfl/slate/week-1
          </Link>
          .
        </div>
      ) : (
        <div className="mt-8 space-y-10">
          {slate.sections.map((section) => (
            <section key={section.key}>
              <div className="mb-4">
                <h2 className="text-xl font-semibold text-kos-text">
                  {section.title}
                </h2>
                <p className="mt-1 max-w-3xl text-sm text-kos-text/65">
                  {section.subtitle}
                </p>
              </div>
              <div className="space-y-3">
                {section.cards.map((card) => (
                  <article
                    key={card.id}
                    className="rounded-2xl border border-white/10 bg-black/35 p-4 sm:p-5 backdrop-blur-xl"
                  >
                    <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-text/55">
                          {card.seasonType} · Week {card.week ?? "—"} ·{" "}
                          {card.kickoffLabel}
                        </p>
                        <h3 className="mt-1 text-base font-semibold text-kos-text sm:text-lg">
                          <span className="sm:hidden">
                            {card.awayAbbr}{" "}
                            <span className="text-kos-text/45">@</span>{" "}
                            {card.homeAbbr}
                          </span>
                          <span className="hidden sm:inline">
                            {card.awayTeam}{" "}
                            <span className="text-kos-text/45">@</span>{" "}
                            {card.homeTeam}
                          </span>
                        </h3>
                        <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-kos-text/80 sm:flex sm:flex-wrap sm:gap-x-4 sm:gap-y-1">
                          <p>
                            <span className="text-kos-text/50">Market</span>{" "}
                            {card.marketSpread} / {card.marketTotal}
                          </p>
                          <p>
                            <span className="text-kos-text/50">
                              {card.referenceLabel}
                            </span>{" "}
                            {card.modelSpread}
                            {card.referenceLabel === "Model"
                              ? ` / ${card.modelTotal}`
                              : card.modelTotal !== "—"
                                ? ` / ${card.modelTotal}`
                                : ""}
                          </p>
                          {card.spreadEdge != null &&
                          card.seasonType === "PRE" ? (
                            <p className="col-span-2 text-kos-text/55">
                              Ref vs market{" "}
                              {card.spreadEdge > 0 ? "+" : ""}
                              {card.spreadEdge.toFixed(1)}
                            </p>
                          ) : null}
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-kos-text/55">
                          {card.note}
                          {card.bestSpreadBook
                            ? ` · Best spread book ${card.bestSpreadBook}`
                            : ""}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span
                          className={`rounded-lg border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${tagClass(card.publishTagSpread)}`}
                        >
                          Spread {card.publishTagSpread ?? "n/a"}
                        </span>
                        <span
                          className={`rounded-lg border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${tagClass(card.publishTagTotal)}`}
                        >
                          Total {card.publishTagTotal ?? "n/a"}
                        </span>
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2 text-sm">
                      <Link
                        href={card.previewAwayHref}
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                      >
                        {card.awayAbbr} preview
                      </Link>
                      <Link
                        href={card.previewHomeHref}
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                      >
                        {card.homeAbbr} preview
                      </Link>
                      <Link
                        href="/pro/nfl/fair-lines"
                        className="rounded-lg border border-kos-gold/30 bg-kos-gold/10 px-3 py-1.5 text-kos-gold hover:border-kos-gold/50"
                      >
                        Open KEI desk
                      </Link>
                      <Link
                        href="/odds/nfl"
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                      >
                        Shop books
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
