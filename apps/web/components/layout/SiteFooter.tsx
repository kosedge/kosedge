import Link from "next/link";

const LEGAL_LINKS = [
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
  { href: "/contact", label: "Contact" },
  { href: "/disclaimer", label: "Disclaimer" },
] as const;

export default function SiteFooter({
  tagline = "Built on Data, Driven by Edge.",
}: {
  tagline?: string;
}) {
  return (
    <footer className="relative z-10 border-t border-white/10 bg-black/35 backdrop-blur">
      <div className="mx-auto max-w-6xl px-5 py-8 sm:px-6">
        <nav
          aria-label="Legal"
          className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-white/65"
        >
          {LEGAL_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="hover:text-kos-gold transition"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <p className="mt-4 text-center text-sm font-medium text-kos-gold">
          {tagline}
        </p>
        <p className="mt-2 text-center text-xs text-white/45">
          © {new Date().getFullYear()} KosEdge Analytics
        </p>
      </div>
    </footer>
  );
}
