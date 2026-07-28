import type { WriterProfile } from "@/lib/team-research";

export default function TeamPreviewSlot({
  teamName,
  writer,
  assignmentNote,
  provisional,
}: {
  teamName: string;
  writer: WriterProfile;
  assignmentNote: string;
  provisional?: boolean;
}) {
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
            Preview by
          </p>
          <p className="text-sm font-semibold text-kos-gold">{writer.name}</p>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-dashed border-white/20 bg-black/25 px-4 py-6 text-center">
        <p className="text-sm font-semibold text-kos-text">Coming soon</p>
        <p className="mx-auto mt-2 max-w-xl text-sm text-kos-text/70">
          Writer ownership is reserved for {writer.shortName}. Season preview
          copy will publish here after research delivery — no placeholder
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
