export default function MatchupPage({
  params,
}: {
  params: { sport: string; date: string; slug: string };
}) {
  return (
    <main>
      <h2 className="text-2xl font-semibold">Matchup</h2>
      <p className="mt-2 text-kos-text/70">
        {params.sport.toUpperCase()} · {params.date} · {params.slug}
      </p>

      <div className="mt-8 grid gap-6">
        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h3 className="text-lg font-semibold">Fair Lines vs Market</h3>
          <p className="mt-2 text-kos-text/80">
            Placeholder. (Model reference + best available numbers will live
            here.)
          </p>
        </section>

        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h3 className="text-lg font-semibold">Matchup Context</h3>
          <p className="mt-2 text-kos-text/80">
            Placeholder. (Short-form informational write-up.)
          </p>
        </section>

        <section className="rounded-2xl border border-kos-border bg-kos-surface/40 p-6">
          <h3 className="text-lg font-semibold">Execution & Availability</h3>
          <p className="mt-2 text-kos-text/80">
            Placeholder. (Book matrix, key numbers, dispersion.)
          </p>
        </section>
      </div>
    </main>
  );
}
