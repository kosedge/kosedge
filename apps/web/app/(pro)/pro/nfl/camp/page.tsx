import type { Metadata } from "next";
import Link from "next/link";
import NflTruthStateBadge from "@/components/pro/nfl/NflTruthStateBadge";
import { buildNflCampDesk } from "@/lib/nfl-camp-desk";
import {
  formatCampDeskShortDate,
  type CampDeskCard,
} from "@/lib/nfl-camp-desk-daily";
import { NFL_TEAM_DIRECTORY, teamDisplayName } from "@/lib/nfl-team-intel";
import {
  NFL_PRODUCT_SEASON,
  resolveNflTruthLabel,
} from "@/lib/nfl-truth-label";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL Camp Desk",
  description:
    "KosEdge daily camp desk — league wrap and team notes. ESPN and beats are sources, not the product.",
};

function formatPublished(value: string | null): string {
  if (!value) return "";
  const ts = Date.parse(value);
  if (!Number.isFinite(ts)) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
    timeZoneName: "short",
  }).format(new Date(ts));
}

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
        {card.is_material_depth ? (
          <span className="rounded-md border border-amber-400/35 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
            SoT flag
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
            Key points
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
          <span className="font-semibold text-kos-text/70">What to watch. </span>
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
            {card.sources.map((source) => (
              <li key={source.href}>
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
  const desk = await buildNflCampDesk({ team: teamFilter });
  const truth = resolveNflTruthLabel({
    season: NFL_PRODUCT_SEASON,
    launchPreseason: true,
  });
  const wrap = desk.kosedgeCards.find((card) => card.kind === "league_wrap");
  const notes = desk.kosedgeCards.filter((card) => card.kind === "team_note");
  const beatsByDivision = new Map<string, typeof desk.beats>();
  for (const beat of desk.beats) {
    const list = beatsByDivision.get(beat.division) ?? [];
    list.push(beat);
    beatsByDivision.set(beat.division, list);
  }

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
            League wrap and short team notes when there is real news. ESPN and
            beat reporters are sources. Thin camp info stays Pass — we do not
            invent a lean from one good practice. {truth.period_line}.
          </p>
          <p className="mt-2 text-xs text-kos-text/55">
            {desk.diagnostics.kosedgeCardCount} KosEdge cards ·{" "}
            {desk.diagnostics.wireCount} wire items (72h) ·{" "}
            {desk.diagnostics.beatCount} team beats
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
            href="/pro/nfl/news"
            className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            News archive
          </Link>
          <Link
            href="/pro/nfl/previews"
            className="min-h-11 inline-flex items-center rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Season previews
          </Link>
        </div>
      </div>

      <form
        method="get"
        className="mt-6 flex flex-wrap items-end gap-3 rounded-2xl border border-white/10 bg-black/25 p-3 sm:p-4"
      >
        <label className="text-sm text-kos-text/70">
          Team
          <select
            name="team"
            defaultValue={teamFilter ?? ""}
            className="mt-1 block min-h-11 min-w-[12rem] rounded-lg border border-white/15 bg-black/50 px-3 text-sm text-kos-text"
          >
            <option value="">All teams with notes</option>
            {NFL_TEAM_DIRECTORY.map((team) => (
              <option key={team.code} value={team.code}>
                {team.code} · {team.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="min-h-11 rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-4 text-sm font-semibold text-kos-gold"
        >
          Filter
        </button>
        {teamFilter ? (
          <Link
            href="/pro/nfl/camp"
            className="min-h-11 inline-flex items-center text-sm text-kos-text/60 hover:text-kos-text"
          >
            Clear
          </Link>
        ) : null}
      </form>

      <section className="mt-8 space-y-4">
        {wrap ? <CampNoteCard card={wrap} /> : null}
        {notes.map((card) => (
          <CampNoteCard key={card.id} card={card} />
        ))}
        {desk.kosedgeCards.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70">
            No KosEdge camp notes inside the 72-hour window
            {teamFilter ? ` for ${teamDisplayName(teamFilter)}` : ""}. Quiet
            days stay empty — no filler.
          </div>
        ) : null}
      </section>

      {desk.rotationNext.length > 0 ? (
        <p className="mt-4 text-xs text-kos-text/50">
          Quiet-club pulse queue: {desk.rotationNext.join(" · ")}
        </p>
      ) : null}

      {desk.sotFlags.length > 0 ? (
        <p className="mt-4 text-xs text-kos-text/50">
          SoT flags ({desk.sotFlags.map((card) => card.team_ids[0]).join(", ")}
          ): queue the existing depth job. This page does not publish a new
          model run.
        </p>
      ) : null}

      <details className="mt-8 rounded-2xl border border-white/10 bg-black/25 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-kos-text">
          Wire · ESPN headlines (not the desk)
        </summary>
        <p className="mt-2 text-xs text-kos-text/55">
          Public headlines from the last 72 hours. Citations only — KosEdge
          judgment lives in the cards above.
        </p>
        {desk.wire.length === 0 && desk.injuryNews.length === 0 ? (
          <p className="mt-3 text-sm text-kos-text/60">
            No camp-tagged ESPN items inside the freshness window.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {[...desk.injuryNews, ...desk.wire].map((item) => (
              <li key={`${item.source}-${item.id}`}>
                <a
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm hover:border-white/20"
                >
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-kos-text/45">
                    ESPN
                    {item.published ? ` · ${formatPublished(item.published)}` : ""}
                  </span>
                  <span className="mt-0.5 block text-kos-text/85">
                    {item.headline}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </details>

      <section className="mt-10">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-kos-text">
            Beat map · all 32
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-kos-text/65">
            Primary beat reporters. Jump to the season preview or public camp
            hub — those links are research, not today&apos;s desk.
          </p>
        </div>
        <div className="space-y-6">
          {[...beatsByDivision.entries()]
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([division, beats]) => (
              <div key={division}>
                <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-kos-gold/90">
                  {division}
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  {beats.map((beat) => (
                    <article
                      key={beat.team}
                      className="rounded-2xl border border-white/10 bg-black/30 p-4"
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-kos-text/50">
                        {beat.team}
                      </p>
                      <h4 className="mt-0.5 font-semibold text-kos-text">
                        {beat.teamName}
                      </h4>
                      <p className="mt-2 text-sm text-kos-text/70">
                        {beat.primaryWriter
                          ? `${beat.primaryWriter}${beat.primaryOutlet ? ` · ${beat.primaryOutlet}` : ""}`
                          : "Beat listing pending registry refresh"}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2 text-sm">
                        <Link
                          href={beat.previewHref}
                          className="min-h-11 inline-flex items-center rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                        >
                          Preview
                        </Link>
                        <Link
                          href={`/pro/nfl/camp?team=${beat.team}`}
                          className="min-h-11 inline-flex items-center rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                        >
                          Desk notes
                        </Link>
                        <Link
                          href={`/pro/nfl/teams/${beat.team}/overview`}
                          className="min-h-11 inline-flex items-center rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                        >
                          Team intel
                        </Link>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </section>
    </main>
  );
}
