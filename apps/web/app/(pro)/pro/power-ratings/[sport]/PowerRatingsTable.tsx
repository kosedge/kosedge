type Row = {
  rank: number;
  team: string;
  teamNorm?: string;
  rating: number;
  adjem?: number;
  torvik?: number;
  barthag?: number;
  year?: number;
};

export function PowerRatingsTable({
  ratings,
  sportName,
}: {
  ratings: Row[];
  sportName: string;
}) {
  if (ratings.length === 0) {
    return (
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-8 text-center">
        <p className="text-kos-text/60">
          No power ratings for {sportName} yet. Run the pipeline export to
          generate{" "}
          <code className="text-kos-gold/80">
            data/processed/power_ratings_*.json
          </code>
          .
        </p>
      </div>
    );
  }

  const hasDetails = ratings.some(
    (r) => r.adjem != null || r.torvik != null || r.barthag != null
  );

  return (
    <div className="overflow-hidden rounded-2xl border border-kos-border bg-kos-surface/30">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-kos-border bg-kos-surface/50">
            <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
              Rank
            </th>
            <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
              Team
            </th>
            <th className="px-4 py-3 text-sm font-semibold text-kos-gold">
              Rating
            </th>
            {hasDetails && (
              <>
                <th className="px-4 py-3 text-sm font-semibold text-kos-text/70">
                  AdjEM
                </th>
                <th className="px-4 py-3 text-sm font-semibold text-kos-text/70">
                  Torvik
                </th>
                <th className="px-4 py-3 text-sm font-semibold text-kos-text/70">
                  Barthag
                </th>
              </>
            )}
          </tr>
        </thead>
        <tbody>
          {ratings.map((r, i) => (
            <tr
              key={r.teamNorm ?? r.team ?? i}
              className="border-b border-kos-border/50 hover:bg-kos-surface/40"
            >
              <td className="px-4 py-3 font-medium text-kos-text/80">
                {r.rank}
              </td>
              <td className="px-4 py-3 font-medium text-kos-text capitalize">
                {(r.team || r.teamNorm || "").replace(/_/g, " ")}
              </td>
              <td className="px-4 py-3 text-kos-gold font-semibold">
                {typeof r.rating === "number" ? r.rating.toFixed(2) : "—"}
              </td>
              {hasDetails && (
                <>
                  <td className="px-4 py-3 text-kos-text/70">
                    {r.adjem != null ? r.adjem.toFixed(2) : "—"}
                  </td>
                  <td className="px-4 py-3 text-kos-text/70">
                    {r.torvik != null ? r.torvik.toFixed(2) : "—"}
                  </td>
                  <td className="px-4 py-3 text-kos-text/70">
                    {r.barthag != null ? r.barthag.toFixed(2) : "—"}
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
