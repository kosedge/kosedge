import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";
import SiteFooter from "@/components/layout/SiteFooter";

export const metadata = {
  title: "Terms of Service",
  description:
    "KosEdge Analytics Terms of Service — eligibility, accounts, Pro subscriptions, acceptable use, and liability.",
};

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-5 pt-10 pb-16 sm:px-6">
        <h1 className="text-4xl font-extrabold tracking-tight">
          Terms of Service
        </h1>
        <p className="mt-2 text-sm text-white/55">
          Last updated: August 8, 2026
        </p>
        <p className="mt-4 text-base leading-7 text-white/80">
          These Terms govern your use of kosedge.com and related services
          operated by KosEdge Analytics (&quot;KosEdge,&quot; &quot;we,&quot;
          &quot;us&quot;).
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          By using the site, you agree to these Terms and our{" "}
          <Link
            href="/privacy"
            className="font-semibold text-kos-gold hover:underline"
          >
            Privacy Policy
          </Link>{" "}
          and{" "}
          <Link
            href="/disclaimer"
            className="font-semibold text-kos-gold hover:underline"
          >
            Disclaimer
          </Link>
          .
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">What KosEdge is</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          KosEdge provides sports analytics, projections, tools, and educational
          content for entertainment and informational purposes.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          It is not a sportsbook, financial advisor, or betting service. Nothing
          here is financial, legal, or betting advice. See our{" "}
          <Link
            href="/disclaimer"
            className="font-semibold text-kos-gold hover:underline"
          >
            Disclaimer
          </Link>
          .
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Eligibility</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          You must be able to form a binding contract and comply with the laws
          where you live. Where gambling is regulated by age, you must meet that
          age (often 21+). If betting is illegal where you are, do not use this
          information to wager.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Accounts</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          You are responsible for your account credentials and activity. Provide
          accurate information. We may suspend or terminate accounts for abuse,
          fraud, or Terms violations.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Subscriptions / Pro
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Some features may be free; others may require a paid Pro subscription.
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>Prices and benefits are shown at purchase</li>
          <li>Billing is handled by our payment processor</li>
          <li>Subscriptions renew until canceled per the checkout terms</li>
          <li>
            We may change pricing or plan features with notice where required
          </li>
          <li>
            Refunds follow the policy stated at purchase or required by law
          </li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          We do not promise the free tier will always remain free. When paid
          tiers launch or change, we will communicate clearly.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Acceptable use</h2>
        <p className="mt-3 text-base leading-7 text-white/75">You may not:</p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>
            Scrape, bulk-export, or resell our content/data without permission
          </li>
          <li>Reverse engineer or attack the service</li>
          <li>Misrepresent our numbers as guaranteed outcomes</li>
          <li>Use the service for unlawful activity</li>
        </ul>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Intellectual property
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Site content, models, branding, and software are owned by KosEdge or
          licensors. You get a limited, non-exclusive license to use the service
          for personal, non-commercial research unless we agree otherwise in
          writing.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">No warranties</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          The service is provided &quot;as is.&quot; Models, KEI lines, edges,
          tags, simulations, and tools are estimates. We do not warrant
          accuracy, uptime, or results.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Limitation of liability
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          To the fullest extent permitted by law, KosEdge is not liable for
          betting losses, consequential damages, or decisions you make using the
          site. Our total liability for any claim relating to the service is
          limited to the amount you paid us in the 12 months before the claim
          (or $0 if you paid nothing).
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Indemnity</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          You agree to indemnify KosEdge against claims arising from your misuse
          of the service or violation of these Terms.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Changes</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          We may update these Terms. Continued use after posting means
          acceptance. Material changes may be highlighted in-product or by email
          when appropriate.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Governing law</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          These Terms are governed by the laws of the Commonwealth of Virginia,
          USA, without regard to conflict-of-law rules, unless mandatory local
          law says otherwise.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Contact</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Questions:{" "}
          <a
            href="mailto:support@kosedge.com"
            className="font-semibold text-kos-gold hover:underline"
          >
            support@kosedge.com
          </a>{" "}
          or the{" "}
          <Link
            href="/contact"
            className="font-semibold text-kos-gold hover:underline"
          >
            Contact
          </Link>{" "}
          page.
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
