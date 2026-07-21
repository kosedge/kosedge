import Link from "next/link";
import { NflDataFreshnessBanner } from "@/components/pro/NflDataFreshnessBanner";
import { SPORTS } from "@/lib/sports";

export default async function ProLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ sport: string }> | { sport: string };
}) {
  const resolved = await Promise.resolve(params);
  const sport = String(resolved.sport || "").toLowerCase();

  return (
    <div className="min-h-screen bg-kos-black text-kos-text">
      <header className="border-b border-kos-border bg-kos-surface/30">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-3">
            <span className="text-lg font-semibold tracking-tight">
              Kos Edge
            </span>
            <span className="rounded-full border border-kos-border bg-kos-surface/40 px-2 py-0.5 text-xs text-kos-text/70">
              Pro Hub
            </span>
          </Link>

          <nav className="flex flex-wrap items-center gap-2">
            {SPORTS.map((s) => (
              <Link
                key={s.key}
                href={`/pro/${s.key}`}
                className="rounded-lg border border-transparent px-3 py-1.5 text-sm text-kos-text/80 hover:border-kos-border hover:bg-kos-surface/40 hover:text-kos-text"
              >
                {s.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {sport === "nfl" ? <NflDataFreshnessBanner /> : null}

      {children}
    </div>
  );
}
