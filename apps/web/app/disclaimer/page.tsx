import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";
import SiteFooter from "@/components/layout/SiteFooter";

export const metadata = {
  title: "Disclaimer",
  description:
    "KosEdge Analytics disclaimer: entertainment and informational only. Not advice. Models and KEI are estimates, not instructions to bet.",
};

export default function DisclaimerPage() {
  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-5 pt-10 pb-20 sm:px-6">
        <h1 className="text-4xl font-extrabold tracking-tight">Disclaimer</h1>
        <p className="mt-4 text-base leading-7 text-white/80">
          KosEdge Analytics provides sports analytics, projections, and
          educational content for entertainment and informational purposes only.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Nothing on this site is financial, legal, tax, or betting advice.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          KosEdge is not a sportsbook, broker, or advisor. We do not place bets
          for you and we do not tell you that you must wager.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Your responsibility
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          You are solely responsible for:
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>your own decisions</li>
          <li>understanding the risks of sports betting</li>
          <li>complying with the laws where you live</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          In many jurisdictions you must be 21 or older to gamble. If betting is
          illegal where you are, do not use this information to wager.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Only risk money you can afford to lose.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          What our numbers are — and are not
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Model outputs, KEI lines, edges, tags (including PLAY / LEAN),
          simulations, rankings, and tools are research estimates, not
          guarantees and not instructions to bet.
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>Markets move</li>
          <li>Information is incomplete</li>
          <li>Models can be wrong</li>
          <li>Past results do not guarantee future outcomes</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          Use the desk as a decision-support framework. Final choices —
          including the choice to pass — are yours.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">No warranties</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          We do not guarantee accuracy, completeness, availability, or results.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Content may contain errors, delays, or gaps from third-party data,
          model limits, or rapid information changes.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          Use this platform at your own risk. To the fullest extent permitted by
          law, KosEdge is not liable for losses or decisions made using this
          site.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Responsible gambling
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          If betting is no longer fun, or you need help, resources are
          available:
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>
            <a
              href="tel:18004262537"
              className="font-semibold text-kos-gold hover:underline"
            >
              1-800-GAMBLER
            </a>
          </li>
          <li>
            <a
              href="https://www.ncpgambling.org"
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-kos-gold hover:underline"
            >
              ncpgambling.org
            </a>
          </li>
          <li>Local responsible-gambling resources in your area</li>
        </ul>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Questions</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          For product questions, use the{" "}
          <Link
            href="/contact"
            className="font-semibold text-kos-gold hover:underline"
          >
            Contact
          </Link>{" "}
          page.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          This page is a disclaimer, not legal advice to you.
        </p>

        <p className="mt-12 text-base font-medium text-kos-gold">
          Built on Data, Driven by Edge.
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
