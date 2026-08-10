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
          ? "mt-0"
          : "mt-2 rounded-lg border border-white/10 bg-black/50 p-3 sm:p-3.5"
      }
      data-testid="edge-board-stat-drop"
      data-has-power={drop.hasPower ? "1" : "0"}
    >
      {!compact ? (
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-kos-gold/90">
          Stat Drop
        </div>
      ) : null}
      {/* 2×N on mobile; wider grids as space allows — never a crushed one-liner */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-8">
        {drop.slots.map((slot) => (
          <div
            key={slot.id}
            className="min-w-0 rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-2"
            data-slot={slot.id}
          >
            <div className="text-[9px] font-semibold uppercase tracking-wide text-gray-500">
              {slot.label}
            </div>
            <div
              className={`mt-1 text-[11px] leading-snug tabular-nums break-words ${
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
