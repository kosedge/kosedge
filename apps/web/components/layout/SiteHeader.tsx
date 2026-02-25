import Image from "next/image";
import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
      <Link href="/" className="flex items-center gap-3">
        <Image
          src="/Brand/kosedge-logo.png"
          alt="Kos Edge Analytics"
          width={160}
          height={48}
          priority
          className="h-10 w-auto"
        />
        <div className="leading-tight">
          <div className="text-xl font-extrabold tracking-wide uppercase">Kos Edge</div>
          <div className="-mt-1 text-xs text-white/60 tracking-[0.2em] uppercase">
            Analytics
          </div>
        </div>
      </Link>

      <nav className="hidden md:flex items-center gap-6 text-sm text-white/70">
        <Link className="hover:text-white" href="/methodology">Methodology</Link>
        <Link className="hover:text-white" href="/insights">Insights</Link>
        <Link className="hover:text-white" href="/about">About</Link>
        <Link className="hover:text-white" href="/disclaimer">Disclaimer</Link>
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