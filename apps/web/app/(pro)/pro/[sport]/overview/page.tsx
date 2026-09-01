import Link from "next/link";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import { getTonightGames } from "@/lib/edge-board-tonight";
import {
  buildSportOverviewContent,
  buildSportOverviewSections,
} from "@/lib/pro-sport-ia";
import {
  deskCardClassName,
  footerCardClassName,
  footerCtaClassName,
  footerTitleClassName,
  getSportDeskConfig,
} from "@/lib/pro-sport-desk";
import SportOverviewSection from "@/components/pro/SportOverviewSection";
import WeeklyGamesScroller from "@/components/pro/WeeklyGamesScroller";
import { getSportGlance } from "@/lib/sport-overview";
import { SPORT_DESK_SUBTITLE, SPORT_TAGLINE } from "@/lib/sport-pro-nav";

const tonightGamesEmpty: Awaited<ReturnType<typeof getTonightGames>> = [];

function deskTitleClass(accent: "gold" | "green" | "neutral"): string {
  if (accent === "gold") return "text-lg font-semibold text-kos-gold";
  if (accent === "green") return "text-lg font-semibold text-edge-green";
  return "text-lg font-semibold text-kos-text";
}

function deskCtaClass(accent: "gold" | "green" | "neutral"): string {
  if (accent === "green")
    return "mt-3 inline-block text-sm font-semibold text-edge-green";
  return "mt-3 inline-block text-sm font-semibold text-kos-gold";
}

