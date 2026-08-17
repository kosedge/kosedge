import Link from "next/link";
import { notFound } from "next/navigation";
import {
  CFB_CONFERENCE_FILTERS,
  cfbTeamDisplayName,
  displayCfbConference,
} from "@/lib/cfb-conferences";
import {
  findCfbConferencePreview,
  getCfbConferencePreviews,
} from "@/lib/cfb-previews";
import { cfbPowerTeams } from "@/lib/cfb-research-artifacts";

export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return getCfbConferencePreviews().map((p) => ({ conf: p.slug }));
}

const SLUG_TO_DISPLAY: Record<string, string> = {
  sec: "SEC",
  "big-ten": "Big Ten",
  acc: "ACC",
  "big-12": "Big 12",
  independent: "Independent",
  aac: "AAC",
  "mountain-west": "Mountain West",
};

export default async function CfbConferencePreviewPage({
  params,
}: {
  params: Promise<{ conf: string }>;
}) {
  const resolved = await params;
  const preview = findCfbConferencePreview(resolved?.conf || "");
  if (!preview) notFound();
  const display = SLUG_TO_DISPLAY[preview.slug] ?? preview.conference;
  const filter = CFB_CONFERENCE_FILTERS.find(
    (f) =>
      f.label === display ||
      (preview.slug === "mountain-west" && f.key === "mwc"),
  );
  const roster = cfbPowerTeams()
    .filter((row) => displayCfbConference(row.team, row.conference) === display)
    .slice(0, 8);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-4 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/cfb/overview" className="hover:text-kos-gold">
          Overview
        </Link>
        <span>/</span>
        <Link href="/pro/cfb/conferences" className="hover:text-kos-gold">
          Conferences
        </Link>
        <span>/</span>
        <span className="text-kos-text">{preview.conference}</span>
      </nav>

      <header className="rounded-2xl border border-kos-gold/25 bg-black/35 p-5 sm:p-7">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
          KosEdge · {preview.date}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          {preview.title}
        </h1>
        {filter ? (
          <Link
            href={filter.href}
            className="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-kos-gold"
          >
            Filter Teams · {filter.label} →
          </Link>
        ) : null}
      </header>

      <article className="mt-6 space-y-5">
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Bottom line
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {preview.bottomLine}
          </p>
        </section>
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Contenders
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {preview.contenders}
          </p>
        </section>
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Sleepers
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {preview.sleepers}
          </p>
        </section>
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Schedule / path notes
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {preview.scheduleNotes}
          </p>
        </section>
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Research angles
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {preview.researchAngles}
          </p>
        </section>
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
            Model note
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
            {preview.modelNote}
          </p>
        </section>
      </article>

      {roster.length > 0 ? (
        <section className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-5">
          <h2 className="text-sm font-semibold text-kos-text">
            Power snapshot
          </h2>
          <ol className="mt-3 space-y-2 text-sm">
            {roster.map((row) => (
              <li key={row.team} className="flex justify-between gap-3">
                <Link
                  href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                  className="text-kos-text hover:text-kos-gold"
                >
                  {row.rank} {cfbTeamDisplayName(row.team)}
                </Link>
                <span className="tabular-nums text-xs text-kos-text/55">
                  {row.power_index?.toFixed(3)}
                </span>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </main>
  );
}
