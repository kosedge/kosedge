import Link from "next/link";
import {
  deskCardClassName,
  footerCardClassName,
  footerCtaClassName,
  footerTitleClassName,
  getSportDeskConfig,
} from "@/lib/pro-sport-desk";
import {
  buildSportOverviewSections,
  buildSportOverviewContent,
} from "@/lib/pro-sport-ia";
import SportOverviewSection from "@/components/pro/SportOverviewSection";
import { NFL_DESK_SUBTITLE, NFL_TAGLINE } from "@/lib/nfl-pro-nav";

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

const AT_A_GLANCE = [
  {
    href: "/pro/nfl/fair-lines",
    title: "Model vs Market",
    body: "KEI lines beside open books — see where the model separates.",
  },
  {
    href: "/pro/nfl/edges",
    title: "Key Numbers",
    body: "Thresholded edges around NFL key numbers and totals bands.",
  },
  {
    href: "/pro/nfl/injuries",
    title: "Injury Impact",
    body: "Availability context that changes pricing and role assumptions.",
  },
  {
    href: "/pro/nfl/teams",
    title: "Quick Access",
    body: "32-team research hub — depth, scheme, and preview angles.",
  },
] as const;

export default async function NflOverviewPage() {
  const desk = getSportDeskConfig("nfl");
  const content = buildSportOverviewContent("nfl", "NFL");
  // Weekly Slate is elevated above; keep Betting Desk / Props / Team / Governance.
  const gridSections = buildSportOverviewSections({
    sportKey: "nfl",
    base: "/pro/nfl",
    edgeBoardHref: "/edge-board/nfl",
    content,
  }).filter((section) => section.title !== "Weekly Slate");

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      {/* Compact header */}
      <section className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.14),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-size-[28px_28px] opacity-40" />
        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
              {NFL_DESK_SUBTITLE}
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
              NFL Overview
            </h1>
            <p className="mt-2 text-sm text-kos-text/75 sm:text-base">
              {NFL_TAGLINE} Context, model lines, and team research — not a
              picks feed.
            </p>
          </div>
          <div className="grid w-full gap-2 sm:w-auto sm:min-w-56">
            <Link
              href="/edge-board/nfl"
              className="rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2.5 text-center text-sm font-semibold text-kos-gold transition hover:border-kos-gold/60 hover:bg-kos-gold/25"
            >
              Open Live Edgeboard
            </Link>
            <Link
              href="/pro/nfl/slate/today"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 text-center text-sm font-semibold text-kos-text transition hover:border-kos-gold/35 hover:bg-white/10"
            >
              Open Weekly Slate
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
          {AT_A_GLANCE.map((item) => (
            <Link
              key={item.title}
              href={item.href}
              className="rounded-xl border border-white/10 bg-black/35 px-4 py-4 transition hover:border-kos-gold/40 hover:bg-black/50"
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

      {/* Elevated Weekly Slate */}
      <section className="mt-6 rounded-2xl border border-kos-gold/25 bg-linear-to-r from-kos-gold/12 via-black/40 to-black/60 p-5 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Primary writer home
            </p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-kos-text">
              Weekly Slate
            </h2>
            <p className="mt-2 text-sm text-kos-text/75">
              Matchup briefs, slate snapshot, and game cards — the desk home for
              weekly writer research before you jump to Edge Board.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/pro/nfl/slate/today"
              className="rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
            >
              Open Weekly Slate →
            </Link>
            <Link
              href="/pro/nfl/previews"
              className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35"
            >
              Team Previews
            </Link>
          </div>
        </div>
      </section>

      {/* Betting Desk */}
      <section className="mt-6">
        <div className="mb-3">
          <h2 className="text-xl font-semibold tracking-tight text-kos-text">
            Betting Desk
          </h2>
          <p className="mt-1 text-sm text-kos-text/70">
            Model lines, edges, and props — research surfaces, not pick sheets.
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

      {/* Props / Team Intel / Model Governance */}
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

      {/* Bottom resource grid — no KEI Lines duplicate; Team Previews elevated */}
      <section id="tools" className="mt-8 scroll-mt-28">
        <h2 className="text-xl font-semibold tracking-tight text-kos-text">
          Research tools
        </h2>
        <p className="mt-1 text-sm text-kos-text/65">
          Depth charts, previews, fantasy, governance, and schedule tools.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
