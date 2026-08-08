import Link from "next/link";
import SiteHeader from "@/components/layout/SiteHeader";
import SiteFooter from "@/components/layout/SiteFooter";

export const metadata = {
  title: "Privacy Policy",
  description:
    "KosEdge Analytics privacy policy — what we collect, how we use it, and your choices.",
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-5 pt-10 pb-16 sm:px-6">
        <h1 className="text-4xl font-extrabold tracking-tight">
          Privacy Policy
        </h1>
        <p className="mt-2 text-sm text-white/55">
          Last updated: August 8, 2026
        </p>
        <p className="mt-4 text-base leading-7 text-white/80">
          KosEdge Analytics (&quot;KosEdge,&quot; &quot;we,&quot;
          &quot;us&quot;) respects your privacy. This policy explains what we
          collect, how we use it, and the choices you have.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Information we collect
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>
            <span className="font-semibold text-kos-text">Account data</span> —
            email, name/display name, password or auth tokens if you create an
            account
          </li>
          <li>
            <span className="font-semibold text-kos-text">
              Subscription / billing data
            </span>{" "}
            — handled by our payment processor; we do not store full card
            numbers
          </li>
          <li>
            <span className="font-semibold text-kos-text">Usage data</span> —
            pages viewed, feature use, device/browser basics, approximate
            location from IP
          </li>
          <li>
            <span className="font-semibold text-kos-text">Communications</span>{" "}
            — messages you send us (support, feedback)
          </li>
          <li>
            <span className="font-semibold text-kos-text">
              Cookies / similar tech
            </span>{" "}
            — session, preference, and analytics cookies needed to run the site
          </li>
        </ul>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          How we use information
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>Provide and improve the product</li>
          <li>Authenticate accounts and protect security</li>
          <li>Process subscriptions and communicate about your account</li>
          <li>Measure performance and fix issues</li>
          <li>Comply with law</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          We do not sell your personal information.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Sharing</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          We share data only with service providers who help us operate
          (hosting, analytics, auth, payments), or when required by law.
          Providers process data under their own terms.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Retention</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          We keep information only as long as needed for the purposes above,
          account life, legal obligations, or dispute resolution.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Your choices</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>
            Access, correct, or delete account data (where available in-product
            or by request)
          </li>
          <li>Opt out of non-essential marketing email</li>
          <li>Control cookies via browser settings</li>
        </ul>
        <p className="mt-4 text-base leading-7 text-white/75">
          Depending on where you live, you may have additional rights under
          applicable privacy law. Contact us to exercise them.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Children</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          KosEdge is not directed at children under 18. We do not knowingly
          collect their data.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Changes</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          We may update this policy. Material changes will be posted here with
          an updated date.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Contact</h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Privacy questions: use the{" "}
          <Link
            href="/contact"
            className="font-semibold text-kos-gold hover:underline"
          >
            Contact
          </Link>{" "}
          page or email{" "}
          <a
            href="mailto:support@kosedge.com"
            className="font-semibold text-kos-gold hover:underline"
          >
            support@kosedge.com
          </a>
          .
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
