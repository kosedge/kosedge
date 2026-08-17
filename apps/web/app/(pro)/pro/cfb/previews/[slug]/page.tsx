import Link from "next/link";
import { notFound } from "next/navigation";
import { cfbTeamDisplayName } from "@/lib/cfb-conferences";
import {
  findCfbTeamPreview,
  getCfbTeamPreviews,
} from "@/lib/cfb-previews";
import {
  findCfbPowerTeam,
  projectGameHref,
} from "@/lib/cfb-research-artifacts";

export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return getCfbTeamPreviews().map((p) => ({ slug: p.slug }));
}

const SECTIONS = [
  ["bottomLine", "Bottom line"],
  ["theNumber", "The number"],
  ["quickProjection", "Quick projection"],
  ["rosterSnapshot", "Roster snapshot"],
  ["whatMattersMost", "What matters most"],
  ["scheduleNotes", "Schedule notes"],
  ["bettingAngles", "Betting angles to track"],
  ["whatWouldChange", "What would change this view"],
  ["modelNote", "Model note"],
] as const;

export default async function CfbTeamPreviewPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolved = await params;
  const preview = findCfbTeamPreview(resolved?.slug || "");
  if (!preview) notFound();
  const power = findCfbPowerTeam(preview.team);
  const nextHref = power
    ? projectGameHref({ team: power.team, next: power.next })
    : null;

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
      <nav className="mb-4 flex flex-wrap items-center gap-2 text-xs text-kos-text/65">
        <Link href="/pro/cfb/overview" className="hover:text-kos-gold">
          Overview
        </Link>
        <span>/</span>
        <Link href="/pro/cfb/previews" className="hover:text-kos-gold">
          Previews
        </Link>
        <span>/</span>
        <span className="text-kos-text">{cfbTeamDisplayName(preview.team)}</span>
      </nav>

      <header className="rounded-2xl border border-kos-gold/25 bg-black/35 p-5 sm:p-7">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
          KosEdge · {preview.date}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text">
          {preview.title}
        </h1>
        <p className="mt-2 text-sm text-kos-text/60">{preview.conference}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link
            href={`/pro/cfb/teams/${preview.team.toLowerCase()}`}
            className="min-h-11 inline-flex items-center rounded-lg border border-white/15 px-3 text-xs font-semibold text-kos-text"
          >
            Team desk
          </Link>
          {nextHref ? (
            <Link
              href={nextHref}
              className="min-h-11 inline-flex items-center rounded-lg border border-kos-gold/35 bg-kos-gold/10 px-3 text-xs font-semibold text-kos-gold"
            >
              Project next game
            </Link>
          ) : null}
        </div>
      </header>

      <article className="mt-6 space-y-5">
        {SECTIONS.map(([key, label]) => (
          <section key={key}>
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-kos-gold">
              {label}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-kos-text/80">
              {preview[key]}
            </p>
          </section>
        ))}
      </article>
    </main>
  );
}
