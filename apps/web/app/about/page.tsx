import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";

export const metadata = {
  title: "About",
  description:
    "KosEdge is a professional multi-sport analytics and handicapping desk. Built on Data, Driven by Edge.",
};

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-5 pt-10 pb-20 sm:px-6">
        <h1 className="text-4xl font-extrabold tracking-tight">
          About <span className="text-kos-gold">KosEdge</span>
        </h1>
        <p className="mt-4 text-base leading-7 text-white/80">
          KosEdge is a professional multi-sport analytics and handicapping desk.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          We build independent numbers, reprice them with real information, and
          measure them against the market. No locks. No hype. Process over
          vibes.
        </p>
        <p className="mt-4 text-base font-medium text-kos-gold">
          Built on Data, Driven by Edge.
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

        <h2 className="text-2xl font-bold text-kos-gold">Why this exists</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Sportsbooks run models. Serious bettors run models. Most people are
          left with narratives, parlays, and &quot;feels.&quot;
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          KosEdge exists to close that gap — professional-grade projection
          systems made usable, not intimidating.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">What we are</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>A modeling and simulation engine</li>
          <li>A structured handicapping desk</li>
          <li>A live Edge Board for comparing our numbers to the market</li>
          <li>A platform built around process, thresholds, and proof</li>
        </ul>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">How the desk works</h2>
        <ol className="mt-4 list-decimal space-y-3 pl-5 text-base leading-7 text-white/75">
          <li>
            <span className="font-semibold text-kos-text">Model</span> —
            independent research fair (simulation / efficiency backbone)
          </li>
          <li>
            <span className="font-semibold text-kos-text">KEI</span> — final
            handicap after information and situation (injuries, rest, weather,
            confirmation)
          </li>
          <li>
            <span className="font-semibold text-kos-text">Edge</span> — KEI
            versus the best available market price
          </li>
        </ol>
        <p className="mt-4 text-base leading-7 text-white/75">
          We don&apos;t bet opinion against the board. We price first, then
          decide.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">What you get</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>Multi-sport Edge Boards</li>
          <li>Season engines and game projections</li>
          <li>Survivor tools</li>
          <li>Fantasy draft desk and rankings</li>
          <li>Insights doctrine and weekly desk notes</li>
          <li>Transparent process language, not black-box &quot;locks&quot;</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          Some surfaces are free. Deeper desk work and ongoing notes sit behind
          Pro.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Who it&apos;s for</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Sharps who already understand EV, price, and discipline — and want
          structure, speed, and a real number to work from.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Serious casuals who are done guessing and want a clear process they
          can learn and trust.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          If you need constant action, this isn&apos;t it. Passing is part of
          the system.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">How we work</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>Make our number before respecting the market&apos;s</li>
          <li>
            Treat disagreement with the market as a question, not an automatic
            bet
          </li>
          <li>Rank information by reliability</li>
          <li>Use thresholds — if the price isn&apos;t there, we pass</li>
          <li>Grade process, not just outcomes</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          We don&apos;t promise you&apos;ll win every night.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          We promise that betting with a real process beats betting without one.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Where we&apos;re going
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          KosEdge is being built as a long-term desk:
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>stronger multi-sport engines</li>
          <li>deeper simulation and player-level work</li>
          <li>better information and reprice loops</li>
          <li>transparent performance tracking</li>
          <li>
            tools people actually stay on — Edge Board, survivor, fantasy,
            projections
          </li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          Built to scale. Built to last.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Start here</h2>
        <ul className="mt-4 space-y-3 text-base leading-7 text-white/75">
          <li>
            Open the{" "}
            <Link
              href="/edge-board"
              className="font-semibold text-kos-gold hover:underline"
            >
              Edge Board
            </Link>
          </li>
          <li>
            Read Insights →{" "}
            <Link
              href="/insights/doctrine"
              className="font-semibold text-kos-gold hover:underline"
            >
              Doctrine
            </Link>
          </li>
          <li>
            <Link
              href="/pro"
              className="font-semibold text-kos-gold hover:underline"
            >
              Go Pro
            </Link>{" "}
            when you want the full desk
          </li>
        </ul>

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

        <p className="mt-12 text-base font-medium text-kos-gold">
          Built on Data, Driven by Edge.
        </p>
        <p className="mt-2 text-base text-white/90">Welcome to KosEdge.</p>
      </article>
    </main>
  );
}
