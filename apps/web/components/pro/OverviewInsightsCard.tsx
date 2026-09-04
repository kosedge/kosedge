import Link from "next/link";

/**
 * Shared Insights card for flagship Overview pages (NFL / NBA / MLB).
 * Same visual language across sports — only sport label/href differ.
 */
export default function OverviewInsightsCard({
  sportKey,
  sportLabel,
}: {
  sportKey: string;
  sportLabel: string;
}) {
  return (
    <Link
      href={`/insights/sports/${sportKey}`}
      className="rounded-2xl border border-kos-gold/25 bg-kos-gold/5 p-5 transition hover:border-kos-gold/45"
    >
      <h3 className="font-semibold text-kos-gold">Insights</h3>
      <p className="mt-2 text-sm text-kos-text/70">
        Desk notes and doctrine for {sportLabel} — This Week and house rules.
      </p>
    </Link>
  );
}
