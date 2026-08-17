import Link from "next/link";
import { cfbTeamDisplayName } from "@/lib/cfb-conferences";
import {
  formatCfbImpliedPct,
  formatCfbMarketOdds,
  type CfbFutureOddsSnap,
} from "@/lib/cfb-futures-odds-format";

export type CfbFuturesCompareRow = {
  team: string;
  conference?: string;
  ourPct: number | null | undefined;
  market: CfbFutureOddsSnap | null;
};

function formatOurPct(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return Number.isInteger(value) ? `${value}` : `${value}`;
}

export default function CfbFuturesCompareTable({
  caption,
  ourLabel,
  rows,
  matched,
  sortMarketHref,
  sortSimHref,
  sortIsMarket,
}: {
  caption: string;
  ourLabel: string;
  rows: CfbFuturesCompareRow[];
  matched: number;
  sortMarketHref?: string;
  sortSimHref?: string;
  sortIsMarket?: boolean;
}) {
  return (
    <section className="mt-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-kos-text">{caption}</h2>
          <p className="mt-0.5 text-xs text-kos-text/55">
            Market matched {matched}/{rows.length} shown
          </p>
        </div>
        {sortMarketHref && sortSimHref ? (
          <p className="text-xs text-kos-text/60">
            Sort:{" "}
            <Link
              href={sortSimHref}
              className={
                sortIsMarket
                  ? "text-kos-text/70 underline-offset-2 hover:underline"
                  : "font-semibold text-kos-gold"
              }
            >
              KosEdge sim
            </Link>
            {" · "}
            <Link
              href={sortMarketHref}
              className={
                sortIsMarket
                  ? "font-semibold text-kos-gold"
                  : "text-kos-text/70 underline-offset-2 hover:underline"
              }
            >
              Market implied
            </Link>
          </p>
        ) : null}
      </div>

      <ol className="mt-3 space-y-2 sm:hidden">
        {rows.map((row) => (
          <li
            key={row.team}
            className="rounded-xl border border-white/10 bg-black/30 px-3 py-2.5"
          >
            <Link
              href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
              className="font-semibold text-kos-text hover:text-kos-gold"
            >
              {cfbTeamDisplayName(row.team)}
            </Link>
            {row.conference ? (
              <p className="text-[11px] text-kos-text/50">{row.conference}</p>
            ) : null}
            <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
              <div>
                <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
                  KosEdge sim
                </dt>
                <dd className="mt-0.5 text-sm font-semibold tabular-nums text-kos-gold">
                  {formatOurPct(row.ourPct)}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
                  Market
                </dt>
                <dd
                  className="mt-0.5 text-sm tabular-nums text-kos-text/90"
                  title={row.market?.book ?? undefined}
                >
                  {formatCfbMarketOdds(row.market)}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wide text-kos-text/45">
                  Implied
                </dt>
                <dd className="mt-0.5 text-sm tabular-nums text-kos-text/80">
                  {formatCfbImpliedPct(row.market)}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ol>

      <div className="mt-3 hidden overflow-x-auto rounded-2xl border border-white/10 sm:block">
        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-black/40 text-[11px] uppercase tracking-[0.12em] text-kos-text/55">
              <th className="px-3 py-2">Team</th>
              <th className="px-3 py-2">Conf</th>
              <th className="px-3 py-2">{ourLabel}</th>
              <th className="px-3 py-2">Market odds</th>
              <th className="px-3 py-2">Market implied</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.team} className="border-b border-white/6">
                <td className="px-3 py-2">
                  <Link
                    href={`/pro/cfb/teams/${row.team.toLowerCase()}`}
                    className="font-semibold text-kos-text hover:text-kos-gold"
                  >
                    {cfbTeamDisplayName(row.team)}
                  </Link>
                </td>
                <td className="px-3 py-2 text-kos-text/65">
                  {row.conference ?? "—"}
                </td>
                <td className="px-3 py-2 font-semibold tabular-nums text-kos-gold">
                  {formatOurPct(row.ourPct)}
                </td>
                <td
                  className="px-3 py-2 tabular-nums text-kos-text/90"
                  title={row.market?.book ?? undefined}
                >
                  {formatCfbMarketOdds(row.market)}
                </td>
                <td className="px-3 py-2 tabular-nums text-kos-text/75">
                  {formatCfbImpliedPct(row.market)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
