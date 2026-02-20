import Link from "next/link";
import type { LegacyEdgeBoardRow } from "./EdgeBoard";

export default function EdgeBoardPreview({
  row,
  articleHref,
}: {
  row: LegacyEdgeBoardRow;
  articleHref: string;
}) {
  return (
    <Link
      href={articleHref}
      className="block rounded-xl border border-white/10 bg-black/30 p-4 hover:border-kos-gold/40 transition"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="font-semibold text-gray-100">
            {row.teamA.name} vs {row.teamB.name}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">{row.time ?? "—"}</div>
        </div>
        <div className="flex gap-4 text-sm tabular-nums">
          <div>
            <div className="text-gray-400 text-xs">Best Line</div>
            <div className="text-kos-gold font-medium">{row.bestLine.top.label}</div>
          </div>
          <div>
            <div className="text-gray-400 text-xs">Best O/U</div>
            <div className="text-kos-gold font-medium">{row.bestOU.top.label}</div>
          </div>
        </div>
      </div>
      <div className="mt-2 text-xs text-kos-gold/80">Read article →</div>
    </Link>
  );
}
