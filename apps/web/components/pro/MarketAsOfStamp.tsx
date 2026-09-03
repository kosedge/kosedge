import { marketAsOfStamp, type MarketAsOfKind } from "@/lib/market-asof-stamp";

type Props = {
  asOf: string | null | undefined;
  books?: string[] | null;
  kind?: MarketAsOfKind;
  className?: string;
  /** Optional test id for Vitest / Playwright. */
  "data-testid"?: string;
};

/**
 * One-line honest market as-of stamp. Blank source → unavailable copy (no fake clock).
 */
export function MarketAsOfStamp({
  asOf,
  books,
  kind = "market",
  className,
  "data-testid": testId = "market-asof-stamp",
}: Props) {
  const stamp = marketAsOfStamp({ asOf, books, kind });
  const tone = stamp.missing
    ? "text-amber-200/80"
    : stamp.stale
      ? "text-amber-300/90"
      : "text-gray-400";

  return (
    <p
      data-testid={testId}
      data-missing={stamp.missing ? "true" : "false"}
      data-stale={stamp.stale ? "true" : "false"}
      className={["text-xs", tone, className].filter(Boolean).join(" ")}
    >
      {stamp.text}
    </p>
  );
}
