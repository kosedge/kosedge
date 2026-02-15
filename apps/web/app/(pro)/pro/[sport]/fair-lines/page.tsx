import Link from "next/link";
import { getSport } from "@/lib/sports";

export default function FairLinesPage({ params }: { params: { sport: string } }) {
  const sport = getSport(params.sport);
  const sportName = sport?.fullName ?? params.sport.toUpperCase();
  const base = `/pro/${params.sport}`;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-2xl font-semibold text-kos-text">{sportName} Fair Lines</h2>
          <p className="mt-2 text-kos-text/70">
            Model reference vs market prices. Neutral presentation—no picks.
          </p>
        </div>
        <Link
          href={`${base}/overview`}
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          Back to Hub
        </Link>
      </div>
      <div className="mt-8 rounded-2xl border border-kos-border bg-kos-surface/30 p-8">
        <p className="text-kos-text/60">Shell placeholder. Wire model for fair lines.</p>
      </div>
    </main>
  );
}