import Link from "next/link";
import { redirect } from "next/navigation";
import { getSport } from "@/lib/sports";

export default async function TeamsPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  if (sportKey === "nfl") {
    redirect("/pro/nfl/teams");
  }

  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const base = `/pro/${sportKey}`;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-2xl font-semibold text-kos-text">
            {sportName} Teams
          </h2>
          <p className="mt-2 text-kos-text/70">
            Weekly team summaries, power ratings.
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
        <p className="text-kos-text/60">
          Shell placeholder. Wire content source.
        </p>
      </div>
    </main>
  );
}
