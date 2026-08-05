"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SPORTS } from "@/lib/sports";
import {
  SPORT_TAGLINE,
  getSportPrimaryNav,
  isSportNavActive,
  sportHubHref,
} from "@/lib/sport-pro-nav";

export default function SportProHeader({
  activeSport,
  showSportsNav = true,
  tagline = SPORT_TAGLINE,
}: {
  activeSport: string;
  showSportsNav?: boolean;
  tagline?: string;
}) {
  const pathname = usePathname();
  const primaryNav = getSportPrimaryNav(activeSport);
  const sportLabel =
    SPORTS.find((s) => s.key === activeSport)?.label ??
    activeSport.toUpperCase();

  return (
    <header className="sticky top-0 z-40 border-b border-kos-border/80 bg-kos-black/90 backdrop-blur-xl [--kos-pro-header-h:6.75rem] sm:[--kos-pro-header-h:7.5rem]">
      <div className="mx-auto flex max-w-7xl flex-col gap-0 px-4 sm:px-6">
        <div className="flex items-center justify-between gap-3 py-2 sm:gap-4 sm:py-3">
          <Link
            href="/"
            className="flex min-h-11 shrink-0 items-center gap-2.5"
          >
            <Image
              src="/brand/kosedge-logo.png"
              alt="Kos Edge Analytics"
              width={160}
              height={48}
              priority
              className="h-10 w-auto sm:h-11"
            />
            <div className="leading-tight">
              <div className="text-base font-extrabold tracking-wide text-kos-text sm:text-lg">
                KosEdge
              </div>
              <div className="hidden text-[10px] tracking-[0.14em] uppercase text-kos-text/60 sm:block">
                {tagline}
              </div>
            </div>
          </Link>

          {showSportsNav ? (
            <nav
              className="-mx-1 flex max-w-[62%] items-center gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:max-w-none sm:flex-wrap sm:justify-end sm:gap-1.5 sm:overflow-visible"
              aria-label="Sport hubs"
            >
              {SPORTS.map((s) => {
                const active = activeSport === s.key;
                return (
                  <Link
                    key={s.key}
                    href={sportHubHref(s.key)}
                    aria-current={active ? "page" : undefined}
                    className={
                      active
                        ? "inline-flex min-h-11 shrink-0 items-center rounded-md border border-kos-gold/45 bg-kos-gold/15 px-2.5 text-sm font-semibold text-kos-gold sm:min-h-0 sm:px-2.5 sm:py-1 sm:text-sm"
                        : "inline-flex min-h-11 shrink-0 items-center rounded-md border border-transparent px-2.5 text-sm text-kos-text/75 hover:border-kos-border hover:bg-kos-surface/40 hover:text-kos-text sm:min-h-0 sm:px-2.5 sm:py-1 sm:text-sm"
                    }
                  >
                    {s.label}
                  </Link>
                );
              })}
            </nav>
          ) : null}
        </div>

        <nav
          className="-mx-1 flex gap-1 overflow-x-auto pb-2 pt-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:pb-3"
          aria-label={`${sportLabel} research desk`}
        >
          {primaryNav.map((item) => {
            const active = isSportNavActive(pathname, item.href, activeSport);
            const edgeBoard = item.emphasis === "gold";
            const inactiveClass = edgeBoard
              ? "inline-flex min-h-11 shrink-0 items-center rounded-md border border-kos-gold/35 bg-kos-gold/8 px-3 text-sm font-semibold text-kos-gold whitespace-nowrap shadow-[0_0_14px_rgba(245,185,66,0.12)] hover:border-kos-gold/50 hover:bg-kos-gold/14 hover:shadow-[0_0_18px_rgba(245,185,66,0.2)] sm:min-h-0 sm:px-2.5 sm:py-1.5 sm:text-xs"
              : "inline-flex min-h-11 shrink-0 items-center rounded-md border border-transparent px-3 text-sm font-medium text-kos-text/70 whitespace-nowrap hover:border-white/10 hover:bg-white/5 hover:text-kos-text sm:min-h-0 sm:px-2.5 sm:py-1.5 sm:text-xs";
            const activeClass = edgeBoard
              ? "inline-flex min-h-11 shrink-0 items-center rounded-md border border-kos-gold/55 bg-kos-gold/18 px-3 text-sm font-semibold text-kos-gold whitespace-nowrap shadow-[0_0_20px_rgba(245,185,66,0.22)] sm:min-h-0 sm:px-2.5 sm:py-1.5 sm:text-xs"
              : "inline-flex min-h-11 shrink-0 items-center rounded-md border border-kos-gold/40 bg-kos-gold/12 px-3 text-sm font-semibold text-kos-gold whitespace-nowrap sm:min-h-0 sm:px-2.5 sm:py-1.5 sm:text-xs";
            return (
              <Link
                key={`${item.label}-${item.href}`}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={active ? activeClass : inactiveClass}
              >
                {item.label}
              </Link>
            );
          })}
          <Link
            href={`/pro/${activeSport}/overview#tools`}
            className="inline-flex min-h-11 shrink-0 items-center rounded-md border border-transparent px-3 text-sm font-medium text-kos-text/50 whitespace-nowrap hover:text-kos-text/80 sm:min-h-0 sm:px-2.5 sm:py-1.5 sm:text-xs"
          >
            More tools
          </Link>
        </nav>
      </div>
    </header>
  );
}
