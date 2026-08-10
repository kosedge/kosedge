import type { StatDrop } from "@/lib/edge-board-stat-drop";

/** Compact 2×4 Stat Drop grid — numbers first, always visible slots. */
export default function StatDropPanel({
  drop,
  compact = false,
}: {
  drop: StatDrop;
  compact?: boolean;
}) {
  const cellPad = compact ? "px-2 py-1.5" : "px-2.5 py-2";
  return (
    <div className="w-full">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-kos-gold/90">
          Stat Drop
        </div>
        <div className="text-[10px] text-gray-500">{drop.siteLabel}</div>
      </div>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-white/12 bg-white/10">
        {drop.slots.map((slot) => (
          <div
            key={slot.key}
            className={`${cellPad} bg-black/80 ${
              slot.highlight ? "bg-kos-gold/10" : ""
            }`}
          >
            <div className="text-[9px] uppercase tracking-wide text-gray-500">
              {slot.label}
            </div>
            <div
              className={`mt-0.5 font-semibold tabular-nums leading-tight ${
                slot.highlight ? "text-kos-gold" : "text-gray-100"
              } ${compact ? "text-[12px]" : "text-[13px]"}`}
            >
              {slot.value}
            </div>
            {slot.detail ? (
              <div className="mt-0.5 text-[10px] leading-snug text-gray-500">
                {slot.detail}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}
