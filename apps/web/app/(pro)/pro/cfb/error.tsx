"use client";

import Link from "next/link";

export default function CfbProError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const message = error?.message || "Unknown error";
  const modelDown =
    /timed out|unreachable|fetch failed|502|503|500|model/i.test(message);

  return (
    <main className="mx-auto max-w-3xl px-4 py-16 text-kos-text">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
        CFB research desk
      </p>
      <h1 className="mt-2 text-2xl font-semibold">
        {modelDown ? "Model unreachable" : "Desk failed to open"}
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-kos-text/70">
        {modelDown
          ? "The CFB season engine did not return in time. This is a research desk, not a black frame — retry or use Edge Board (KEI vs market)."
          : "The CFB Pro desk hit an unexpected error. Retry, or open a known-good surface."}
      </p>
      <p className="mt-3 rounded-lg border border-white/10 bg-black/35 px-3 py-2 text-xs text-kos-text/60">
        {message}
        {error.digest ? ` · digest ${error.digest}` : ""}
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => reset()}
          className="min-h-11 rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 text-sm font-semibold text-kos-gold"
        >
          Retry
        </button>
        <Link
          href="/pro/cfb/slate?week=1"
          className="min-h-11 inline-flex items-center rounded-xl border border-white/15 px-4 text-sm font-semibold text-kos-text"
        >
          Official slate
        </Link>
        <Link
          href="/edge-board/cfb?week=1"
          className="min-h-11 inline-flex items-center rounded-xl border border-white/15 px-4 text-sm font-semibold text-kos-text"
        >
          Edge Board
        </Link>
      </div>
    </main>
  );
}
