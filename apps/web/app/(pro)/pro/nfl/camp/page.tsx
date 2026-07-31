import type { Metadata } from "next";
import Link from "next/link";
import { buildNflCampDesk } from "@/lib/nfl-camp-desk";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "NFL Training Camp Desk",
  description:
    "Kos Edge Training Camp Desk — beat links, public camp intel, and writer coverage for the 2026 preseason.",
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

export default async function NflCampDeskPage() {
  const desk = await buildNflCampDesk();
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
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
            NFL Pro · Training Camp Desk
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
            Camp intel & beat map
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-kos-text/75">
            Daily cadence surface for July–September: public camp news, ESPN
            team hubs, and Kos Edge writer ownership. Thin edges stay Pass.
          </p>
          <p className="mt-2 text-xs text-kos-text/55">
            {desk.diagnostics.newsCount} camp headlines ·{" "}
            {desk.diagnostics.beatCount} team beats
            {desk.diagnostics.beatRegistryVersion
              ? ` · registry ${desk.diagnostics.beatRegistryVersion}`
              : ""}{" "}
            · era {desk.eraLabel}
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
            href="/pro/nfl/slate/today"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Weekly slate
          </Link>
          <Link
            href="/pro/nfl/previews"
            className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm hover:border-kos-gold/35"
          >
            Season previews
          </Link>
          <a
            href={desk.hubHref}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-kos-gold/30 bg-kos-gold/10 px-4 py-2 text-sm text-kos-gold hover:border-kos-gold/50"
          >
            ESPN 32-team hub
          </a>
        </div>
      </div>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-5 backdrop-blur-xl">
        <h2 className="text-lg font-semibold text-kos-text">Desk notes</h2>
        <ul className="mt-3 space-y-2 text-sm text-kos-text/75">
          {desk.notes.map((note) => (
            <li key={note} className="flex gap-2">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-kos-gold/70" />
              <span>{note}</span>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-wrap gap-2">
          {desk.writers.map((writer) => (
            <span
              key={writer.name}
              className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-kos-text/80"
            >
              {writer.name} · {writer.coverage}
            </span>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-kos-text">
              Latest camp headlines
            </h2>
            <p className="mt-1 text-sm text-kos-text/65">
              Filtered from ESPN NFL news for camp / roster / hold-in context.
              External links open the source.
            </p>
          </div>
        </div>
        {desk.news.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-kos-text/70">
            No camp-tagged headlines in the current ESPN pull. Use the 32-team
            hub and beat map below until the next refresh.
          </div>
        ) : (
          <div className="space-y-3">
            {desk.news.map((item) => (
              <a
                key={item.id}
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-2xl border border-white/10 bg-black/35 p-5 transition hover:border-kos-gold/35"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wide text-kos-text/50">
                  ESPN
                  {item.published ? ` · ${formatPublished(item.published)}` : ""}
                </p>
                <h3 className="mt-1 text-base font-semibold text-kos-text">
                  {item.headline}
                </h3>
                {item.description ? (
                  <p className="mt-2 text-sm text-kos-text/70">
                    {item.description}
                  </p>
                ) : null}
              </a>
            ))}
          </div>
        )}
      </section>

      <section className="mt-10">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-kos-text">
            Beat map · all 32
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-kos-text/65">
            Primary beat + Kos Edge writer owner. Jump to the season preview or
            public camp hub for each club.
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
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wide text-kos-text/50">
                            {beat.team}
                          </p>
                          <h4 className="mt-0.5 font-semibold text-kos-text">
                            {beat.teamName}
                          </h4>
                        </div>
                        <span className="rounded-md border border-kos-gold/25 bg-kos-gold/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-kos-gold">
                          {beat.kosEdgeWriter}
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-kos-text/70">
                        {beat.primaryWriter
                          ? `${beat.primaryWriter}${beat.primaryOutlet ? ` · ${beat.primaryOutlet}` : ""}${beat.primaryHandle ? ` · ${beat.primaryHandle}` : ""}`
                          : "Beat listing pending registry refresh"}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2 text-sm">
                        <Link
                          href={beat.previewHref}
                          className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                        >
                          Preview
                        </Link>
                        {beat.espnCampHref ? (
                          <a
                            href={beat.espnCampHref}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
                          >
                            Camp hub
                          </a>
                        ) : null}
                        <Link
                          href={`/pro/nfl/teams/${beat.team}/overview`}
                          className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 hover:border-kos-gold/35"
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
