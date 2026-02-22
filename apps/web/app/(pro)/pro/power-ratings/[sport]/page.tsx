import Link from "next/link";
import { getSport } from "@/lib/sports";
import { getPowerRatings } from "@/lib/power-ratings";
import { PowerRatingsTable } from "./PowerRatingsTable";

export const dynamic = "force-dynamic";

export default async function PowerRatingsSportPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const ratings = getPowerRatings(sportKey);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-kos-text">
            {sportName} — Power Ratings
          </h1>
          <p className="mt-2 text-kos-text/70">
            Team strength and model rankings.
          </p>
        </div>
        <Link
          href="/pro/power-ratings"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          ← All sports
        </Link>
      </div>

      <div className="mt-8">
        <PowerRatingsTable ratings={ratings} sportName={sportName} />
      </div>
    </main>
  );
}
