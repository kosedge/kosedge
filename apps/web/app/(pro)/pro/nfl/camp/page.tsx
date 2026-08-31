import type { Metadata } from "next";
import Link from "next/link";
import CampDeskControls from "@/components/pro/nfl/CampDeskControls";
import NflTruthStateBadge from "@/components/pro/nfl/NflTruthStateBadge";
import { buildNflCampDesk } from "@/lib/nfl-camp-desk";
import {
  formatCampDeskDayLabel,
  formatCampDeskShortDate,
  isCampDeskXProfileHref,
  type CampDeskCard,
} from "@/lib/nfl-camp-desk-daily";
import { teamDisplayName } from "@/lib/nfl-team-intel";
import {
  NFL_PRODUCT_SEASON,
  resolveNflTruthLabel,
} from "@/lib/nfl-truth-label";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL Camp Desk",
  description:
    "KosEdge daily camp desk — league wrap and team notes. Pass is first-class.",
};

/**
 * Camp day JSON has no author/byline field. Do not invent one on the page.
 * Flag for ops: add `author` to the day schema before surfacing bylines.
 */
// BYLINE: cards have no author field — left blank on purpose.

function CampNoteCard({ card }: { card: CampDeskCard }) {
  const isWrap = card.kind === "league_wrap";
  return (
    <article
      className={`rounded-2xl border p-4 sm:p-5 ${
        isWrap
          ? "border-kos-gold/30 bg-kos-gold/5"
          : "border-white/10 bg-black/35"
      }`}
      data-testid={isWrap ? "camp-desk-wrap" : "camp-desk-note"}
      data-desk-date={card.desk_date}
      data-source-type={card.source_type}
    >
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
          KosEdge · {formatCampDeskShortDate(card.desk_date)}
        </p>
        {card.packageKind === "monday" ? (
          <span className="rounded-md border border-kos-gold/35 bg-kos-gold/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-kos-gold">
            Monday package
          </span>
        ) : null}
        {card.is_material_depth ? (
          <span className="rounded-md border border-amber-400/35 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
            Depth watch
          </span>
        ) : null}
      </div>
      <h2 className="mt-2 text-lg font-semibold leading-snug text-kos-text sm:text-xl">
        {card.title}
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-kos-text/85">
        <span className="font-semibold text-kos-text/70">Bottom line. </span>
        {card.bottom_line}
      </p>
      {card.key_points.length > 0 ? (
        <div className="mt-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-text/50">
            {isWrap ? "Call sheet" : "Key points"}
          </p>
          <ul className="mt-1.5 list-disc space-y-1.5 pl-5 text-sm text-kos-text/80">
            {card.key_points.map((point) => (
              <li key={point.slice(0, 48)}>{point}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {card.what_to_watch ? (
        <p className="mt-3 text-sm text-kos-text/75">
          <span className="font-semibold text-kos-text/70">
            What to watch.{" "}
          </span>
          {card.what_to_watch}
        </p>
      ) : null}
      {card.sot_flag ? (
        <p className="mt-2 text-xs text-amber-100/80">{card.sot_flag}</p>
      ) : null}
      {card.sources.length > 0 ? (
        <div className="mt-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-text/50">
            Sources
          </p>
          <ul className="mt-1 space-y-1 text-sm">
            {card.sources
              .filter((source) => !isCampDeskXProfileHref(source.href))
              .map((source) => (
                <li key={`${source.label}-${source.href}`}>
                  <a
                    href={source.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-kos-gold/90 underline-offset-2 hover:underline"
                  >
                    {source.label}
                  </a>
                </li>
              ))}
          </ul>
        </div>
      ) : null}
      {card.href && card.kind === "team_note" ? (
        <Link
          href={card.href}
          className="mt-3 inline-flex min-h-11 items-center rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm hover:border-kos-gold/35"
        >
          Season preview →
        </Link>
      ) : null}
    </article>
  );
}

export default async function NflCampDeskPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const raw = await searchParams;
  const teamRaw = raw.team;
  const teamFilter =
    typeof teamRaw === "string" && teamRaw.trim()
      ? teamRaw.trim().toUpperCase()
      : null;
  const dateRaw = raw.date;
  const dateFilter =
    typeof dateRaw === "string" && /^\d{4}-\d{2}-\d{2}$/.test(dateRaw.trim())
      ? dateRaw.trim()
      : null;
  const desk = await buildNflCampDesk({
    team: teamFilter,
    deskDate: dateFilter,
  });
  const truth = resolveNflTruthLabel({
    season: NFL_PRODUCT_SEASON,
    launchPreseason: true,
  });
  const wrap = desk.kosedgeCards.find((card) => card.kind === "league_wrap");
  const notes = desk.kosedgeCards.filter((card) => card.kind === "team_note");
  const viewingArchive =
    Boolean(desk.activeDeskDate) &&
    Boolean(desk.latestDeskDate) &&
    desk.activeDeskDate !== desk.latestDeskDate;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
              NFL Pro · Camp Desk
            </p>
            <NflTruthStateBadge state="PRESEASON" />
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
            KosEdge daily desk
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-kos-text/75">
            Today&apos;s call sheet and team notes. Pass stays first-class — we
            do not invent a lean from thin camp noise. {truth.period_line}.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/pro/nfl/overview"
            className="min-h-11 inline-flex items-center rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
          >
            NFL Overview
          </Link>
          <Link
            href="/pro/nfl/previews"
            className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Season previews
          </Link>
        </div>
      </div>

      <CampDeskControls
        team={teamFilter}
        date={desk.activeDeskDate}
        latestDeskDate={desk.latestDeskDate}
        deskDates={desk.deskDates}
      />

      <section className="mt-8 space-y-4" data-testid="camp-desk-shelf">
        {desk.deskStale && desk.latestDeskDate && !viewingArchive ? (
          <p
            className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100"
            data-testid="camp-desk-updating"
          >
            Desk updating — last package{" "}
            {formatCampDeskDayLabel(desk.latestDeskDate)}.
          </p>
        ) : null}
        {viewingArchive && desk.activeDeskDate ? (
          <p
            className="text-xs text-kos-text/55"
            data-testid="camp-desk-archive-banner"
          >
            Archive · {formatCampDeskDayLabel(desk.activeDeskDate)}. Switch Desk
            day back to today for the live shelf.
          </p>
        ) : null}
        {wrap ? <CampNoteCard card={wrap} /> : null}
        {notes.map((card) => (
          <CampNoteCard key={card.id} card={card} />
        ))}
        {desk.kosedgeCards.length === 0 ? (
          <div
            className="rounded-2xl border border-amber-500/25 bg-amber-500/10 p-6 text-sm text-amber-100"
            data-testid="camp-desk-updating"
          >
            Desk updating
            {desk.latestDeskDate
              ? ` — last package ${formatCampDeskDayLabel(desk.latestDeskDate)}`
              : ""}
            {teamFilter ? ` (${teamDisplayName(teamFilter)})` : ""}.
          </div>
        ) : null}
      </section>
    </main>
  );
}
