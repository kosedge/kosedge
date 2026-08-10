import type { StatDrop } from "@/lib/edge-board-stat-drop";

/** Mobile-scannable Stat Drop strip — always renders all 8 slots. */
export default function EdgeBoardStatDrop({
  drop,
  compact = false,
}: {
  drop: StatDrop;
  compact?: boolean;
}) {
  return (
    <div
      className={
        compact
          ? "mt-2"
          : "mt-2 rounded-lg border border-white/10 bg-black/50 p-2.5"
      }
      data-testid="edge-board-stat-drop"
      data-has-power={drop.hasPower ? "1" : "0"}
    >
      {!compact ? (
        <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-kos-gold/90">
          Stat Drop
        </div>
      ) : null}
      <div className="flex gap-2 overflow-x-auto pb-0.5 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {drop.slots.map((slot) => (
          <div
            key={slot.id}
            className="min-w-[7.5rem] shrink-0 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1.5"
            data-slot={slot.id}
          >
            <div className="text-[9px] font-semibold uppercase tracking-wide text-gray-500">
              {slot.label}
            </div>
            <div
              className={`mt-0.5 text-[11px] leading-snug tabular-nums ${
                slot.id === "power" && drop.hasPower
                  ? "font-semibold text-kos-gold"
                  : "text-gray-200"
              }`}
            >
              {slot.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
