import * as React from "react";
import { generateGameOverview } from "@/lib/sports";

// Flat API row format (from Odds API / model); kei = our projected line/total
export type FlatEdgeBoardRow = {
  id?: string;
  game?: string;
  time?: string;
  market?: string;
  open?: string;
  best?: string;
  book?: string;
  note?: string;
  commenceTime?: string;
  kei?: string;
};

export type EdgeBoardRow = FlatEdgeBoardRow;

type Variant = "home" | "full";
type Tag = "PLAY" | "LEAN" | "PASS";

export type PriceSide = { label: string; juice: string };
export type PricePair = { top: PriceSide; bottom: PriceSide };

export type TeamBlock = {
  name: string;
  keiRank?: string;
  keiNumber?: string;
  site: "Away" | "Home";
  record?: string;
  confRecord?: string;
};

export type LegacyEdgeBoardRow = {
  id: string;
  time?: string;
  teamA: TeamBlock;
  teamB: TeamBlock;
  openOU: PricePair;
  openLine: PricePair;
  bestLine: PricePair;
  bestOU: PricePair;
  keiLine?: PricePair;
  keiOU?: PricePair;
  edgeLine?: PricePair;
  edgeOU?: PricePair;
  edgeLineNum?: number;
  edgeOUNum?: number;
  tagLine?: Tag;
  tagOU?: Tag;
  overview?: string;
};

const COMING_SOON_PAIR: PricePair = {
  top: { label: "Coming soon", juice: "—" },
  bottom: { label: "Coming soon", juice: "—" },
};

const sampleRows: LegacyEdgeBoardRow[] = [
  {
    id: "sample-1",
    time: "8:30pm",
    teamA: {
      name: "Duke",
      keiRank: "12",
      site: "Away",
      record: "21-1",
      confRecord: "10-0",
    },
    teamB: {
      name: "UNC",
      keiRank: "18",
      site: "Home",
      record: "18-4",
      confRecord: "8-2",
    },
    openOU: {
      top: { label: "o150.5", juice: "-110" },
      bottom: { label: "u150.5", juice: "-110" },
    },
    openLine: {
      top: { label: "+5.5", juice: "-110" },
      bottom: { label: "-5.5", juice: "-110" },
    },
    bestLine: {
      top: { label: "+6.5", juice: "-112" },
      bottom: { label: "-5.0", juice: "-110" },
    },
    bestOU: {
      top: { label: "o149.5", juice: "-110" },
      bottom: { label: "u152.5", juice: "-112" },
    },
    overview: generateGameOverview("Duke", "UNC"),
    tagLine: "LEAN",
    tagOU: "PASS",
  },
];

function PriceCell({
  p,
  valueClassName = "text-gray-200 font-semibold",
  compact = false,
}: {
  p: PricePair;
  valueClassName?: string;
  compact?: boolean;
}) {
  const sep = compact ? "mt-1 h-px" : "mt-1.5 h-px";
  const topPad = compact ? "mt-1" : "mt-1.5";
  const valueLeading = compact ? "leading-[1.05]" : "leading-tight";

  return (
    <div className={valueLeading}>
      <div className={valueClassName}>{p.top.label}</div>
      <div className="text-[11px] text-gray-400">({p.top.juice})</div>
      <div className={`${sep} bg-white/10`} />
      <div className={`${topPad} ${valueClassName}`}>{p.bottom.label}</div>
      <div className="text-[11px] text-gray-400">({p.bottom.juice})</div>
    </div>
  );
}

function HeaderStack({ a, b }: { a: string; b?: string }) {
  return (
    <div className="flex flex-col leading-[1.05]">
      <span>{a}</span>
      {b ? <span>{b}</span> : null}
    </div>
  );
}

/** Tag from edge: PLAY ≥2.5, LEAN 1.0–2.5, PASS <1.0 */
function edgeToTag(edgeNum: number | undefined): Tag | undefined {
  if (edgeNum == null) return undefined;
  if (edgeNum >= 2.5) return "PLAY";
  if (edgeNum >= 1.0) return "LEAN";
  return "PASS";
}

