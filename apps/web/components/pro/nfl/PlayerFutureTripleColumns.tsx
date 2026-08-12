import {
  CURRENT_YTD_TOOLTIP,
  formatCurrentOddsWithBook,
  formatCurrentYtd,
  formatProjectedValue,
  type PlayerFutureCurrentKind,
  type PlayerFutureOddsSnap,
} from "@/lib/nfl-player-futures";

/**
 * Shared Projected | Current | Current odds cells for NFL player futures.
 * Desktop table headers + stacked mobile card fields use the same meanings.
 */

export function PlayerFutureColumnHeaders({
  projectedLabel = "Projected",
  projectedTitle,
}: {
  projectedLabel?: string;
  projectedTitle?: string;
}) {
  return (
    <>
      <th
        className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65"
        title={projectedTitle}
      >
        {projectedLabel}
      </th>
      <th
        className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65"
        title={CURRENT_YTD_TOOLTIP}
      >
        Current
      </th>
      <th className="border-b border-white/10 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-kos-text/65">
        Current odds
      </th>
    </>
  );
}

export function PlayerFutureTripleCell({
  projected,
  current,
  currentKind,
  odds,
  projectedDigits = 0,
  currentDigits = 0,
  projectedUnit,
  projectedPercent = false,
  projectedSubLabel,
}: {
  projected: number | null | undefined;
  current: number | null | undefined;
  currentKind: PlayerFutureCurrentKind;
  odds?: PlayerFutureOddsSnap | null;
  projectedDigits?: number;
  currentDigits?: number;
  projectedUnit?: string;
  projectedPercent?: boolean;
  /** Quiet sublabel under projected (e.g. "Award Score", "yds"). */
  projectedSubLabel?: string;
}) {
  const proj = formatProjectedValue(projected, {
    digits: projectedDigits,
    unit: projectedUnit,
    percent: projectedPercent,
  });
  const cur = formatCurrentYtd(current, currentKind, currentDigits);
  const oddsFmt = formatCurrentOddsWithBook(odds);

  return (
    <>
      <td className="border-b border-white/5 px-3 py-2">
        <div className="text-sm font-semibold tabular-nums text-kos-gold">
          {proj}
        </div>
        {projectedSubLabel ? (
          <div className="text-[11px] uppercase tracking-wide text-kos-text/45">
            {projectedSubLabel}
          </div>
        ) : null}
      </td>
      <td
        className="border-b border-white/5 px-3 py-2 text-sm tabular-nums text-kos-text/85"
        title={CURRENT_YTD_TOOLTIP}
      >
        {cur}
      </td>
      <td className="border-b border-white/5 px-3 py-2">
        <div className="text-sm tabular-nums text-kos-text/85">
          {oddsFmt.price}
        </div>
        {oddsFmt.book && oddsFmt.price !== "—" ? (
          <div className="text-[11px] text-kos-text/45">{oddsFmt.book}</div>
        ) : null}
      </td>
    </>
  );
}

/** Mobile card strip — same three fields, quiet labels. */
export function PlayerFutureMobileFields({
  projected,
  current,
  currentKind,
  odds,
  projectedDigits = 0,
  currentDigits = 0,
  projectedUnit,
  projectedPercent = false,
  projectedLabel = "Projected",
}: {
  projected: number | null | undefined;
  current: number | null | undefined;
  currentKind: PlayerFutureCurrentKind;
  odds?: PlayerFutureOddsSnap | null;
  projectedDigits?: number;
  currentDigits?: number;
  projectedUnit?: string;
  projectedPercent?: boolean;
  projectedLabel?: string;
}) {
  const proj = formatProjectedValue(projected, {
    digits: projectedDigits,
    unit: projectedUnit,
    percent: projectedPercent,
  });
  const cur = formatCurrentYtd(current, currentKind, currentDigits);
  const oddsFmt = formatCurrentOddsWithBook(odds);

  return (
    <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
          {projectedLabel}
        </dt>
        <dd className="mt-0.5 text-sm font-semibold tabular-nums text-kos-gold">
          {proj}
        </dd>
      </div>
      <div title={CURRENT_YTD_TOOLTIP}>
        <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
          Current
        </dt>
        <dd className="mt-0.5 text-sm tabular-nums text-kos-text/85">{cur}</dd>
      </div>
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
          Odds
        </dt>
        <dd className="mt-0.5 text-sm tabular-nums text-kos-text/85">
          {oddsFmt.price}
        </dd>
      </div>
    </dl>
  );
}

export function CurrentYtdHint({ className = "" }: { className?: string }) {
  return (
    <p
      className={`text-[11px] text-kos-text/45 ${className}`}
      title={CURRENT_YTD_TOOLTIP}
    >
      {CURRENT_YTD_TOOLTIP}
    </p>
  );
}
