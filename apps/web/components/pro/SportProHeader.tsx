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
    <header className="sticky top-0 z-40 border-b border-kos-border/80 bg-kos-black/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-col gap-0 px-4 sm:px-6">
        <div className="flex items-center justify-between gap-4 py-3">
          <Link href="/" className="flex shrink-0 items-center gap-2.5">
            <Image
              src="/brand/kosedge-logo.png"
              alt="Kos Edge Analytics"
              width={140}
              height={42}
              priority
              className="h-8 w-auto sm:h-9"
            />
            <div className="leading-tight">
              <div className="text-base font-extrabold tracking-wide uppercase text-kos-text sm:text-lg">
                Kos Edge
              </div>
              <div className="hidden text-[10px] tracking-[0.18em] uppercase text-kos-text/55 sm:block">
                {tagline}
              </div>
            </div>
          </Link>

          {showSportsNav ? (
            <nav
              className="flex max-w-[58%] flex-wrap items-center justify-end gap-1 sm:max-w-none sm:gap-1.5"
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
                        ? "rounded-md border border-kos-gold/45 bg-kos-gold/15 px-2 py-1 text-xs font-semibold text-kos-gold sm:px-2.5 sm:text-sm"
                        : "rounded-md border border-transparent px-2 py-1 text-xs text-kos-text/75 hover:border-kos-border hover:bg-kos-surface/40 hover:text-kos-text sm:px-2.5 sm:text-sm"
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
          className="-mx-1 flex gap-1 overflow-x-auto pb-3 pt-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          aria-label={`${sportLabel} research desk`}
        >
          {primaryNav.map((item) => {
            const active = isSportNavActive(pathname, item.href, activeSport);
            return (
              <Link
                key={`${item.label}-${item.href}`}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "shrink-0 rounded-md border border-kos-gold/40 bg-kos-gold/12 px-2.5 py-1.5 text-xs font-semibold text-kos-gold whitespace-nowrap"
                    : "shrink-0 rounded-md border border-transparent px-2.5 py-1.5 text-xs font-medium text-kos-text/70 whitespace-nowrap hover:border-white/10 hover:bg-white/5 hover:text-kos-text"
                }
              >
                {item.label}
              </Link>
            );
          })}
          <Link
            href={`/pro/${activeSport}/overview#tools`}
            className="shrink-0 rounded-md border border-transparent px-2.5 py-1.5 text-xs font-medium text-kos-text/50 whitespace-nowrap hover:text-kos-text/80"
          >
            More tools
          </Link>
        </nav>
      </div>
    </header>
  );
}
