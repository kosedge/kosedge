import type { DriverChipView } from "@/lib/nfl-true-pr-format";

/**
 * Compact driver chips under a team's intrinsic PR.
 * Mobile-first wrap — no horizontal doom scroll.
 */
export default function TruePrDriverChips({
  chips,
}: {
  chips: DriverChipView[];
}) {
  if (chips.length === 0) {
    return (
      <p className="mt-2 text-[11px] text-kos-text/45">
        Drivers thin on this path — no invented confidence.
      </p>
    );
  }

  return (
    <ul className="mt-2 flex flex-wrap gap-1.5">
      {chips.map((chip) => (
        <li
          key={chip.key}
          className={
            chip.muted
              ? "max-w-full rounded-md border border-white/10 bg-white/[0.03] px-2 py-1"
              : "max-w-full rounded-md border border-white/12 bg-black/40 px-2 py-1"
          }
          title={
            chip.framing
              ? `${chip.detail} — ${chip.framing}`
              : chip.detail || undefined
          }
        >
          <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-0.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-kos-text/45">
              {chip.title}
            </span>
            <span
              className={
                chip.muted
                  ? "text-xs font-medium text-kos-text/55"
                  : "text-xs font-semibold text-kos-text/85"
              }
            >
              {chip.value}
            </span>
            {chip.approximate ? (
              <span className="text-[10px] text-amber-100/70">approx</span>
            ) : null}
            {chip.key === "proj_sos" ? (
              <span className="text-[10px] text-kos-text/40">outlook</span>
            ) : null}
          </div>
          {chip.detail ? (
            <p className="mt-0.5 max-w-[18rem] text-[11px] leading-snug text-kos-text/55 sm:max-w-none">
              {chip.detail}
            </p>
          ) : null}
          {chip.framing ? (
            <p className="mt-0.5 text-[10px] leading-snug text-kos-text/40">
              {chip.framing}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
