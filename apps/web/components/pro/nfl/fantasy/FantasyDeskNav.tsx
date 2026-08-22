import Link from "next/link";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";
import { Fragment } from "react";

type DeskSurface = "rankings" | "builder" | "mock";

type Props = {
  active: DeskSurface;
  scoring: FantasyScoringProfile;
  className?: string;
};

const LINKS: {
  id: DeskSurface;
  label: string;
  href: (s: FantasyScoringProfile) => string;
}[] = [
  {
    id: "rankings",
    label: "Draft board",
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

/** Shared Draft board → Builder → Mock flow strip; preserves scoring. */
export function FantasyDeskNav({ active, scoring, className = "" }: Props) {
  return (
    <div className={className}>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-kos-text/40">
        Draft flow
      </p>
      <nav
        aria-label="Draft board, Builder, Mock"
        className="flex flex-wrap items-center gap-1.5 sm:gap-2"
      >
        {LINKS.map((link, index) => {
          const isActive = link.id === active;
          return (
            <Fragment key={link.id}>
              {index > 0 ? (
                <span aria-hidden className="px-0.5 text-sm text-kos-text/30">
                  →
                </span>
              ) : null}
              <Link
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
            </Fragment>
          );
        })}
      </nav>
    </div>
  );
}
