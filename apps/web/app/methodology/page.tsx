import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";
import SiteFooter from "@/components/layout/SiteFooter";

export const metadata = {
  title: "Methodology",
  description:
    "KosEdge methodology: Model → KEI → Edge. Process over noise. Built on Data. Driven by Edge.",
};

export default function MethodologyPage() {
  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-5 pt-10 pb-20 sm:px-6">
        <h1 className="text-4xl font-extrabold tracking-tight">Methodology</h1>
        <p className="mt-3 text-xl font-semibold text-kos-gold">
          Process over noise
        </p>
        <p className="mt-3 text-base font-medium text-kos-gold">
          Built on Data. Driven by Edge.
        </p>
        <p className="mt-4 text-base leading-7 text-white/80">
          We don&apos;t sell locks. We run a desk.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          KosEdge prices games independently, reprices with real information,
          then measures our number against the market. Edge only exists when the
          separation clears our thresholds.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/edge-board"
            className="inline-flex rounded-xl bg-kos-gold px-5 py-3 text-sm font-semibold text-black hover:opacity-90"
          >
            Edge Board
          </Link>
          <Link
            href="/pro/model-transparency"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Model Transparency
          </Link>
          <Link
            href="/insights/doctrine"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Insights Doctrine
          </Link>
          <Link
            href="/about"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            About
          </Link>
        </div>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">The core contract</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Every serious number on this platform follows the same three-layer
          system:
        </p>
        <ol className="mt-4 list-decimal space-y-3 pl-5 text-base leading-7 text-white/75">
          <li>
            <span className="font-semibold text-kos-text">Model</span> —
            independent research fair from the simulation / efficiency engine
          </li>
          <li>
            <span className="font-semibold text-kos-text">KEI</span> — final
            handicap after information and situation (injuries, rest, weather,
            confirmation, market structure)
          </li>
          <li>
            <span className="font-semibold text-kos-text">Edge</span> — KEI
            versus the best available market price
          </li>
        </ol>
        <ul className="mt-5 space-y-2 text-base leading-7 text-white/75">
          <li>Model is research.</li>
          <li>KEI is the board number.</li>
          <li>
            Edge is only vs the market — never model vs market for PLAY/LEAN.
          </li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          If information is thin, KEI stays closer to Model.
        </p>
        <p className="mt-2 text-base leading-7 text-white/75">
          If information is strong, KEI moves.
        </p>
        <p className="mt-2 text-base leading-7 text-white/75">
          If price isn&apos;t there, we pass.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          How a number is built
        </h2>

        <h3 className="mt-6 text-lg font-semibold text-kos-text">1. Inputs</h3>
        <p className="mt-2 text-base leading-7 text-white/75">
          Sport-specific data stacks, not one generic formula:
        </p>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>team strength / efficiency</li>
          <li>roster and availability</li>
          <li>usage and role</li>
          <li>schedule / rest / travel</li>
          <li>environment (park, weather, venue)</li>
          <li>market context where useful</li>
        </ul>

        <h3 className="mt-6 text-lg font-semibold text-kos-text">
          2. Projection
        </h3>
        <p className="mt-2 text-base leading-7 text-white/75">
          The model produces a research fair — spread, total, win probability,
          and where available player-level output.
        </p>

        <h3 className="mt-6 text-lg font-semibold text-kos-text">
          3. Handicap (KEI)
        </h3>
        <p className="mt-2 text-base leading-7 text-white/75">
          We reprice the research fair with current information. This is the
          desk judgment layer. It is explicit, not hidden inside the sim.
        </p>

        <h3 className="mt-6 text-lg font-semibold text-kos-text">
          4. Market compare
        </h3>
        <p className="mt-2 text-base leading-7 text-white/75">
          KEI is compared to live books. Separation becomes candidate edge.
        </p>

        <h3 className="mt-6 text-lg font-semibold text-kos-text">
          5. Thresholds
        </h3>
        <p className="mt-2 text-base leading-7 text-white/75">
          Minimum edge, price quality, volatility, and confidence filters decide
          what is actionable.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Close is not enough. Passing is a position.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          What appears on the Edge Board
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>KEI lines (the handicap)</li>
          <li>Market prices</li>
          <li>Edge / tags only when thresholds clear</li>
          <li>
            Honest empty or markets-only states when a sport is not fully
            modeled yet
          </li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          We do not invent edges to fill a board.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Sport stacks, same standard
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Same professional energy. Different factor emphasis.
        </p>
        <ul className="mt-4 list-disc space-y-3 pl-5 text-base leading-7 text-white/75">
          <li>
            <span className="font-semibold text-kos-text">NFL</span> —
            EPA/script, depth, injuries, coaching tendencies, survivor/fantasy
            paths
          </li>
          <li>
            <span className="font-semibold text-kos-text">CFB</span> — roster
            construction, QB situation, efficiency backbone, HFA, early-season
            uncertainty
          </li>
          <li>
            <span className="font-semibold text-kos-text">
              CBB / NBA / MLB / NHL / WNBA
            </span>{" "}
            — sport-native efficiency, availability, and market structure
          </li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          Every sport is held to the same honesty bar: real model when ready,
          identity/fallback when not, no fake precision.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Tracking and accountability
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          We care about more than last night&apos;s result:
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>projection vs open and close</li>
          <li>CLV as a diagnostic</li>
          <li>process grades (good bet / bad bet independent of outcome)</li>
          <li>continuous calibration where evidence supports it</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          CLV is useful. It is not the whole religion.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Long-term edge is the goal. Short-term noise is expected.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Discipline</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>No forced action</li>
          <li>No chasing</li>
          <li>No parlay culture as process</li>
          <li>Bankroll and variance are part of the system</li>
          <li>
            Information has tiers — official and reliable sources outrank noise
          </li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          If the number isn&apos;t there, the correct play is nothing.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          What this is / isn&apos;t
        </h2>
        <h3 className="mt-5 text-lg font-semibold text-kos-text">This is</h3>
        <p className="mt-2 text-base leading-7 text-white/75">
          A modeling + handicapping desk with transparent process language and
          live tools.
        </p>
        <h3 className="mt-5 text-lg font-semibold text-kos-text">
          This isn&apos;t
        </h3>
        <p className="mt-2 text-base leading-7 text-white/75">
          A lock service, a tipster feed, or a promise that every night pays.
        </p>
        <p className="mt-4 text-base leading-7 text-white/75">
          We promise process.
        </p>
        <p className="mt-2 text-base leading-7 text-white/75">
          We promise independent numbers.
        </p>
        <p className="mt-2 text-base leading-7 text-white/75">
          We promise that betting with a real framework beats betting without
          one.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Go deeper</h2>
        <ul className="mt-4 space-y-3 text-base leading-7 text-white/75">
          <li>
            Insights →{" "}
            <Link
              href="/insights/doctrine"
              className="font-semibold text-kos-gold hover:underline"
            >
              Doctrine
            </Link>{" "}
            — house rules of the desk
          </li>
          <li>
            <Link
              href="/edge-board"
              className="font-semibold text-kos-gold hover:underline"
            >
              Edge Board
            </Link>{" "}
            — live numbers
          </li>
          <li>
            <Link
              href="/about"
              className="font-semibold text-kos-gold hover:underline"
            >
              About
            </Link>{" "}
            — what KosEdge is building
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
            href="/pro/model-transparency"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Model Transparency
          </Link>
          <Link
            href="/insights/doctrine"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            Insights Doctrine
          </Link>
          <Link
            href="/about"
            className="inline-flex rounded-xl border border-kos-border bg-kos-surface/40 px-5 py-3 text-sm font-semibold text-kos-text hover:border-kos-gold/40"
          >
            About
          </Link>
        </div>

        <p className="mt-12 text-base font-medium text-kos-gold">
          Built on Data. Driven by Edge.
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
