import Link from "next/link";
import TruePrDriverChips from "@/components/pro/nfl/TruePrDriverChips";
import { driverChipsForTeam } from "@/lib/nfl-true-pr-format";
import type { TruePrProductSurface } from "@/lib/nfl-true-pr";
import { teamDisplayName } from "@/lib/nfl-team-intel";

/**
 * Scannable True PR board for /pro/nfl/model.
 * Intrinsic PR is the headline; drivers support it.
 */
export default function TruePrDriversBoard({
  surface,
}: {
  surface: TruePrProductSurface;
}) {
  if (surface.error) {
    return (
      <section className="mt-6 rounded-2xl border border-amber-500/25 bg-amber-500/10 px-4 py-4 text-sm text-amber-100/90">
        True PR board unavailable: {surface.error}
      </section>
    );
  }

  if (!surface.teams.length) {
    return (
      <section className="mt-6 rounded-2xl border border-white/10 bg-black/30 px-4 py-4 text-sm text-kos-text/65">
        No team strength rows on this path yet — empty state is intentional.
      </section>
    );
  }

  return (
    <section className="mt-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-kos-gold">
            True power ratings
          </h2>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-kos-text/60">
            Intrinsic PR is research fair strength. Drivers explain why a team
            sits where it sits. 2026 SOS is schedule outlook only — harder
            schedule ≠ weaker team. Blend stays prior-heavy through games 0–2
            (no Week-1 cliff). Edge stays KEI vs market on Edge Board.
          </p>
        </div>
        <p className="text-[11px] text-kos-text/45">
          {surface.engine_version || "engine"} · {surface.team_count} teams
          {surface.mode ? ` · ${surface.mode}` : ""}
        </p>
      </div>

      <ol className="mt-4 grid gap-2">
        {surface.teams.map((row) => {
          const chips = driverChipsForTeam(row.drivers);
          return (
            <li
              key={row.team}
              className="rounded-xl border border-white/10 bg-black/35 px-3 py-3 sm:px-4"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <span className="text-xs font-semibold tabular-nums text-kos-text/45">
                    #{row.rank}
                  </span>
                  <Link
                    href={`/pro/nfl/teams/${row.team}/overview`}
                    className="text-sm font-semibold text-kos-text hover:text-kos-gold"
                  >
                    {row.team}
                    <span className="ml-1.5 font-normal text-kos-text/50">
                      {teamDisplayName(row.team)}
                    </span>
                  </Link>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-kos-text/40">
                    Intrinsic PR
                  </p>
                  <p className="text-lg font-semibold tabular-nums text-kos-gold">
                    {row.intrinsic_pr.toFixed(3)}
                  </p>
                  <p className="text-[11px] tabular-nums text-kos-text/45">
                    Off {row.full_strength_offense_index.toFixed(3)} · Def{" "}
                    {row.full_strength_defense_index.toFixed(3)}
                  </p>
                </div>
              </div>
              <TruePrDriverChips chips={chips} />
            </li>
          );
        })}
      </ol>

      <p className="mt-3 text-[11px] leading-relaxed text-kos-text/40">
        Approximate factors are labeled. Missing evidence is hidden or marked
        unavailable — never decorated as elite confidence. Full opponent-tier
        pages and public non-Pro teaser remain out of scope.
      </p>
    </section>
  );
}
