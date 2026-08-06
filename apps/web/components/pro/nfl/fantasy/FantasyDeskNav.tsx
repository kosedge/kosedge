import Link from "next/link";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";

type DeskSurface = "rankings" | "builder" | "mock";

type Props = {
  active: DeskSurface;
  scoring: FantasyScoringProfile;
  className?: string;
};

const LINKS: { id: DeskSurface; label: string; href: (s: FantasyScoringProfile) => string }[] = [
  {
    id: "rankings",
    label: "Rankings",
    href: (s) => `/pro/nfl/fantasy?scoring=${s}`,
  },
  {
    id: "builder",
    label: "Builder",
    href: (s) => `/pro/nfl/fantasy/builder?scoring=${s}`,
  },
  {
    id: "mock",
    label: "Mock",
    href: (s) => `/pro/nfl/fantasy/mock?scoring=${s}`,
  },
];

/** Shared Rankings → Builder → Mock flow strip; preserves scoring. */
export function FantasyDeskNav({ active, scoring, className = "" }: Props) {
  return (
    <nav
      aria-label="Fantasy Draft Desk"
      className={`flex flex-wrap gap-2 ${className}`}
    >
      {LINKS.map((link) => {
        const isActive = link.id === active;
        return (
          <Link
            key={link.id}
            href={link.href(scoring)}
            className={`min-h-10 min-w-[5.5rem] rounded-xl border px-3 py-2 text-center text-sm font-semibold transition active:scale-[0.98] ${
              isActive
                ? "border-kos-gold/45 bg-kos-gold/15 text-kos-gold"
                : "border-white/10 bg-white/5 text-kos-text/70 hover:border-kos-gold/30 hover:text-kos-text"
            }`}
            aria-current={isActive ? "page" : undefined}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
