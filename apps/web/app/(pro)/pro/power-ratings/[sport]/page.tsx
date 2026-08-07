import Link from "next/link";
import { resolveSportKey, sportDisplayLabel } from "@/lib/sports";
import {
  getNflPowerRatingsBoard,
  getPowerRatings,
  type PowerRatingRow,
} from "@/lib/power-ratings";
import { fetchNflIntel } from "@/lib/nfl-intel";
import { PowerRatingsTable } from "./PowerRatingsTable";
import SportProShell from "@/components/pro/SportProShell";

export const dynamic = "force-dynamic";

function formatSigned(value: number | null | undefined, digits = 2): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

function NflAtAGlance({ rows }: { rows: PowerRatingRow[] }) {
  const top5 = rows.slice(0, 5);
  const risers = rows
    .filter((r) => (r.rankDelta ?? 0) > 0)
    .sort((a, b) => (b.rankDelta ?? 0) - (a.rankDelta ?? 0))
    .slice(0, 5);
  const fallers = rows
    .filter((r) => (r.rankDelta ?? 0) < 0)
    .sort((a, b) => (a.rankDelta ?? 0) - (b.rankDelta ?? 0))
    .slice(0, 5);

  const card = (
    title: string,
    items: PowerRatingRow[],
    renderMeta: (r: PowerRatingRow) => string,
  ) => (
    <div className="rounded-xl border border-white/10 bg-black/35 p-4">
      <h3 className="text-sm font-semibold text-kos-gold">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-3 text-xs text-kos-text/55">No movement yet.</p>
      ) : (
        <ol className="mt-3 space-y-2">
          {items.map((r) => (
            <li
              key={r.teamNorm ?? r.team}
              className="flex items-baseline justify-between gap-2 text-sm"
            >
              <Link
                href={`/pro/nfl/teams/${r.teamNorm ?? ""}/overview`}
                className="font-medium text-kos-text hover:text-kos-gold"
              >
                {r.rank}. {r.teamNorm ?? r.team}
              </Link>
              <span className="text-xs text-kos-text/60">{renderMeta(r)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );

  return (
    <section className="mt-6 grid gap-3 md:grid-cols-3">
      {card("Top 5", top5, (r) => `${r.rating.toFixed(2)} wins`)}
      {card("Biggest Risers", risers, (r) =>
        `Rank ${formatSigned(r.rankDelta, 0)} · ${formatSigned(r.weeklyDelta)}`,
      )}
      {card("Biggest Fallers", fallers, (r) =>
        `Rank ${formatSigned(r.rankDelta, 0)} · ${formatSigned(r.weeklyDelta)}`,
      )}
    </section>
  );
}

function bundleLabel(id: string, opts?: { nTeamSims?: number | null }): string {
  const stamp = id.replace("nfl-preseason-sim-2026-", "");
  const day =
    stamp.length >= 8
      ? `${stamp.slice(0, 4)}-${stamp.slice(4, 6)}-${stamp.slice(6, 8)}`
      : null;
  if (opts?.nTeamSims && opts.nTeamSims >= 50000) {
    return day
      ? `Launch ${opts.nTeamSims.toLocaleString()} · ${day}`
      : `Launch ${opts.nTeamSims.toLocaleString()}`;
  }
  if (day) return `Sim ${day}`;
  return id;
}

export default async function PowerRatingsSportPage({
  params,
  searchParams,
}: {
  params: Promise<{ sport: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolved = await params;
  const sportKey = resolveSportKey(resolved?.sport);
  const sportName = sportDisplayLabel(sportKey);
  const sp = searchParams ? await searchParams : {};
  const bundleRaw = Array.isArray(sp.bundle) ? sp.bundle[0] : sp.bundle;

  if (sportKey === "nfl") {
    const board = getNflPowerRatingsBoard({ bundleId: bundleRaw });
    const [standings, stats] = await Promise.all([
      fetchNflIntel("standings", {}),
      fetchNflIntel("stats", {}),
    ]);
    const standingsByTeam = new Map(
      standings.rows
        .filter((r) => typeof r.team === "string")
        .map((r) => [String(r.team), r] as const),
    );
    const statsByTeam = new Map(
      stats.rows
        .filter((r) => typeof r.team === "string")
        .map((r) => [String(r.team), r] as const),
    );

    const enriched = board.rows.map((row) => {
      const code = row.teamNorm ?? "";
      const st = standingsByTeam.get(code);
      const stat = statsByTeam.get(code);
      const wins = typeof st?.wins === "number" ? st.wins : null;
      const losses = typeof st?.losses === "number" ? st.losses : null;
      const ties = typeof st?.ties === "number" ? st.ties : null;
      const record =
        wins != null && losses != null
          ? ties && ties > 0
            ? `${wins}-${losses}-${ties}`
            : `${wins}-${losses}`
          : null;
      const offense =
        typeof stat?.epa_per_play_offense === "number"
          ? Number(stat.epa_per_play_offense.toFixed(3))
          : null;
      const defense =
        typeof stat?.epa_per_play_defense_allowed === "number"
          ? Number(stat.epa_per_play_defense_allowed.toFixed(3))
          : null;
      return { ...row, record, offense, defense };
    });

    return (
      <SportProShell
        sport="nfl"
        pageTitle="NFL Power Ratings"
        pageSubtitle="Team strength from the Kos Edge season-engine research layer (expected wins). Off/Def use owned EPA when available. Weekly Δ compares sim snapshots."
      >
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <p className="text-sm text-kos-text/65">
              {board.bundleId
                ? `Active · ${bundleLabel(board.bundleId, { nTeamSims: board.nTeamSims })}`
                : "No sim bundle found"}
              {board.engineVersion ? ` · ${board.engineVersion}` : ""}
              {board.previousBundleId
                ? ` · Δ vs ${bundleLabel(board.previousBundleId)}`
                : ""}
            </p>
          </div>
          {board.launchIdentity || (board.nTeamSims && board.nTeamSims >= 50000) ? (
            <p className="mt-2 rounded-lg border border-kos-gold/25 bg-kos-gold/10 px-3 py-2 text-xs text-kos-text/80">
              Launch-current research
              {board.nTeamSims
                ? ` · ${board.nTeamSims.toLocaleString()} team W/L paths`
                : ""}
              {board.generatedAtUtc
                ? ` · generated ${board.generatedAtUtc.slice(0, 10)}`
                : ""}
              . Preseason numbers — not live week-1 Edge Board grades.
            </p>
          ) : null}

          {board.availableBundles.length > 1 ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {board.availableBundles.slice(0, 8).map((id) => {
                const active = id === board.bundleId;
                return (
                  <Link
                    key={id}
                    href={`/pro/power-ratings/nfl?bundle=${encodeURIComponent(id)}`}
                    className={
                      active
                        ? "rounded-md border border-kos-gold/40 bg-kos-gold/15 px-2.5 py-1 text-xs font-semibold text-kos-gold"
                        : "rounded-md border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-kos-text/70 hover:border-kos-gold/30"
                    }
                  >
                    {bundleLabel(id, {
                      nTeamSims: active ? board.nTeamSims : null,
                    })}
                  </Link>
                );
              })}
            </div>
          ) : null}

          <NflAtAGlance rows={enriched} />

          <div className="mt-6 overflow-x-auto rounded-2xl border border-kos-border bg-kos-surface/30">
            <table className="min-w-full text-left">
              <thead>
                <tr className="border-b border-kos-border bg-kos-surface/50">
                  {[
                    "Rank",
                    "Team",
                    "Power Rating",
                    "Off",
                    "Def",
                    "Weekly Δ",
                    "Rank Δ",
                    "Record",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-3 py-3 text-xs font-semibold uppercase tracking-wide text-kos-text/70"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {enriched.map((r) => (
                  <tr
                    key={r.teamNorm ?? r.team}
                    className="border-b border-kos-border/40 hover:bg-kos-surface/40"
                  >
                    <td className="px-3 py-2.5 text-sm text-kos-text/80">
                      {r.rank}
                    </td>
                    <td className="px-3 py-2.5 text-sm font-medium">
                      <Link
                        href={`/pro/nfl/teams/${r.teamNorm}/overview`}
                        className="text-kos-text hover:text-kos-gold"
                      >
                        {r.teamNorm}{" "}
                        <span className="text-kos-text/50">{r.team}</span>
                      </Link>
                    </td>
                    <td className="px-3 py-2.5 text-sm font-semibold text-kos-gold">
                      {r.rating.toFixed(2)}
                    </td>
                    <td className="px-3 py-2.5 text-sm text-kos-text/75">
                      {r.offense != null ? r.offense.toFixed(3) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-sm text-kos-text/75">
                      {r.defense != null ? r.defense.toFixed(3) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-sm text-kos-text/75">
                      {formatSigned(r.weeklyDelta)}
                    </td>
                    <td className="px-3 py-2.5 text-sm text-kos-text/75">
                      {formatSigned(r.rankDelta, 0)}
                    </td>
                    <td className="px-3 py-2.5 text-sm text-kos-text/75">
                      {r.record ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-kos-text/45">
            Power Rating = model expected wins. Off = offense EPA/play; Def =
            defense EPA allowed/play (intel). Empty cells mean that feed is not
            on the current week yet.
          </p>
        </main>
      </SportProShell>
    );
  }

  const ratings = getPowerRatings(sportKey);

  return (
    <SportProShell
      sport={sportKey}
      pageTitle={`${sportName} Power Ratings`}
      pageSubtitle="Team strength, tiering, and model rankings for slate research. Neutral presentation — not picks."
    >
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <p className="text-sm text-kos-text/65">
            {ratings.length
              ? `${ratings.length} teams ranked`
              : "Ratings feed pending for this sport — shell stays ready without invented numbers."}
          </p>
          <Link
            href="/pro/power-ratings"
            className="min-h-11 inline-flex items-center rounded-xl border border-kos-border bg-kos-surface/40 px-4 py-2 text-sm hover:border-kos-gold/40"
          >
            All sports
          </Link>
        </div>

        <div className="mt-6">
          <PowerRatingsTable ratings={ratings} sportName={sportName} />
        </div>
      </main>
    </SportProShell>
  );
}
