import Link from "next/link";
import {
  CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE,
  publicEdgeBoardSports,
} from "@/lib/cfb-edge-board-public";
import { SPORTS } from "@/lib/sports";

/**
 * Fail-closed CFB Edge Board chrome. Same copy on the board page,
 * homepage hero, and pro edges entry.
 */
export default function CfbEdgeBoardUnavailable({
  showSelector = false,
  compact = false,
}: {
  showSelector?: boolean;
  compact?: boolean;
}) {
  const selectorSports = publicEdgeBoardSports(SPORTS);

  return (
    <div data-testid="cfb-edge-board-unavailable">
      {showSelector ? (
        <div className="flex flex-wrap gap-2">
          {selectorSports.map((s) => (
            <Link
              key={s.key}
              href={`/edge-board/${s.key}`}
              className="rounded-xl px-3 py-2 text-sm font-semibold transition bg-black/30 border border-white/12 hover:border-edge-green/35 text-gray-300"
            >
              {s.label}
            </Link>
          ))}
        </div>
      ) : null}

      <div
        className={
          compact
            ? "rounded-2xl border border-amber-200/25 bg-black/30 p-6 text-center"
            : "mt-6 rounded-2xl border border-amber-200/25 bg-black/30 p-12 text-center"
        }
      >
        <h1
          className={
            compact
              ? "text-xl font-semibold tracking-tight text-edge-green"
              : "text-3xl sm:text-4xl font-semibold tracking-tight text-edge-green"
          }
        >
          CFB Edge Board
        </h1>
        <p
          className={
            compact
              ? "mt-3 text-sm text-amber-100/90"
              : "mt-4 text-base sm:text-lg text-amber-100/90 max-w-2xl mx-auto"
          }
          data-testid="cfb-edge-board-unavailable-message"
        >
          {CFB_EDGE_BOARD_UNAVAILABLE_MESSAGE}
        </p>
      </div>
    </div>
  );
}
