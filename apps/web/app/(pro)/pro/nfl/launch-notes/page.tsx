import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How to read the NFL desk",
  description:
    "Week 1 REG live · PRE off board · KEI = model + desk factors. Model, KEI, tags, play-to, and Edge Board — research only, not a tip service.",
};

const TERM_ROWS = [
  {
    term: "Model",
    meaning: "Research fair. Does not drive PLAY alone.",
  },
  {
    term: "KEI",
    meaning:
      "Model + Week 1 desk factors (injury / QB / rest-travel). Edge Board action line. Edge/Tag = KEI vs market, never Model vs market.",
  },
  {
    term: "Current / Open",
    meaning: "Latest books vs first capture.",
  },
  {
    term: "Tag",
    meaning:
      "PASS / LEAN / PLAY / BEST VALUE / ALERT / STAY AWAY — KEI vs Current.",
  },
  {
    term: "Play-to",
    meaning:
      "Price where the tag still holds; worse price can downgrade the tag.",
  },
  {
    term: "Confidence",
    meaning: "Separate from edge size.",
  },
] as const;

export default function NflLaunchNotesPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
        Week 1 REG live · PRE off board · KEI = model + desk factors
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
        How to read the NFL desk
      </h1>
      <p className="mt-2 text-sm text-kos-text/65">
        Date: August 17, 2026 · Depth as_of 2026-08-13 — not live injury feed
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href="/pro/nfl/overview"
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35"
        >
          ← NFL Overview
        </Link>
        <Link
          href="/edge-board/nfl"
          className="rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
        >
          Edge Board
        </Link>
        <Link
          href="/methodology"
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm text-kos-text/80 hover:border-kos-gold/35"
        >
          Methodology
        </Link>
      </div>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">Bottom line</h2>
        <p className="mt-3 text-base leading-7 text-kos-text/80">
          This is a research desk with Model fair, KEI = model + Week 1 desk
          factors, and tags vs market.
        </p>
        <p className="mt-2 text-base leading-7 text-kos-text/80">
          It isn&apos;t guaranteed picks or a tip service.
        </p>
        <p className="mt-2 text-base leading-7 text-kos-text/80">
          You bet prices, not teams.
        </p>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">
          How to read the numbers
        </h2>
        <div className="mt-4 overflow-x-auto rounded-xl border border-white/10">
          <table className="w-full min-w-[20rem] text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-black/40">
                <th className="px-3 py-2.5 font-semibold text-kos-text sm:px-4">
                  Term
                </th>
                <th className="px-3 py-2.5 font-semibold text-kos-text sm:px-4">
                  Meaning
                </th>
              </tr>
            </thead>
            <tbody>
              {TERM_ROWS.map((row) => (
                <tr
                  key={row.term}
                  className="border-b border-white/8 last:border-0"
                >
                  <td className="whitespace-nowrap px-3 py-3 align-top font-semibold text-kos-text sm:px-4">
                    {row.term}
                  </td>
                  <td className="px-3 py-3 align-top leading-relaxed text-kos-text/75 sm:px-4">
                    {row.meaning}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">
          Injury → current (manual v1)
        </h2>
        <p className="mt-3 text-base leading-7 text-kos-text/80">
          Depth is packaged as_of 2026-08-13. There is no live injury API.
          Boards must say that. Model stays research-fair. KEI may reprice
          when a starter is out — never a Model gut-edit.
        </p>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-base leading-7 text-kos-text/80">
          <li>
            Midweek report — beat + desk notes into pack injury_status /
            ol_roles
          </li>
          <li>
            Friday final — lock named Week 1 starters; if a QB1/skill1 is OUT,
            add injury_paths[] and republish
          </li>
          <li>
            Gameday inactives — apply to current depth; KEI reprices (injury_net
            / QB backup drop-off)
          </li>
        </ul>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">Week 1–2</h2>
        <p className="mt-3 text-base leading-7 text-kos-text/80">
          Tighter tag thresholds (need more edge to PLAY). Early season
          uncertainty is intentional.
        </p>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">Edge Board</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-base leading-7 text-kos-text/80">
          <li>Week 1 tab = all 16 REG Week 1 games</li>
          <li>
            <code className="text-kos-text/70">/pro/nfl/weekly-slate</code>{" "}
            aliases to{" "}
            <Link
              href="/pro/nfl/slate/today"
              className="font-semibold text-kos-gold hover:underline"
            >
              Weekly Slate
            </Link>
          </li>
          <li>Full slate = multi-week board; PRE filtered out</li>
          <li>Neutral sites labeled (e.g. Melbourne)</li>
          <li>Stat Drop includes Power</li>
        </ul>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">
          Game Boxes &amp; Survivor
        </h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-base leading-7 text-kos-text/80">
          <li>Deeper sims than thin demo runs; FG/XP included in scoring</li>
          <li>
            Survivor is a planning tool — path % is research, not a promise
          </li>
        </ul>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">Fantasy</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-base leading-7 text-kos-text/80">
          <li>
            Preseason skill board (QB/RB/WR/TE) vs FantasyPros ADP — same
            depth SoT as the engine (MIN QB1 Murray, ARI QB1 Brissett)
          </li>
          <li>
            K/DST may be unavailable until rankings include them — grades
            don&apos;t punish missing K/DST
          </li>
          <li>
            Guillotine + Sleepers desks live —{" "}
            <Link
              href="/pro/nfl/fantasy/guillotine"
              className="font-semibold text-kos-gold hover:underline"
            >
              Guillotine
            </Link>{" "}
            ·{" "}
            <Link
              href="/pro/nfl/fantasy/sleepers"
              className="font-semibold text-kos-gold hover:underline"
            >
              Sleepers
            </Link>
          </li>
          <li>Mock is practice; still model-informed, not pure ADP</li>
        </ul>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">Lineage</h2>
        <p className="mt-3 text-base leading-7 text-kos-text/80">
          Engine version + run id shown on major surfaces — know what
          you&apos;re looking at.
        </p>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">Responsibility</h2>
        <p className="mt-3 text-base leading-7 text-kos-text/80">
          Information only. No bet recommendations as instructions. Gamble
          responsibly.{" "}
          <Link
            href="/disclaimer"
            className="font-semibold text-kos-gold hover:underline"
          >
            Disclaimer
          </Link>
          .
        </p>
      </section>

      <hr className="my-8 border-white/12" />

      <section>
        <h2 className="text-xl font-semibold text-kos-gold">
          What comes after kickoff
        </h2>
        <p className="mt-3 text-base leading-7 text-kos-text/80">
          Injury report cadence → KEI updates; CLV tracking accumulates;
          ratings reweight with real games.
        </p>
      </section>

      <div className="mt-10 rounded-xl border border-white/10 bg-black/30 px-4 py-4 text-sm text-kos-text/70">
        Still unclear? Start on{" "}
        <Link
          href="/edge-board/nfl"
          className="font-semibold text-kos-gold hover:underline"
        >
          Edge Board
        </Link>{" "}
        with one game and compare Model → KEI → Current → Tag. Deeper process:{" "}
        <Link
          href="/methodology"
          className="font-semibold text-kos-gold hover:underline"
        >
          Methodology
        </Link>
        .
      </div>
    </main>
  );
}
