import Link from "next/link";
import { redirect } from "next/navigation";
import { getSport, supportsPropsFantasy } from "@/lib/sports";

export default async function PropsPage({
  params,
}: {
  params: Promise<{ sport: string }>;
}) {
  const { sport: sportKey } = await params;
  if (sportKey === "nfl") {
    redirect("/pro/nfl/props");
  }

  const sport = getSport(sportKey);
  const sportName = sport?.fullName ?? sportKey.toUpperCase();
  const base = `/pro/${sportKey}`;
  const propsEnabled = supportsPropsFantasy(sportKey);

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-end justify-between gap-6">
        <div>
          <h2 className="text-2xl font-semibold text-kos-text">
            {sportName} Props
          </h2>
          <p className="mt-2 text-kos-text/70">
            {propsEnabled
              ? "Prop analyzer and edge screens. Player props, team props, and alternate lines."
              : "Premium placeholder: props and fantasy modules are staged for this college sport pending player-data validation."}
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
        <p className="text-sm font-semibold text-kos-gold">
          {propsEnabled ? "Not wired yet" : "Coming soon"}
        </p>
        <p className="mt-2 text-kos-text/60">
          {propsEnabled
            ? `${sportName} props are staged but not connected to a live model board. NFL props are live.`
            : "Data pending. Props unlock once sport-level player feeds meet launch confidence thresholds."}
        </p>
        {propsEnabled ? (
          <Link
            href="/pro/nfl/props"
            className="mt-4 inline-flex rounded-xl border border-kos-gold/35 bg-kos-gold/10 px-4 py-2 text-sm font-semibold text-kos-gold transition hover:border-kos-gold/55"
          >
            Open NFL props board →
          </Link>
        ) : null}
      </div>
    </main>
  );
}
