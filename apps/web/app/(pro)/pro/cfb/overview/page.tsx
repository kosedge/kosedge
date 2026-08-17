import Link from "next/link";
import {
  CFB_CONFERENCE_FILTERS,
  cfbTeamDisplayName,
} from "@/lib/cfb-conferences";
import {
  getCfbConferencePreviews,
  getCfbTeamPreviews,
} from "@/lib/cfb-previews";
import { cfbKeiVersionStrip } from "@/lib/cfb-kei-artifacts";
import {
  cfbResearchVersionStrip,
  loadCfbPowerSot,
} from "@/lib/cfb-research-artifacts";
import { cfbModelDeskHonestyNote } from "@/lib/cfb-truth-label";

export const dynamic = "force-dynamic";

const START_HERE = [
  {
    step: "1",
    href: "/edge-board/cfb",
    title: "Edge Board",
    body: "Week 0/1 KEI vs market. Model is the research column. PASS default.",
  },
  {
    step: "2",
    href: "/pro/cfb/project-game",
    title: "Project Game",
    body: "Model + KEI when the game is on the slate. Drivers stay inspectable.",
  },
  {
    step: "3",
    href: "/pro/cfb/projections",
    title: "Projections",
    body: "Frozen N=10,000 expected wins. E[wins] ≠ power.",
  },
  {
    step: "4",
    href: "/pro/cfb/futures",
    title: "Futures",
    body: "Natty · CFP · conference titles from our paths. Not book prices.",
  },
  {
    step: "5",
    href: "/pro/cfb/teams",
    title: "Teams / Power",
    body: "136 FBS rows, conference filter, next opponent → Project Game.",
  },
] as const;

export default function CfbOverviewPage() {
  const power = loadCfbPowerSot();
  const version = cfbResearchVersionStrip();
  const teamPreviews = getCfbTeamPreviews();
  const confPreviews = getCfbConferencePreviews();
  const top = (power.teams ?? []).slice(0, 6);
  const p4Filters = CFB_CONFERENCE_FILTERS.filter((f) =>
    ["p4", "sec", "big-ten", "acc", "big-12", "independent"].includes(f.key),
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
      <section className="relative overflow-hidden rounded-2xl border border-kos-gold/20 bg-[radial-gradient(ellipse_at_top_left,_rgba(245,185,66,0.14),_transparent_55%),linear-gradient(160deg,#0c0c0e_0%,#141218_45%,#0a0a0c_100%)] p-5 sm:p-7">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-size-[28px_28px] opacity-40" />
        <div className="relative">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
            Pro desk · CFB Model + KEI
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
            College Football Overview
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-kos-text/75 sm:text-base">
            Independent lines are live. Model stays research-fair. KEI is the
            published line. Edge / Tag = KEI vs market. {cfbModelDeskHonestyNote()}
          </p>
          <p className="mt-3 text-xs text-kos-text/55">
            Engine {version.engine_version} · N={version.n_sims} · as_of{" "}
            {version.as_of} · KEI {cfbKeiVersionStrip().kei_version}
          </p>
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-kos-gold/25 bg-black/35 p-5 sm:p-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
          Start here
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-kos-text">
          One-screen contract
        </h2>
        <p className="mt-2 max-w-3xl text-sm text-kos-text/70">
          Model = research fair. KEI = published line (used_in_spread). Tag =
          KEI vs market. Early weeks: 4-pt PLAY bar, PASS default.
        </p>
        <ol className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {START_HERE.map((item) => (
            <li key={item.step}>
              <Link
                href={item.href}
                className="flex min-h-11 h-full flex-col rounded-xl border border-white/10 bg-black/40 px-4 py-4 transition hover:border-kos-gold/40 hover:bg-black/55"
              >
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-kos-gold">
                  {item.step}
                </span>
                <h3 className="mt-1 text-sm font-semibold text-kos-text">
                  {item.title}
                </h3>
                <p className="mt-1.5 text-xs leading-relaxed text-kos-text/65">
                  {item.body}
                </p>
              </Link>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <h2 className="text-lg font-semibold text-kos-text">Power snapshot</h2>
            <Link
              href="/pro/cfb/teams"
              className="text-xs font-semibold text-kos-gold hover:underline"
            >
              Full 136 →
            </Link>
          </div>
          <p className="mt-1 text-xs text-kos-text/55">
            Top of board is Power-4 / Notre Dame — not inverted G5-over-P4.
          </p>
          <ol className="mt-3 space-y-2">
            {top.map((row) => (
              <li key={row.team} className="flex items-center justify-between gap-3 text-sm">
                <Link
                  href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                  className="font-medium text-kos-text hover:text-kos-gold"
                >
                  <span className="mr-2 text-kos-text/40">{row.rank}</span>
                  {cfbTeamDisplayName(row.team)}
                </Link>
                <span className="tabular-nums text-xs text-kos-text/60">
                  {row.power_index?.toFixed(3)} · {row.conference}
                </span>
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-2xl border border-white/10 bg-black/30 p-5">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <h2 className="text-lg font-semibold text-kos-text">Previews</h2>
            <Link
              href="/pro/cfb/previews"
              className="text-xs font-semibold text-kos-gold hover:underline"
            >
              All team previews →
            </Link>
          </div>
          <p className="mt-1 text-xs text-kos-text/55">
            KosEdge + date only. Research language. {teamPreviews.length} team
            · {confPreviews.length} conference.
          </p>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {teamPreviews.map((p) => (
              <li key={p.slug}>
                <Link
                  href={`/pro/cfb/previews/${p.slug}`}
                  className="block min-h-11 rounded-lg border border-white/10 px-3 py-2 text-sm text-kos-text hover:border-kos-gold/35"
                >
                  {cfbTeamDisplayName(p.team)}
                  <span className="ml-2 text-xs text-kos-text/45">
                    {p.conference}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-5">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h2 className="text-lg font-semibold text-kos-text">
            Conference filter
          </h2>
          <Link
            href="/pro/cfb/conferences"
            className="text-xs font-semibold text-kos-gold hover:underline"
          >
            Conference previews →
          </Link>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {p4Filters.map((f) => (
            <Link
              key={f.key}
              href={f.href}
              className="min-h-11 inline-flex items-center rounded-lg border border-white/12 px-3 text-xs font-semibold text-kos-text/80 hover:border-kos-gold/40"
            >
              {f.label}
            </Link>
          ))}
          <Link
            href="/pro/cfb/conferences/aac"
            className="min-h-11 inline-flex items-center rounded-lg border border-white/12 px-3 text-xs font-semibold text-kos-text/80 hover:border-kos-gold/40"
          >
            AAC
          </Link>
          <Link
            href="/pro/cfb/conferences/mountain-west"
            className="min-h-11 inline-flex items-center rounded-lg border border-white/12 px-3 text-xs font-semibold text-kos-text/80 hover:border-kos-gold/40"
          >
            Mountain West
          </Link>
        </div>
      </section>
    </main>
  );
}
