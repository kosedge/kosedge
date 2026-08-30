import Link from "next/link";
import type { FantasyScoringProfile } from "@/lib/fantasy/types";
import { Fragment } from "react";

type DeskSurface = "rankings" | "builder" | "mock";
type ResearchSurface = "guillotine" | "sleepers" | "pickem";

type Props = {
  active: DeskSurface;
  scoring: FantasyScoringProfile;
  className?: string;
  /** Highlight on the research strip (Guillotine / Sleepers / Pick’em). */
  researchActive?: ResearchSurface | null;
  /** When false, hide the research strip (draft-only surfaces). Default true. */
  showResearch?: boolean;
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

const RESEARCH_LINKS: {
  id: ResearchSurface;
  label: string;
  href: (s: FantasyScoringProfile) => string;
}[] = [
  {
    id: "guillotine",
    label: "Guillotine",
    href: (s) => `/pro/nfl/fantasy/guillotine?scoring=${s}`,
  },
  {
    id: "sleepers",
    label: "Sleepers",
    href: (s) => `/pro/nfl/fantasy/sleepers?scoring=${s}`,
  },
  {
    id: "pickem",
    label: "Pick’em",
    href: () => `/pro/nfl/fantasy/pickem`,
  },
];

/** Shared Draft board → Builder → Mock flow strip; preserves scoring. */
export function FantasyDeskNav({
  active,
  scoring,
  className = "",
  researchActive = null,
  showResearch = true,
}: Props) {
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

      {showResearch ? (
        <nav
          className="mt-3 flex flex-wrap gap-2"
          aria-label="Fantasy research pages"
        >
          {RESEARCH_LINKS.map((link) => {
            const isActive = researchActive === link.id;
            if (isActive) {
              return (
                <span
                  key={link.id}
                  className="rounded-md border border-kos-gold/40 bg-kos-gold/15 px-3 py-1.5 text-xs font-semibold text-kos-gold"
                >
                  {link.label}
                </span>
              );
            }
            return (
              <Link
                key={link.id}
                href={link.href(scoring)}
                className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-kos-text/75 hover:border-kos-gold/30"
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      ) : null}
    </div>
  );
}
