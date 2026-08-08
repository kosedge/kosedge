import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";

export const metadata = {
  title: "About",
  description:
    "KosEdge is a premier multi-sport analytics and handicapping desk — Model, KEI, and Edge. Built on Data, Driven by Edge.",
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <section className="mx-auto max-w-3xl px-5 pt-10 pb-20 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-kos-gold/80">
          About
        </p>
        <h1 className="mt-2 text-4xl font-extrabold tracking-tight">KosEdge</h1>
        <p className="mt-3 text-lg text-kos-gold">
          Built on Data, Driven by Edge
        </p>
        <p className="mt-4 text-base leading-7 text-white/75">
          A premier multi-sport analytics and handicapping desk. We price games
          independently, reprice with information, and measure edge only against
          the market you can bet.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/edge-board"
            className="inline-flex rounded-xl bg-kos-gold px-5 py-3 text-sm font-semibold text-black hover:opacity-90"
          >
            Edge Board
          </Link>
          <Link
            href="/insights/doctrine"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Insights Doctrine
          </Link>
          <Link
            href="/pro"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Pro
          </Link>
        </div>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Why the desk exists
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Sportsbooks and sharp desks run on numbers. Most recreational betting
          runs on narrative. That gap is expensive.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          KosEdge exists to put a usable desk in front of you — research fair,
          handicap reprice, and clear market disagreement — without turning the
          product into picks or hype.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Model · KEI · Edge</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Three layers. Do not collapse them into one number.
        </p>
        <ul className="mt-4 space-y-4 text-base leading-7 text-white/75">
          <li>
            <span className="font-semibold text-kos-text">Model</span> —
            research fair from structure and simulation. Independent price
            before market respect.
          </li>
          <li>
            <span className="font-semibold text-kos-text">KEI</span> — handicap
            reprice. Trusted information moves the desk fair when it earns the
            right to.
          </li>
          <li>
            <span className="font-semibold text-kos-text">Edge</span> — only
            versus the market. Fair disagreement that clears threshold at a
            price you can actually get.
          </li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          The boards show the number. Insights explains how the desk thinks.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">What you get</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>
            Edge Board — open vs best, fair context, live slate disagreement
          </li>
          <li>KEI Lines — desk fair by sport</li>
          <li>Insights — weekly desk notes + free Doctrine (house rules)</li>
          <li>Pro tools — deeper tracking, sport hubs, and ongoing notes</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          We do not sell locks. Pass is a position. Empty slates are allowed.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Who it&apos;s for</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          <span className="font-semibold text-kos-text">Sharps</span> — if you
          already think in EV, CLV, and thresholds, the desk adds structure and
          speed without drowning you in raw dumps.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          <span className="font-semibold text-kos-text">Serious casuals</span> —
          if you want to understand{" "}
          <em className="not-italic text-kos-text">why</em> a number matters —
          and leave parlays and vibes behind — Doctrine teaches the house rules;
          the boards put them to work.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">How we operate</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Make our number first. Reprice on tiered information. Act only when
          price clears threshold. Grade process over outcomes.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          CLV is a diagnostic, not a religion. Bankroll and variance are part of
          the job. No forced action.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Read the full house rules in Insights Doctrine — free by design.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Start here</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Open the board for numbers. Open Doctrine for process. Go Pro when you
          want the full weekly desk notes and deeper tools.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/edge-board"
            className="inline-flex rounded-xl bg-kos-gold px-5 py-3 text-sm font-semibold text-black hover:opacity-90"
          >
            Edge Board
          </Link>
          <Link
            href="/insights/doctrine"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Insights Doctrine
          </Link>
          <Link
            href="/pro"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Pro
          </Link>
        </div>

        <p className="mt-12 text-base font-medium text-white/90">
          Built on Data, Driven by Edge.
        </p>
      </section>
    </main>
  );
}
