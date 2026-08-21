import type { Metadata } from "next";
import Link from "next/link";
import { MODEL_TRANSPARENCY_HREF } from "@/lib/model-transparency-hub";

export const metadata: Metadata = {
  title: "How to read the NFL desk",
  description:
    "Model, KEI, and product surfaces live on Model Transparency. Research estimates, not a tip service.",
};

export default function NflLaunchNotesPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-10">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-kos-gold">
        Week 1 REG live · PRE off board
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-kos-text sm:text-4xl">
        How to read the NFL desk
      </h1>
      <p className="mt-3 text-base leading-7 text-kos-text/75">
        Model, KEI, Edge / Tag, and every product surface are explained on one
        hub. Boards stay clean on purpose.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href={MODEL_TRANSPARENCY_HREF}
          className="rounded-xl border border-kos-gold/40 bg-kos-gold/15 px-4 py-2 text-sm font-semibold text-kos-gold hover:border-kos-gold/55"
        >
          Model Transparency
        </Link>
        <Link
          href="/pro/nfl/overview"
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35"
        >
          ← NFL Overview
        </Link>
        <Link
          href="/edge-board/nfl"
          className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-kos-text hover:border-kos-gold/35"
        >
          Edge Board
        </Link>
      </div>

      <p className="mt-8 text-sm text-kos-text/55">
        Public long-form stays on{" "}
        <Link href="/methodology" className="text-kos-gold/80 hover:underline">
          Methodology
        </Link>{" "}
        and{" "}
        <Link href="/disclaimer" className="text-kos-gold/80 hover:underline">
          Disclaimer
        </Link>
        .
      </p>
    </main>
  );
}
