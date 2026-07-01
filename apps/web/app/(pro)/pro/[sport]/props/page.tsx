import Link from "next/link";
import { getSport, supportsPropsFantasy } from "@/lib/sports";

export default function PropsPage({ params }: { params: { sport: string } }) {
  const sport = getSport(params.sport);
  const sportName = sport?.fullName ?? params.sport.toUpperCase();
  const base = `/pro/${params.sport}`;
  const propsEnabled = supportsPropsFantasy(params.sport);

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
        <p className="text-kos-text/60">
          {propsEnabled
            ? "Soft-launch placeholder. Props module is wired and awaiting league-specific data services."
            : "Data pending. Props and fantasy cards will unlock once sport-level player feeds meet launch confidence thresholds."}
        </p>
      </div>
    </main>
  );
}
