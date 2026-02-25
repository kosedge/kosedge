type Game = {
  id?: string;
  homeTeam: string;
  awayTeam: string;
  commenceTime?: string;
  projSpreadHome: number | null;
  projTotal: number | null;
};

export function KeiLinesTable({
  games,
  sportName,
}: {
  games: Game[];
  sportName: string;
}) {
  if (games.length === 0) {
    return (
      <div className="rounded-2xl border border-kos-border bg-kos-surface/30 p-8 text-center">
        <p className="text-kos-text/60">
          No KEI lines for {sportName} yet. Run the pipeline export to generate{" "}
          <code className="text-kos-gold/80">data/processed/kei_lines_*.json</code>.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-kos-border bg-kos-surface/30">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-kos-border bg-kos-surface/50">
            <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
              Away
            </th>
            <th className="px-4 py-3 text-sm font-semibold text-kos-text/80">
              Home
            </th>
            <th className="px-4 py-3 text-sm font-semibold text-kos-gold">
              Proj line (H)
            </th>
            <th className="px-4 py-3 text-sm font-semibold text-kos-gold">
              Proj O/U
            </th>
          </tr>
        </thead>
        <tbody>
          {games.map((g, i) => (
            <tr
              key={g.id ?? i}
              className="border-b border-kos-border/50 hover:bg-kos-surface/40"
            >
              <td className="px-4 py-3 font-medium text-kos-text">
                {g.awayTeam}
              </td>
              <td className="px-4 py-3 font-medium text-kos-text">
                {g.homeTeam}
              </td>
              <td className="px-4 py-3 text-kos-gold">
                {g.projSpreadHome != null
                  ? g.projSpreadHome > 0
                    ? `+${g.projSpreadHome.toFixed(1)}`
                    : g.projSpreadHome.toFixed(1)
                  : "—"}
              </td>
              <td className="px-4 py-3 text-kos-gold">
                {g.projTotal != null ? g.projTotal.toFixed(1) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
