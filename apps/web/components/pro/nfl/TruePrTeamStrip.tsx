import Link from "next/link";
import TruePrDriverChips from "@/components/pro/nfl/TruePrDriverChips";
import { driverChipsForTeam } from "@/lib/nfl-true-pr-format";
import type { TruePrTeamRow } from "@/lib/nfl-true-pr";

/** Compact True PR strip for team intel when strength is already wired. */
export default function TruePrTeamStrip({
  row,
  engineVersion,
}: {
  row: TruePrTeamRow | null;
  engineVersion?: string;
}) {
  if (!row) return null;
  const chips = driverChipsForTeam(row.drivers);

  return (
    <section className="mt-4 rounded-2xl border border-white/10 bg-black/30 px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-kos-gold/80">
            True PR
          </p>
          <p className="mt-0.5 text-sm text-kos-text/70">
            Rank #{row.rank} · intrinsic{" "}
            <span className="font-semibold tabular-nums text-kos-gold">
              {row.intrinsic_pr.toFixed(3)}
            </span>
            {engineVersion ? (
              <span className="text-kos-text/40"> · {engineVersion}</span>
            ) : null}
          </p>
        </div>
        <Link
          href="/pro/nfl/model"
          className="min-h-11 inline-flex items-center text-xs font-medium text-kos-gold/90 hover:text-kos-gold sm:min-h-0"
        >
          Full board →
        </Link>
      </div>
      <TruePrDriverChips chips={chips} />
    </section>
  );
}
