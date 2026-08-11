import Image from "next/image";
import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
      <Link href="/" className="flex items-center gap-3">
        <Image
          src="/brand/kosedge-logo.png"
          alt="Kos Edge Analytics"
          width={192}
          height={56}
          priority
          className="h-12 w-auto sm:h-14"
        />
        <div className="leading-tight">
          <div className="text-xl font-extrabold tracking-wide text-kos-text sm:text-2xl">
            KosEdge Analytics
          </div>
          <div className="-mt-0.5 text-[11px] text-white/65 tracking-[0.12em] uppercase sm:text-xs">
            Built on Data, Driven by Edge
          </div>
        </div>
      </Link>

      <nav className="hidden md:flex items-center gap-6 text-sm text-white/70">
        <Link className="hover:text-white" href="/methodology">
          Methodology
        </Link>
        <Link className="hover:text-white" href="/insights">
          Insights
        </Link>
        <Link className="hover:text-white" href="/about">
          About
        </Link>
        <Link className="hover:text-white" href="/disclaimer">
          Disclaimer
        </Link>
      </nav>

      <div className="flex items-center gap-3">
        <Link
          href="/insights"
          className="hidden sm:inline-flex items-center rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
        >
          Read Insights
        </Link>
        <Link
          href="/pro"
          className="inline-flex items-center rounded-xl bg-[#F5B942] px-4 py-2 text-sm font-semibold text-black shadow-[0_0_25px_rgba(245,185,66,0.35)] hover:opacity-90"
        >
          Pro
        </Link>
      </div>
    </header>
  );
}