export default async function SportOverviewPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const sportName = sportDisplayLabel(sportKey);
  const base = `/pro/${sportKey || "nfl"}`;
  const edgeBoardHref = `/edge-board/${sportKey || "nfl"}`;
  const content = buildSportOverviewContent(sportKey, sportName);
  const desk = getSportDeskConfig(sportKey);
  const glance = getSportGlance(sportKey) ?? [];
  let tonightGames: typeof tonightGamesEmpty = tonightGamesEmpty;
  try {
    tonightGames = await Promise.race([
      getTonightGames(sportKey),
      new Promise<typeof tonightGamesEmpty>((resolve) =>
        setTimeout(() => resolve(tonightGamesEmpty), 8_000),
      ),
    ]);
    if (!Array.isArray(tonightGames)) tonightGames = tonightGamesEmpty;
  } catch {
    tonightGames = tonightGamesEmpty;
  }

  const isWeekly = sportKey === "cfb" || sportKey === "nfl";
  const slateLabel = isWeekly ? "Weekly Slate" : "Daily Slate";
  // NBA Daily Slate lives at /slate/today; bare /slate 404s — prefer Edge Board CTA.
  const slateHref = sportKey === "nba" ? edgeBoardHref : `${base}/slate/today`;
  const slateCtaLabel =
    sportKey === "nba" ? "Open Edge Board" : `Open ${slateLabel}`;

  // Elevate slate above; drop empty props walls for college sports.
  const gridSections = (
    buildSportOverviewSections({
      sportKey,
      base,
      edgeBoardHref,
      content,
    }) ?? []
  ).filter((section) => {
    if (!section?.title) return false;
    if (section.title === "Weekly Slate") return false;
    if (
      (sportKey === "ncaam" || sportKey === "cfb") &&
      section.title.toLowerCase().includes("props")
    ) {
      return false;
    }
    return true;
  });

  const deskCards = Array.isArray(desk?.cards) ? desk.cards : [];
  const footerCards = Array.isArray(desk?.footerCards) ? desk.footerCards : [];
  const footerCols =
    footerCards.length >= 5
      ? "sm:grid-cols-2 lg:grid-cols-3"
      : footerCards.length >= 3
        ? "sm:grid-cols-2 lg:grid-cols-3"
        : "sm:grid-cols-2";

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      {/* Compact header — NFL Overview pattern */}
      <section className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.14),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-size-[28px_28px] opacity-40" />
        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
              {SPORT_DESK_SUBTITLE}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              {sportName} Overview
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              {SPORT_TAGLINE} {content.heroSummary}
            </p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-56">
            <Link
              href={edgeBoardHref}
              className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25"
            >
              Open Live Edgeboard
            </Link>
            <Link
              href={slateHref}
              className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/35 hover:bg-white/10"
            >
              {slateCtaLabel}
            </Link>
          </div>
        </div>
      </section>

      {/* At a Glance */}
      <section className="mt-6">
        <div className="mb-3 flex items-end justify-between gap-3">
          <h2 className="text-lg font-semibold tracking-tight text-kos-text">
            At a Glance
          </h2>
        </div>
        {glance.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {glance.map((item) => (
              <Link
                key={item.title}
                href={item.href}
                className="min-h-11 rounded-xl border border-white/10 bg-black/35 px-4 py-4 transition hover:border-kos-gold/40 hover:bg-black/50"
              >
                <h3 className="text-sm font-semibold text-kos-gold">
                  {item.title}
                </h3>
                <p className="mt-1.5 text-xs leading-relaxed text-kos-text/70">
                  {item.body}
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-kos-text/60">
            Desk links will appear here when this sport hub is wired.
          </p>
        )}
      </section>

      {/* Elevated Slate */}
      <section className="mt-6 rounded-2xl border border-kos-gold/25 bg-linear-to-r from-kos-gold/12 via-black/40 to-black/60 p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Primary research home
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-kos-text">
              {sportKey === "nba" ? "Edge Board slate" : slateLabel}
            </h2>
            <p className="mt-2 text-sm text-kos-text/75">
              {sportKey === "nba"
                ? "Matchup cards from the live Edge Board (Ch4 KEI). Times in ET."
                : "Matchup cards and slate context — the desk home before you jump to Edge Board. Times in ET."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={slateHref}
              className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55 inline-flex items-center"
            >
              {slateCtaLabel} →
            </Link>
            {sportKey === "nba" ? (
              <Link
                href="/pro/nba/fantasy"
                className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35 inline-flex items-center"
              >
                Fantasy
              </Link>
            ) : (
              <Link
                href={`${base}/teams`}
                className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35 inline-flex items-center"
              >
                Team Research
              </Link>
            )}
          </div>
        </div>
        {tonightGames.length > 0 ? (
          <div className="mt-4">
            <WeeklyGamesScroller games={tonightGames} sport={sportKey} />
          </div>
        ) : (
          <p className="mt-4 text-sm text-kos-text/60">
            {sportKey === "nba" || sportKey === "ncaam"
              ? `No ${sportName} game board posted on Odds API right now (offseason / no live slate). Shell stays ready — we do not invent matchups or KEI.`
              : `No live ${sportName} slate rows yet. Edge Board and Compare Odds refresh when books post.`}
          </p>
        )}
      </section>

      {/* Betting Desk */}
      <section className="mt-6">
        <div className="mb-3">
          <h2 className="text-xl font-semibold tracking-tight text-kos-text">
            Betting Desk
          </h2>
          <p className="mt-1 text-sm text-kos-text/70">
            {desk?.pathLabel ?? "Research path"} — research surfaces, not pick
            sheets.
          </p>
        </div>
        {deskCards.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-3">
            {deskCards.map((card) => (
              <Link
                key={card.title}
                href={card.href}
                className={deskCardClassName(card.accent, card.status)}
              >
                <h3 className={deskTitleClass(card.accent)}>{card.title}</h3>
                <p className="mt-2 text-sm text-kos-text/75">
                  {card.description}
                </p>
                <span className={deskCtaClass(card.accent)}>{card.cta}</span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-kos-text/60">
            No desk cards for this sport yet.
          </p>
        )}
      </section>

      {/* Team Intel / Governance (and Props only when supported) */}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {gridSections.map((section) => (
          <SportOverviewSection
            key={section.title}
            title={section.title}
            subtitle={section.subtitle}
            links={section.links ?? []}
          />
        ))}
        <Link
          href={`/insights/sports/${sportKey}`}
          className="rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-5 hover:border-kos-gold/45 transition"
        >
          <h3 className="font-semibold text-kos-gold">Insights</h3>
          <p className="mt-2 text-sm text-kos-text/70">
            Desk notes and doctrine for {sportName} — This Week and house rules.
          </p>
        </Link>
      </div>

      {/* Bottom research tools */}
      <section id="tools" className="mt-8 scroll-mt-28">
        <h2 className="text-xl font-semibold tracking-tight text-kos-text">
          Research tools
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">
          Power ratings, odds compare, execution, and sport-specific desks.
        </p>
        {footerCards.length > 0 ? (
          <div className={`mt-4 grid gap-4 ${footerCols}`}>
            {footerCards.map((card) => (
              <Link
                key={card.title}
                href={card.href}
                className={footerCardClassName(card.accent)}
              >
                <h3 className={footerTitleClassName(card.accent)}>
                  {card.title}
                </h3>
                <p className="mt-2 text-sm text-kos-text/80">
                  {card.description}
                </p>
                <span className={footerCtaClassName(card.accent)}>
                  {card.cta}
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-kos-text/60">
            No research-tool cards for this sport yet.
          </p>
        )}
      </section>
    </main>
  );
}
