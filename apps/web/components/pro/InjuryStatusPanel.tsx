import type { NflIntelResponseRow } from "@/lib/nfl-intel";
import { formatIntelValue } from "@/lib/nfl-intel";

function impactTone(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized.includes("out") || normalized.includes("ir")) return "text-red-300 border-red-400/35 bg-red-400/10";
  if (normalized.includes("questionable") || normalized.includes("doubtful"))
    return "text-amber-200 border-amber-300/35 bg-amber-300/10";
  return "text-emerald-200 border-emerald-300/35 bg-emerald-300/10";
}

export default function InjuryStatusPanel({ rows }: { rows: NflIntelResponseRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-kos-text/70">
        Injury report is currently unavailable for the selected team/week.
      </div>
    );
  }

  return (
    <section className="space-y-2">
      {rows.slice(0, 12).map((row, index) => {
        const status = typeof row.report_status === "string" ? row.report_status : "Unknown";
        return (
          <article
            key={`${row.player_name ?? "player"}-${index}`}
            className="rounded-xl border border-white/10 bg-white/5 p-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-kos-text">{formatIntelValue(row.player_name)}</p>
                <p className="text-xs text-kos-text/65">
                  {formatIntelValue(row.injury)} · Practice: {formatIntelValue(row.practice_status)}
                </p>
              </div>
              <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${impactTone(status)}`}>
                {status}
              </span>
            </div>
          </article>
        );
      })}
    </section>
  );
}
