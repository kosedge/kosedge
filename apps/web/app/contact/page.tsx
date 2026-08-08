import SiteHeader from "@/components/layout/SiteHeader";
import SiteFooter from "@/components/layout/SiteFooter";

export const metadata = {
  title: "Contact",
  description:
    "Contact KosEdge Analytics for product support, privacy requests, and partnerships.",
};

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-kos-black text-kos-text">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-5 pt-10 pb-16 sm:px-6">
        <h1 className="text-4xl font-extrabold tracking-tight">Contact</h1>

        <h2 className="mt-8 text-2xl font-bold text-kos-gold">
          Product / support
        </h2>
        <p className="mt-3 text-base leading-7 text-white/80">
          <a
            href="mailto:support@kosedge.com"
            className="font-semibold text-kos-gold hover:underline"
          >
            support@kosedge.com
          </a>
        </p>

        <h2 className="mt-8 text-2xl font-bold text-kos-gold">
          Business / partnerships
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          Same inbox is fine for now — include &quot;Business&quot; in the
          subject line.
        </p>
        <p className="mt-3 text-base leading-7 text-white/75">
          We read everything. Response times vary; we&apos;re a focused desk,
          not a call center.
        </p>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">Before you write</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-base leading-7 text-white/75">
          <li>Account / billing issues → include the email on the account</li>
          <li>Data / privacy requests → say so clearly in the subject</li>
          <li>Product feedback → welcomed; specific beats vague</li>
        </ul>

        <hr className="my-10 border-white/15" />

        <h2 className="text-2xl font-bold text-kos-gold">
          Responsible gambling
        </h2>
        <p className="mt-3 text-base leading-7 text-white/75">
          If you need help with gambling behavior:{" "}
          <a
            href="tel:18004262537"
            className="font-semibold text-kos-gold hover:underline"
          >
            1-800-GAMBLER
          </a>{" "}
          ·{" "}
          <a
            href="https://www.ncpgambling.org"
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-kos-gold hover:underline"
          >
            ncpgambling.org
          </a>
        </p>

        <p className="mt-12 text-base font-medium text-kos-gold">
          Built on Data, Driven by Edge.
        </p>
      </article>
      <SiteFooter />
    </main>
  );
}
