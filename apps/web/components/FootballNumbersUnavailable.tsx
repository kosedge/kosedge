import Link from "next/link";
import {
  FOOTBALL_PUBLIC_NUMBERS_HEADING,
  footballPublicNumbersUnavailableMessage,
  publicEdgeBoardSports,
} from "@/lib/cfb-edge-board-public";
import { SPORTS } from "@/lib/sports";

/**
 * Fail-closed NFL/CFB public number chrome. Same copy on Edge Board,
 * homepage hero, edges, KEI/fair, power, and week-stale slates.
 * Do not invent KEI / fair / PLAY or render a ghost table.
 */
export default function FootballNumbersUnavailable({
  sport = "cfb",
  showSelector = false,
  compact = false,
  title,
}: {
  sport?: string;
  showSelector?: boolean;
  compact?: boolean;
  /** Optional surface label under Coming soon (e.g. "NFL Power Ratings"). */
  title?: string;
}) {
  const selectorSports = publicEdgeBoardSports(SPORTS);
  const key = String(sport ?? "")
    .trim()
    .toLowerCase();
  const sportLabel = key === "nfl" ? "NFL" : key === "cfb" ? "CFB" : "Football";
  const message = footballPublicNumbersUnavailableMessage(key);
  const testId =
    key === "nfl" ? "nfl-edge-board-unavailable" : "cfb-edge-board-unavailable";
  const messageTestId =
    key === "nfl"
      ? "nfl-edge-board-unavailable-message"
      : "cfb-edge-board-unavailable-message";

  return (
    <div
      data-testid={testId}
      data-football-numbers-unavailable={key || "football"}
    >
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
          {FOOTBALL_PUBLIC_NUMBERS_HEADING}
        </h1>
        {title ? (
          <p className="mt-2 text-sm font-semibold text-kos-text/80">{title}</p>
        ) : (
          <p className="mt-2 text-sm font-semibold text-kos-text/80">
            {sportLabel} numbers
          </p>
        )}
        <p
          className={
            compact
              ? "mt-3 text-sm text-amber-100/90"
              : "mt-4 text-base sm:text-lg text-amber-100/90 max-w-2xl mx-auto"
          }
          data-testid={messageTestId}
        >
          {message}
        </p>
      </div>
    </div>
  );
}
