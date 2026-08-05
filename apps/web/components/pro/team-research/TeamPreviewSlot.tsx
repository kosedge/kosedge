import Link from "next/link";
import type { WriterProfile } from "@/lib/team-research";
import { getNflSeasonPreview } from "@/lib/nfl-season-previews";

export default function TeamPreviewSlot({
  teamName,
  teamCode,
  writer,
  assignmentNote,
  provisional,
}: {
  teamName: string;
  /** NFL team abbreviation — enables live season-preview wiring. */
  teamCode?: string;
  writer: WriterProfile;
  assignmentNote: string;
  provisional?: boolean;
}) {
  const preview =
    teamCode && teamCode.trim()
      ? getNflSeasonPreview(teamCode)
      : null;

  if (preview) {
    return (
      <section
        className="rounded-2xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-6"
        aria-labelledby="team-preview-heading"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
              Season preview
            </p>
            <h2
              id="team-preview-heading"
              className="mt-1 text-xl font-semibold text-kos-text"
            >
              {preview.teamName}
            </h2>
          </div>
          <div className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-3 py-2 text-right">
            <p className="text-[10px] uppercase tracking-wide text-kos-gold/80">
              KosEdge
            </p>
            <p className="text-sm font-semibold text-kos-gold">2026</p>
          </div>
        </div>

        {preview.angle ? (
          <p className="mt-4 text-sm font-medium text-kos-text/90">
            {preview.angle}
          </p>
        ) : null}
        <p className="mt-2 text-sm leading-relaxed text-kos-text/75">
          {preview.excerpt}
        </p>
        {preview.market ? (
          <p className="mt-3 text-xs text-kos-text/55">Market · {preview.market}</p>
        ) : null}

        <div className="mt-5 flex flex-wrap gap-2">
          <Link
            href={preview.href}
            className="rounded-xl border border-kos-gold/35 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:bg-kos-gold/20"
          >
            Read full preview →
          </Link>
          <Link
            href="/pro/nfl/previews"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm text-kos-text hover:border-kos-gold/35"
          >
            All 32 teams
          </Link>
        </div>

        <p className="mt-3 text-xs text-kos-text/55">
          {assignmentNote}
          {provisional ? " · Provisional until college matrix is locked." : ""}
        </p>
      </section>
    );
  }

  return (
    <section
      className="rounded-2xl border border-kos-gold/25 bg-linear-to-br from-kos-gold/10 via-black/40 to-black/70 p-5 sm:p-6"
      aria-labelledby="team-preview-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
            Season preview
          </p>
          <h2
            id="team-preview-heading"
            className="mt-1 text-xl font-semibold text-kos-text"
          >
            {teamName}
          </h2>
        </div>
        <div className="rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-3 py-2 text-right">
          <p className="text-[10px] uppercase tracking-wide text-kos-gold/80">
            KosEdge
          </p>
          <p className="text-sm font-semibold text-kos-gold">Pending</p>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-dashed border-white/20 bg-black/25 px-4 py-6 text-center">
        <p className="text-sm font-semibold text-kos-text">Preview pending</p>
        <p className="mx-auto mt-2 max-w-xl text-sm text-kos-text/70">
          Season preview publishes here after research delivery — no placeholder
          article text is invented.
        </p>
      </div>

      <p className="mt-3 text-xs text-kos-text/55">
        {assignmentNote}
        {provisional ? " · Provisional until college matrix is locked." : ""}
      </p>
    </section>
  );
}
