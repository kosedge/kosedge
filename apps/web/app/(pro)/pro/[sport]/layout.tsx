import Link from "next/link";
import { SPORTS } from "@/lib/sports";

export default function ProLayout({ children }: { children: React.ReactNode }) {
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

      {children}
    </div>
  );
}
