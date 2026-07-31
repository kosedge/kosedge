import Link from "next/link";
import NflProShell from "@/components/pro/nfl/NflProShell";
import { SPORTS } from "@/lib/sports";

export default async function ProSportLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ sport: string }> | { sport: string };
}) {
  const resolved = await Promise.resolve(params);
  const sport = String(resolved.sport || "").toLowerCase();

  if (sport === "nfl") {
    return <NflProShell>{children}</NflProShell>;
  }

  return (
    <div className="min-h-screen bg-kos-black text-kos-text">
      <header className="border-b border-kos-border bg-kos-surface/30">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link
            href="/pro/welcome"
            className="flex shrink-0 items-center gap-3"
          >
            <span className="text-lg font-semibold tracking-tight">
              Kos Edge
            </span>
            <span className="rounded-full border border-kos-border bg-kos-surface/40 px-2 py-0.5 text-xs text-kos-text/70">
              Pro Hub
            </span>
          </Link>

          <nav
            className="flex flex-wrap items-center justify-end gap-1.5 sm:gap-2"
            aria-label="Sport hubs"
          >
            {SPORTS.map((s) => {
              const active = sport === s.key;
              return (
                <Link
                  key={s.key}
                  href={s.key === "nfl" ? "/pro/nfl/overview" : `/pro/${s.key}`}
                  aria-current={active ? "page" : undefined}
                  className={
                    active
                      ? "rounded-lg border border-kos-gold/45 bg-kos-gold/15 px-2.5 py-1.5 text-sm font-semibold text-kos-gold sm:px-3"
                      : "rounded-lg border border-transparent px-2.5 py-1.5 text-sm text-kos-text/80 hover:border-kos-border hover:bg-kos-surface/40 hover:text-kos-text sm:px-3"
                  }
                >
                  {s.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>

      {children}
    </div>
  );
}
