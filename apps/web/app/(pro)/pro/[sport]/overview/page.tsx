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
import {
  getSportGlance,
  getSportWorkflow,
} from "@/lib/sport-overview";
import {
  SPORT_DESK_SUBTITLE,
  SPORT_TAGLINE,
} from "@/lib/sport-pro-nav";

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
  const glance = getSportGlance(sportKey);
  const workflow = getSportWorkflow(sportKey);
  const tonightGames = await getTonightGames(sportKey);

  const isWeekly = sportKey === "cfb" || sportKey === "nfl";
  const slateLabel = isWeekly ? "Weekly Slate" : "Daily Slate";

  // Elevate slate above; drop empty props walls for college sports.
  const gridSections = buildSportOverviewSections({
    sportKey,
    base,
    edgeBoardHref,
    content,
  }).filter((section) => {
    if (section.title === "Weekly Slate") return false;
    if (
      (sportKey === "ncaam" || sportKey === "cfb") &&
      section.title.toLowerCase().includes("props")
    ) {
      return false;
    }
    return true;
  });

  const footerCols =
    desk.footerCards.length >= 5
      ? "sm:grid-cols-2 lg:grid-cols-3"
      : desk.footerCards.length >= 3
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
              href={`${base}/slate/today`}
              className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/35 hover:bg-white/10"
            >
              Open {slateLabel}
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
      </section>

      {/* Research Workflow */}
      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-5 sm:p-6">
        <h2 className="text-lg font-semibold tracking-tight text-kos-text">
          Research Workflow
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">{workflow.label}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {workflow.steps.map((item) => (
            <Link
              key={item.step}
              href={item.href}
              className="group min-h-11 rounded-xl border border-white/10 bg-white/[0.03] p-4 transition hover:border-kos-gold/40"
            >
              <span className="text-[11px] font-semibold tracking-[0.14em] text-kos-text/40">
                {item.step}
              </span>
              <h3 className="mt-1 text-base font-semibold text-kos-text group-hover:text-kos-gold">
                {item.title}
              </h3>
              <p className="mt-1 text-xs text-kos-text/65">{item.body}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Elevated Slate */}
      <section className="mt-6 rounded-2xl border border-kos-gold/25 bg-linear-to-r from-kos-gold/12 via-black/40 to-black/60 p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Primary research home
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-kos-text">
              {slateLabel}
            </h2>
            <p className="mt-2 text-sm text-kos-text/75">
              Matchup cards and slate context — the desk home before you jump to
              Edge Board. Times in ET.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`${base}/slate/today`}
              className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55 inline-flex items-center"
            >
              Open {slateLabel} →
            </Link>
            <Link
              href={`${base}/teams`}
              className="min-h-11 rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35 inline-flex items-center"
            >
              Team Research
            </Link>
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
            {desk.pathLabel} — research surfaces, not pick sheets.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {desk.cards.map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className={deskCardClassName(card.accent, card.status)}
            >
              <h3 className={deskTitleClass(card.accent)}>{card.title}</h3>
              <p className="mt-2 text-sm text-kos-text/75">{card.description}</p>
              <span className={deskCtaClass(card.accent)}>{card.cta}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Team Intel / Governance (and Props only when supported) */}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {gridSections.map((section) => (
          <SportOverviewSection
            key={section.title}
            title={section.title}
            subtitle={section.subtitle}
            links={section.links}
          />
        ))}
      </div>

      {/* Bottom research tools */}
      <section id="tools" className="mt-8 scroll-mt-28">
        <h2 className="text-xl font-semibold tracking-tight text-kos-text">
          Research tools
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">
          Power ratings, odds compare, execution, and sport-specific desks.
        </p>
        <div className={`mt-4 grid gap-4 ${footerCols}`}>
          {desk.footerCards.map((card) => (
            <Link
              key={card.title}
              href={card.href}
              className={footerCardClassName(card.accent)}
            >
              <h3 className={footerTitleClassName(card.accent)}>{card.title}</h3>
              <p className="mt-2 text-sm text-kos-text/80">{card.description}</p>
              <span className={footerCtaClassName(card.accent)}>{card.cta}</span>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