/** Edge column highlight: 0–2.5 kos gray, 2.6–3.4 kos gold, 3.5+ edge green */
function edgeCellClass(edgeNum: number | undefined): string {
  if (edgeNum == null) return "bg-white/5 text-gray-500";
  if (edgeNum <= 2.5) return "bg-kos-gray/25 text-kos-muted";
  if (edgeNum <= 3.4) return "bg-kos-gold/25 text-kos-gold font-medium";
  return "bg-edge-green/20 text-edge-green font-semibold";
}

const COL_WIDTHS = [
  "160px",
  "85px",
  "85px",
  "85px",
  "85px",
  "85px",
  "85px",
  "85px",
  "75px",
  "75px",
  "75px",
  "75px",
] as const;

function flatRowsToLegacy(flat: FlatEdgeBoardRow[]): LegacyEdgeBoardRow[] {
  const valid = Array.isArray(flat)
    ? flat.filter(
        (r): r is FlatEdgeBoardRow => r != null && typeof r === "object",
      )
    : [];
  const sorted = [...valid].sort((a, b) =>
    String(a?.commenceTime ?? a?.time ?? "").localeCompare(
      String(b?.commenceTime ?? b?.time ?? ""),
    ),
  );
  const byGame = new Map<
    string,
    { spread?: FlatEdgeBoardRow; total?: FlatEdgeBoardRow }
  >();
  for (const r of sorted) {
    const key = String(r?.game ?? r?.id ?? "unknown").trim() || "unknown";
    const entry = byGame.get(key) ?? {};
    if (r?.market === "Spread") entry.spread = r;
    else if (r?.market === "Total") entry.total = r;
    byGame.set(key, entry);
  }
  const result: LegacyEdgeBoardRow[] = [];
  for (const [gameKey, entry] of byGame) {
    const spread = entry.spread ?? entry.total;
    const total = entry.total ?? entry.spread;
    if (!spread && !total) continue;
    const game = String(spread?.game ?? total?.game ?? gameKey ?? "");
    const parts = game.includes(" @ ") ? game.split(" @ ") : game.split(" vs ");
    const away = (parts[0] ?? "Away").trim() || "Away";
    const home = (parts[1] ?? "Home").trim() || "Home";
    const time = (spread ?? total)?.time ?? "—";
    const flipSpread = (s: string | undefined): string => {
      const str = String(s ?? "").trim();
      if (!str) return "—";
      if (str.startsWith("+")) return `-${str.slice(1)}`;
      const n = parseFloat(str);
      return Number.isFinite(n) ? (n <= 0 ? `+${Math.abs(n)}` : `-${n}`) : "—";
    };
    const openLine: PricePair = spread?.open
      ? {
          top: { label: spread.open, juice: "—" },
          bottom: { label: flipSpread(spread.open), juice: "—" },
        }
      : COMING_SOON_PAIR;
    const bestLine: PricePair = spread?.best
      ? {
          top: { label: spread.best, juice: "—" },
          bottom: { label: flipSpread(spread.best), juice: "—" },
        }
      : COMING_SOON_PAIR;
    const t = total?.open ?? total?.best ?? "—";
    const openOU: PricePair =
      t !== "—"
        ? {
            top: { label: `o${t}`, juice: "—" },
            bottom: { label: `u${t}`, juice: "—" },
          }
        : COMING_SOON_PAIR;
    const b = total?.best ?? total?.open ?? "—";
    const bestOU: PricePair =
      b !== "—"
        ? {
            top: { label: `o${b}`, juice: "—" },
            bottom: { label: `u${b}`, juice: "—" },
          }
        : COMING_SOON_PAIR;

    const spreadKei = (spread as FlatEdgeBoardRow | undefined)?.kei;
    const totalKei = (total as FlatEdgeBoardRow | undefined)?.kei;
    const keiLine: PricePair = spreadKei
      ? {
          top: { label: spreadKei, juice: "—" },
          bottom: { label: flipSpread(spreadKei), juice: "—" },
        }
      : COMING_SOON_PAIR;
    const keiOU: PricePair = totalKei
      ? {
          top: { label: `o${totalKei}`, juice: "—" },
          bottom: { label: `u${totalKei}`, juice: "—" },
        }
      : COMING_SOON_PAIR;

    const parseSpread = (s: string): number | null => {
      const n = parseFloat(String(s).replace(/[^+\-\d.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    const parseTotal = (s: string): number | null => {
      const n = parseFloat(String(s).replace(/[^\d.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    const bestSpreadNum = parseSpread(bestLine.bottom.label);
    const keiSpreadNum = parseSpread(keiLine.bottom.label);
    const edgeLineNum =
      bestSpreadNum != null && keiSpreadNum != null
        ? Math.abs(bestSpreadNum - keiSpreadNum)
        : undefined;
    const bestTotalNum = parseTotal(bestOU.top.label);
    const keiTotalNum = parseTotal(keiOU.top.label);
    const edgeOUNum =
      bestTotalNum != null && keiTotalNum != null
        ? Math.abs(bestTotalNum - keiTotalNum)
        : undefined;

    const edgeLineDisplay: PricePair =
      edgeLineNum != null
        ? {
            top: { label: edgeLineNum.toFixed(1), juice: "—" },
            bottom: { label: edgeLineNum.toFixed(1), juice: "—" },
          }
        : COMING_SOON_PAIR;
    const edgeOUDisplay: PricePair =
      edgeOUNum != null
        ? {
            top: { label: edgeOUNum.toFixed(1), juice: "—" },
            bottom: { label: edgeOUNum.toFixed(1), juice: "—" },
          }
        : COMING_SOON_PAIR;

    result.push({
      id: String(spread?.id ?? total?.id ?? gameKey),
      time,
      teamA: {
        name: away,
        site: "Away",
        keiNumber:
          keiLine.top.label !== "Coming soon" ? keiLine.top.label : undefined,
      },
      teamB: {
        name: home,
        site: "Home",
        keiNumber:
          keiLine.bottom.label !== "Coming soon"
            ? keiLine.bottom.label
            : undefined,
      },
      openOU,
      openLine,
      bestLine,
      bestOU,
      keiLine,
      keiOU,
      edgeLine: edgeLineDisplay,
      edgeOU: edgeOUDisplay,
      edgeLineNum,
      edgeOUNum,
      tagLine: edgeToTag(edgeLineNum),
      tagOU: edgeToTag(edgeOUNum),
      overview: generateGameOverview(away, home),
    });
  }
  return result;
}

export default function EdgeBoard({
  variant = "full",
  rows,
}: {
  variant?: Variant;
  rows?: FlatEdgeBoardRow[] | null;
}) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const edgeGreen =
    "text-[#22c55e] font-bold drop-shadow-[0_0_10px_rgba(34,197,94,0.55)]";
  const hasRealData = safeRows.length > 0;
  const legacy = hasRealData ? flatRowsToLegacy(safeRows) : sampleRows;
  const data = hasRealData ? legacy : sampleRows;

  if (variant === "home") {
    return (
      <div className="lg:col-span-5">
        <div className="relative">
          <div className="absolute -inset-1 rounded-3xl bg-linear-to-r from-kos-gold/25 via-kos-green/15 to-kos-gold/25 blur-2xl opacity-80" />
          <div className="relative bg-black/40 border border-white/12 rounded-3xl p-5 sm:p-6 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-3xl font-bebas text-kos-gold">Edge Board</h2>
              <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-gray-400">
                Sample
              </span>
            </div>
            <div className="overflow-hidden rounded-2xl border border-white/10">
              <table className="w-full text-sm sm:text-base">
                <thead className="bg-white/5">
                  <tr className="text-left text-gray-300">
                    <th className="py-2.5 px-3">Game</th>
                    <th className="py-2.5 px-3">Best Line</th>
                    <th className="py-2.5 px-3">Best O/U</th>
                    <th className="py-2.5 px-3">Edge</th>
                    <th className="py-2.5 px-3">Tag</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10 text-gray-200">
                  {sampleRows.map((r) => (
                    <tr key={r.id} className="hover:bg-white/5 transition">
                      <td className="py-2.5 px-3">
                        <div className="font-semibold">
                          {r.teamA.name} vs {r.teamB.name}
                        </div>
                        <div className="text-[11px] text-gray-400">
                          {r.teamA.name} ({r.teamA.keiRank ?? "—"}) •{" "}
                          {r.teamB.name} ({r.teamB.keiRank ?? "—"})
                        </div>
                      </td>
                      <td className="py-2.5 px-3">{r.bestLine.top.label}</td>
                      <td className="py-2.5 px-3">{r.bestOU.top.label}</td>
                      <td className={["py-2.5 px-3", edgeGreen].join(" ")}>
                        Coming soon
                      </td>
                      <td className="py-2.5 px-3 font-bebas text-kos-gold tracking-wide">
                        Coming soon
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 text-xs text-gray-400">
              Sample data for illustrative purposes only.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const MobileCards = (
    <div className="lg:hidden mt-6">
      <div className="relative">
        <div className="absolute -inset-1 rounded-3xl bg-linear-to-r from-kos-gold/25 via-kos-green/15 to-kos-gold/25 blur-2xl opacity-80" />
        <div className="relative bg-black/40 border border-white/12 rounded-3xl p-5 sm:p-6 backdrop-blur-xl shadow-2xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bebas text-kos-gold">Edge Board</h2>
            <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-gray-400">
              {safeRows.length
                ? `${new Set(safeRows.map((r) => r?.game).filter(Boolean)).size} games`
                : "Live"}
            </span>
          </div>
          <div className="overflow-hidden rounded-2xl border border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-white/5">
                <tr className="text-left text-gray-300">
                  <th className="py-2.5 px-3">Game</th>
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Best Line</th>
                  <th className="py-2.5 px-3">Best O/U</th>
                  <th className="py-2.5 px-3">Edge</th>
                  <th className="py-2.5 px-3">Tag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10 text-gray-200">
                {data.map((r) => (
                  <tr key={r.id} className="hover:bg-white/5 transition">
                    <td className="py-2.5 px-3 align-top">
                      <div className="font-semibold">
                        {r.teamA.name} vs {r.teamB.name}
                      </div>
                      <details className="mt-1 group/details">
                        <summary className="cursor-pointer text-[12px] text-kos-gold hover:underline list-none [&::-webkit-details-marker]:hidden">
                          Overview ▾
                        </summary>
                        <div className="mt-2 p-3 rounded-lg border border-white/10 bg-black/60 text-[11px] text-gray-300 leading-relaxed whitespace-pre-wrap">
                          {r.overview ?? "No overview available."}
                        </div>
                      </details>
                    </td>
                    <td className="py-2.5 px-3 text-gray-300 tabular-nums">
                      {r.time ?? "—"}
                    </td>
                    <td className="py-2.5 px-3">{r.bestLine.top.label}</td>
                    <td className="py-2.5 px-3">{r.bestOU.top.label}</td>
                    <td
                      className={`py-2.5 px-3 rounded ${edgeCellClass(r.edgeLineNum)}`}
                    >
                      {r.edgeLineNum != null ? (
                        <span className="font-semibold tabular-nums">
                          {r.edgeLineNum.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      {r.tagLine ? (
                        <span
                          className={`inline-flex px-2 py-0.5 rounded text-[11px] font-semibold ${
                            r.tagLine === "PLAY"
                              ? "bg-edge-green/20 text-edge-green"
                              : r.tagLine === "LEAN"
                                ? "bg-kos-gold/20 text-kos-gold"
                                : "bg-white/10 text-gray-400"
                          }`}
                        >
                          {r.tagLine}
                        </span>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 text-xs text-gray-400">
            Game • Time • Best Line/O/U • Edge • Tag • Overview
          </div>
        </div>
      </div>
    </div>
  );

  const DesktopTable = (
    <div className="hidden lg:block mt-6">
      <div className="bg-black/30 border border-white/12 rounded-2xl overflow-hidden backdrop-blur-xl shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="text-sm text-gray-300">
            Tonight • Live odds (Open + Best) • Everything else coming soon
          </div>
          <div className="text-xs text-gray-500">
            {safeRows.length
              ? `${new Set(safeRows.map((r) => r?.game).filter(Boolean)).size} games`
              : "Logos + links next"}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-[1100px] w-full table-fixed text-[12.75px] tabular-nums">
            <colgroup>
              {COL_WIDTHS.map((w, i) => (
                <col key={i} style={{ width: w }} />
              ))}
            </colgroup>
            <thead className="bg-white/5 text-gray-300 uppercase tracking-wide text-[13px]">
              <tr className="text-left">
                <th className="py-2.5 px-3">
                  <HeaderStack a="Game" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="Time" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="Open" b="O/U" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="Open" b="Line" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="Best" b="Line" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="Best" b="O/U" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="KEICMB" b="Line" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="KEICMB" b="O/U" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="Edge" b="Line" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a="Edge" b="O/U" />
                </th>
                <th className="py-2.5 px-3 text-center">
                  <HeaderStack a="Tag" b="Line" />
                </th>
                <th className="py-2.5 px-3 text-center">
                  <HeaderStack a="Tag" b="O/U" />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10 text-gray-200">
              {data.map((r) => (
                <tr key={r.id} className="hover:bg-white/5 transition">
                  <td className="py-2.5 px-3 align-top relative pb-7 overflow-visible">
                    <div className="font-semibold truncate">
                      {r.teamA.name}
                      {r.teamA.keiNumber != null ? (
                        <span className="ml-1 text-kos-gold tabular-nums">
                          ({r.teamA.keiNumber})
                        </span>
                      ) : (
                        r.teamA.keiRank != null && (
                          <span className="text-gray-400">
                            {" "}
                            ({r.teamA.keiRank})
                          </span>
                        )
                      )}
                    </div>
                    <div className="text-xs text-gray-400">
                      {r.teamA.site}
                      {r.teamA.record ? ` • ${r.teamA.record}` : ""}
                      {r.teamA.confRecord ? ` (${r.teamA.confRecord})` : ""}
                    </div>
                    <div className="mt-1 font-semibold truncate">
                      {r.teamB.name}
                      {r.teamB.keiNumber != null ? (
                        <span className="ml-1 text-kos-gold tabular-nums">
                          ({r.teamB.keiNumber})
                        </span>
                      ) : (
                        r.teamB.keiRank != null && (
                          <span className="text-gray-400">
                            {" "}
                            ({r.teamB.keiRank})
                          </span>
                        )
                      )}
                    </div>
                    <div className="text-xs text-gray-400">
                      {r.teamB.site}
                      {r.teamB.record ? ` • ${r.teamB.record}` : ""}
                      {r.teamB.confRecord ? ` (${r.teamB.confRecord})` : ""}
                    </div>
                    <details className="absolute bottom-2 left-3 group/details">
                      <summary className="cursor-pointer text-[14px] text-kos-gold hover:underline whitespace-nowrap list-none [&::-webkit-details-marker]:hidden">
                        Overview ▾
                      </summary>
                      <div className="absolute left-0 top-full mt-1 z-50 w-[340px] rounded-xl border border-white/15 bg-black/95 backdrop-blur-xl p-4 shadow-xl text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                        {r.overview ?? "No overview available."}
                      </div>
                    </details>
                  </td>
                  <td className="py-2.5 px-1 align-top relative pb-7 overflow-hidden">
                    <div className="text-sm font-medium text-gray-300 whitespace-nowrap">
                      {r.time ?? "—"}
                    </div>
                    <button
                      className="absolute bottom-2 left-0 right-0 mx-auto text-center text-[14px] text-kos-gold hover:text-kos-gold transition whitespace-nowrap"
                      type="button"
                      title="Expandable panel coming soon"
                    >
                      Stats ▾
                    </button>
                  </td>
                  <td className="py-2.5 px-3 align-top text-gray-400">
                    <PriceCell
                      p={r.openOU}
                      compact
                      valueClassName="text-gray-400 font-medium"
                    />
                  </td>
                  <td className="py-2.5 px-3 align-top text-gray-400">
                    <PriceCell
                      p={r.openLine}
                      compact
                      valueClassName="text-gray-400 font-medium"
                    />
                  </td>
                  <td className="py-2.5 px-3 align-top">
                    <PriceCell
                      p={r.bestLine}
                      compact
                      valueClassName="text-gray-100 font-semibold"
                    />
                  </td>
                  <td className="py-2.5 px-3 align-top">
                    <PriceCell
                      p={r.bestOU}
                      compact
                      valueClassName="text-gray-100 font-semibold"
                    />
                  </td>
                  <td className="py-2.5 px-2 align-top">
                    <PriceCell
                      p={r.keiLine ?? COMING_SOON_PAIR}
                      compact
                      valueClassName="text-kos-gold/90 font-medium"
                    />
                  </td>
                  <td className="py-2.5 px-2 align-top">
                    <PriceCell
                      p={r.keiOU ?? COMING_SOON_PAIR}
                      compact
                      valueClassName="text-kos-gold/90 font-medium"
                    />
                  </td>
                  <td
                    className={`py-2.5 px-2 align-top rounded ${edgeCellClass(r.edgeLineNum)}`}
                  >
                    {r.edgeLineNum != null ? (
                      <span className="font-semibold tabular-nums">
                        {r.edgeLineNum.toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-gray-500">—</span>
                    )}
                  </td>
                  <td
                    className={`py-2.5 px-2 align-top rounded ${edgeCellClass(r.edgeOUNum)}`}
                  >
                    {r.edgeOUNum != null ? (
                      <span className="font-semibold tabular-nums">
                        {r.edgeOUNum.toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-gray-500">—</span>
                    )}
                  </td>
                  <td className="py-2.5 px-2 align-top text-center">
                    {r.tagLine ? (
                      <span
                        className={`inline-flex items-center justify-center px-2 py-1 rounded-lg text-[12px] font-semibold ${
                          r.tagLine === "PLAY"
                            ? "bg-edge-green/20 text-edge-green border border-edge-green/30"
                            : r.tagLine === "LEAN"
                              ? "bg-kos-gold/20 text-kos-gold border border-kos-gold/30"
                              : "bg-white/5 text-gray-400 border border-white/10"
                        }`}
                      >
                        {r.tagLine}
                      </span>
                    ) : (
                      <span className="text-gray-500">—</span>
                    )}
                  </td>
                  <td className="py-2.5 px-2 align-top text-center">
                    {r.tagOU ? (
                      <span
                        className={`inline-flex items-center justify-center px-2 py-1 rounded-lg text-[12px] font-semibold ${
                          r.tagOU === "PLAY"
                            ? "bg-edge-green/20 text-edge-green border border-edge-green/30"
                            : r.tagOU === "LEAN"
                              ? "bg-kos-gold/20 text-kos-gold border border-kos-gold/30"
                              : "bg-white/5 text-gray-400 border border-white/10"
                        }`}
                      >
                        {r.tagOU}
                      </span>
                    ) : (
                      <span className="text-gray-500">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-3 text-[10px] text-gray-400 border-t border-white/10">
          Live: Game/Time/Open/Best. KEI: our projected line and O/U (when data
          available). Coming soon: Edge + Tags, sportsbook logos + deep links,
          Overview/Stats expanders.
        </div>
      </div>
    </div>
  );

  // Empty state for full variant when no real data (avoids misleading sample)
  if (variant === "full" && !hasRealData) {
    return (
      <div className="mt-6 rounded-2xl border border-white/10 bg-black/30 backdrop-blur-xl p-8 sm:p-12 text-center">
        <div className="text-kos-gold text-2xl font-bebas tracking-wide mb-2">
          No Live Data
        </div>
        <p className="text-gray-400 text-sm max-w-md mx-auto">
          Today&apos;s games will appear here when live odds are available.
          Ensure ODDS_API_KEY is configured in your deployment environment.
        </p>
      </div>
    );
  }

  return (
    <>
      {MobileCards}
      {DesktopTable}
    </>
  );
}
