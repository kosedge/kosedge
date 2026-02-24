import Link from "next/link";
import { getSport } from "@/lib/sports";
import { getKeiLines } from "@/lib/kei-lines";
import { KeiLinesTable } from "./KeiLinesTable";
import { NcaamKeiLinesClient } from "./NcaamKeiLinesClient";

export const dynamic = "force-dynamic";

export default async function KeiLinesSportPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const games = getKeiLines(sportKey);
  const isNcaam = sportKey === "ncaam";

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl font-semibold text-kos-text">
            {sportName} — KEI Lines
          </h1>
          <p className="mt-2 text-kos-text/70">
            {isNcaam
              ? "Projected spread and over/under by game date. Use the dropdown to pick a day."
              : "Projected spread and over/under for each game."}
          </p>
        </div>
        <Link
          href="/pro/kei-lines"
          className="rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
        >
          ← All sports
        </Link>
      </div>

      <div className="mt-8">
        {isNcaam ? (
          <NcaamKeiLinesClient games={games} sportName={sportName} />
        ) : (
          <KeiLinesTable games={games} sportName={sportName} />
        )}
      </div>
    </main>
  );
}
