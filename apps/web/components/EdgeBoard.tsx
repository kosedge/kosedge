import * as React from "react";
import SportsbookBadge from "@/components/SportsbookBadge";
import { getKeiCode } from "@/lib/kei-brand";
import { nflPublishTag } from "@/lib/nfl-publish-policy";
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
  bookKey?: string;
  /** American odds juice for Open top (away / over). */
  openJuice?: string;
  /** American odds juice for Open bottom (home / under). */
  openJuiceHome?: string;
  bestJuice?: string;
  bestJuiceHome?: string;
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
  bestLineBook?: string;
  bestOUBook?: string;
  keiLine?: PricePair;
  keiOU?: PricePair;
  edgeLine?: PricePair;
  edgeOU?: PricePair;
  edgeLineNum?: number;
  edgeOUNum?: number;
  /** Team the spread edge favors (short label). */
  edgeLineFavor?: string;
  /** Over / Under the total edge favors. */
  edgeOUFavor?: "Over" | "Under";
  /** Concrete spread action at the best book, e.g. "Chiefs -3.5". */
  playLine?: string;
  /** Concrete total action at the best book, e.g. "Over 45.5". */
  playOU?: string;
  /** True when total edge is oversized (model overconfidence zone) — size down. */
  edgeOUCaution?: boolean;
  tagLine?: Tag;
  tagOU?: Tag;
  overview?: string;
};

const COMING_SOON_PAIR: PricePair = {
  top: { label: "Coming soon", juice: "—" },
  bottom: { label: "Coming soon", juice: "—" },
};

/** Empty market / KEI cell — not “coming soon”, just no number yet. */
const EMPTY_PAIR: PricePair = {
  top: { label: "—", juice: "—" },
  bottom: { label: "—", juice: "—" },
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
    edgeLineNum: 1.5,
    edgeOUNum: 0.4,
    edgeLineFavor: "Duke",
    edgeOUFavor: "Under",
    playLine: "Duke +6.5",
    playOU: "Under 152.5",
    tagLine: "LEAN",
    tagOU: "PASS",
  },
];

/** Short team label for dense board cells (last word of full name). */
function shortTeamLabel(name: string): string {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return "—";
  if (parts.length === 1) return parts[0];
  // "New York Jets" → Jets; "LA Clippers" → Clippers
  return parts[parts.length - 1];
}

function tagClassName(tag: Tag, compact = false): string {
  const base = compact
    ? "inline-flex px-2 py-0.5 rounded text-[11px] font-semibold"
    : "inline-flex items-center justify-center px-2 py-1 rounded-lg text-[12px] font-semibold";
  if (tag === "PLAY")
    return `${base} bg-edge-green/20 text-edge-green border border-edge-green/30`;
  if (tag === "LEAN")
    return `${base} bg-kos-gold/20 text-kos-gold border border-kos-gold/30`;
  return `${base} bg-white/5 text-gray-400 border border-white/10`;
}

function EdgeSideCell({
  edgeNum,
  favor,
  tag,
}: {
  edgeNum?: number;
  favor?: string;
  tag?: Tag;
}) {
  if (edgeNum == null) {
    return <span className="text-gray-500">—</span>;
  }
  return (
    <div className="leading-tight">
      <div className="font-semibold tabular-nums">{edgeNum.toFixed(1)}</div>
      {favor ? (
        <div
          className={`mt-0.5 text-[11px] font-semibold truncate ${favorTextClass(tag)}`}
        >
          {favor}
        </div>
      ) : null}
    </div>
  );
}

function TagPlayCell({
  tag,
  play,
  compact = false,
  caution = false,
}: {
  tag?: Tag;
  play?: string;
  compact?: boolean;
  caution?: boolean;
}) {
  if (!tag) return <span className="text-gray-500">—</span>;
  return (
    <div className={compact ? "leading-tight" : "leading-tight text-center"}>
      <span className={tagClassName(tag, compact)}>{tag}</span>
      {play && tag !== "PASS" ? (
        <div
          className={`mt-1 text-[11px] font-semibold truncate ${favorTextClass(tag)}`}
        >
          {play}
        </div>
      ) : null}
      {caution && tag !== "PASS" ? (
        <div className="mt-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-300/90">
          Size down
        </div>
      ) : null}
    </div>
  );
}

function PriceCell({
  p,
  valueClassName = "text-gray-200 font-semibold",
  compact = false,
  book,
}: {
  p: PricePair;
  valueClassName?: string;
  compact?: boolean;
  /** Sportsbook that holds this best price (shown under the lines). */
  book?: string | null;
}) {
  const sep = compact ? "mt-1 h-px" : "mt-1.5 h-px";
  const topPad = compact ? "mt-1" : "mt-1.5";
  const valueLeading = compact ? "leading-[1.05]" : "leading-tight";
  const blank =
    p.top.label === "Coming soon" ||
    p.bottom.label === "Coming soon" ||
    p.top.label === "—" ||
    p.bottom.label === "—";

  return (
    <div className={valueLeading}>
      <div className={valueClassName}>{p.top.label}</div>
      <div className="text-[11px] text-gray-400">({p.top.juice})</div>
      <div className={`${sep} bg-white/10`} />
      <div className={`${topPad} ${valueClassName}`}>{p.bottom.label}</div>
      <div className="text-[11px] text-gray-400">({p.bottom.juice})</div>
      {!blank && book ? (
        <div className={`${topPad}`}>
          <SportsbookBadge book={book} compact />
        </div>
      ) : null}
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

type EdgeMarket = "line" | "total";

/**
 * NFL: selective publish (see lib/nfl-publish-policy.ts + docs/NFL_ENTERPRISE_GATES.md).
 *   Spread: PASS default · PLAY ≥2.5 with ATS evidence · LEAN disabled
 *   Total:  PASS default · PLAY only in [2.5, 3.0) · ≥3.0 PASS (toxic)
 * Other sports keep the legacy 1.0 / 2.5 cut for both markets.
 */
function edgeToTag(
  edgeNum: number | undefined,
  market: EdgeMarket,
  sportKey = "ncaam",
): Tag | undefined {
  if (edgeNum == null) return undefined;
  const nfl = String(sportKey).toLowerCase() === "nfl";
  if (nfl) {
    const pub = nflPublishTag(
      market === "total" ? "total" : "spread",
      edgeNum,
      "YELLOW",
    );
    return pub.tag;
  }
  if (edgeNum >= 2.5) return "PLAY";
  if (edgeNum >= 1.0) return "LEAN";
  return "PASS";
}

/** Oversized total edges: still PLAY when ≥2.5, but stake down when ≥3.0. */
function isNflTotalCaution(
  edgeNum: number | undefined,
  sportKey: string,
): boolean {
  return (
    String(sportKey).toLowerCase() === "nfl" &&
    edgeNum != null &&
    edgeNum >= 3.0
  );
}

/** Cell chrome matches the tag — gray PASS, gold LEAN, green PLAY. */
function edgeCellClass(tag: Tag | undefined): string {
  if (tag == null) return "bg-white/5 text-gray-500";
  if (tag === "PLAY") return "bg-edge-green/20 text-edge-green font-semibold";
  if (tag === "LEAN") return "bg-kos-gold/25 text-kos-gold font-medium";
  return "bg-kos-gray/25 text-kos-muted";
}

function favorTextClass(tag: Tag | undefined): string {
  if (tag === "PLAY") return "text-edge-green";
  if (tag === "LEAN") return "text-kos-gold";
  return "text-gray-400";
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
  "80px",
  "80px",
  "100px",
  "100px",
] as const;

export function flatRowsToLegacy(
  flat: FlatEdgeBoardRow[],
  sportKey = "ncaam",
): LegacyEdgeBoardRow[] {
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
    const spreadRow = spread as FlatEdgeBoardRow | undefined;
    const totalRow = total as FlatEdgeBoardRow | undefined;
    const juiceOr = (v: string | undefined) => v || "—";

    const openLine: PricePair = spreadRow?.open
      ? {
          top: { label: spreadRow.open, juice: juiceOr(spreadRow.openJuice) },
          bottom: {
            label: flipSpread(spreadRow.open),
            juice: juiceOr(spreadRow.openJuiceHome),
          },
        }
      : EMPTY_PAIR;
    const bestLine: PricePair = spreadRow?.best
      ? {
          top: { label: spreadRow.best, juice: juiceOr(spreadRow.bestJuice) },
          bottom: {
            label: flipSpread(spreadRow.best),
            juice: juiceOr(spreadRow.bestJuiceHome),
          },
        }
      : EMPTY_PAIR;
    const t = totalRow?.open ?? totalRow?.best ?? "—";
    const openOU: PricePair =
      t !== "—"
        ? {
            top: { label: `o${t}`, juice: juiceOr(totalRow?.openJuice) },
            bottom: { label: `u${t}`, juice: juiceOr(totalRow?.openJuiceHome) },
          }
        : EMPTY_PAIR;
    const b = totalRow?.best ?? totalRow?.open ?? "—";
    const bestOU: PricePair =
      b !== "—"
        ? {
            top: { label: `o${b}`, juice: juiceOr(totalRow?.bestJuice) },
            bottom: { label: `u${b}`, juice: juiceOr(totalRow?.bestJuiceHome) },
          }
        : EMPTY_PAIR;

    const spreadKei = spreadRow?.kei;
    const totalKei = totalRow?.kei;
    // KEI spread is home-side; flip so Away (top) / Home (bottom) match Open/Best.
    const keiLine: PricePair = spreadKei
      ? {
          top: { label: flipSpread(spreadKei), juice: "—" },
          bottom: { label: spreadKei, juice: "—" },
        }
      : EMPTY_PAIR;
    const keiOU: PricePair = totalKei
      ? {
          top: { label: `o${totalKei}`, juice: "—" },
          bottom: { label: `u${totalKei}`, juice: "—" },
        }
      : EMPTY_PAIR;

    const parseSpread = (s: string): number | null => {
      const n = parseFloat(String(s).replace(/[^+\-\d.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    const parseTotal = (s: string): number | null => {
      const n = parseFloat(String(s).replace(/[^\d.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    // Edge only vs a real sportsbook/market best — never vs KEINFL provisional.
    const spreadBookKey = String(spreadRow?.bookKey ?? "").toLowerCase();
    const totalBookKey = String(totalRow?.bookKey ?? "").toLowerCase();
    const hasSportsbookSpread =
      Boolean(spreadRow?.best) &&
      spreadBookKey !== "" &&
      spreadBookKey !== "keinfl";
    const hasSportsbookTotal =
      Boolean(totalRow?.best) &&
      totalBookKey !== "" &&
      totalBookKey !== "keinfl";

    // Compare home-side market vs home-side KEI.
    // Signed edge matches fair-lines / nfl-edges: kei_home - market_home.
    // Negative => model likes Home more; positive => Away.
    const bestSpreadNum = parseSpread(bestLine.bottom.label);
    const keiSpreadNum = parseSpread(keiLine.bottom.label);
    const signedLineEdge =
      hasSportsbookSpread && bestSpreadNum != null && keiSpreadNum != null
        ? keiSpreadNum - bestSpreadNum
        : null;
    const edgeLineNum =
      signedLineEdge != null ? Math.abs(signedLineEdge) : undefined;
    const bestTotalNum = parseTotal(bestOU.top.label);
    const keiTotalNum = parseTotal(keiOU.top.label);
    const signedOUEdge =
      hasSportsbookTotal && bestTotalNum != null && keiTotalNum != null
        ? keiTotalNum - bestTotalNum
        : null;
    const edgeOUNum = signedOUEdge != null ? Math.abs(signedOUEdge) : undefined;

    // Exact zero = no directional lean (tag will be PASS).
    const leanHome =
      signedLineEdge != null && signedLineEdge !== 0
        ? signedLineEdge < 0
        : null;
    const leanOver =
      signedOUEdge != null && signedOUEdge !== 0 ? signedOUEdge > 0 : null;
    const edgeLineFavor =
      leanHome == null ? undefined : shortTeamLabel(leanHome ? home : away);
    const edgeOUFavor =
      leanOver == null
        ? undefined
        : leanOver
          ? ("Over" as const)
          : ("Under" as const);

    const playLine =
      leanHome == null
        ? undefined
        : leanHome
          ? `${shortTeamLabel(home)} ${bestLine.bottom.label}`
          : `${shortTeamLabel(away)} ${bestLine.top.label}`;
    const playOU =
      leanOver == null
        ? undefined
        : leanOver
          ? bestOU.top.label.replace(/^o/i, "Over ")
          : bestOU.bottom.label.replace(/^u/i, "Under ");

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
          keiLine.top.label !== "—" && keiLine.top.label !== "Coming soon"
            ? keiLine.top.label
            : undefined,
      },
      teamB: {
        name: home,
        site: "Home",
        keiNumber:
          keiLine.bottom.label !== "—" && keiLine.bottom.label !== "Coming soon"
            ? keiLine.bottom.label
            : undefined,
      },
      openOU,
      openLine,
      bestLine,
      bestOU,
      bestLineBook: spreadRow?.bookKey ?? spreadRow?.book,
      bestOUBook: totalRow?.bookKey ?? totalRow?.book,
      keiLine,
      keiOU,
      edgeLine: edgeLineDisplay,
      edgeOU: edgeOUDisplay,
      edgeLineNum,
      edgeOUNum,
      edgeLineFavor,
      edgeOUFavor,
      playLine,
      playOU,
      edgeOUCaution: isNflTotalCaution(edgeOUNum, sportKey),
      tagLine: edgeToTag(edgeLineNum, "line", sportKey),
      tagOU: edgeToTag(edgeOUNum, "total", sportKey),
      overview: generateGameOverview(away, home),
    });
  }
  return result;
}

export default function EdgeBoard({
  variant = "full",
  rows,
  sportKey = "ncaam",
}: {
  variant?: Variant;
  rows?: FlatEdgeBoardRow[] | null;
  /** Sport key drives the KEI column brand (KEICMB, KEINFL, …). Same board layout every sport. */
  sportKey?: string;
}) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const keiCode = getKeiCode(sportKey);
  const edgeGreen =
    "text-[#22c55e] font-bold drop-shadow-[0_0_10px_rgba(34,197,94,0.55)]";
  const hasRealData = safeRows.length > 0;
  const legacy = hasRealData
    ? flatRowsToLegacy(safeRows, sportKey)
    : sampleRows;
  const data = hasRealData ? legacy : sampleRows;
  const isNfl = String(sportKey).toLowerCase() === "nfl";

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
                  <th className="py-2.5 px-3">Best Line</th>
                  <th className="py-2.5 px-3">Best O/U</th>
                  <th className="py-2.5 px-3">Edge L/OU</th>
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
                      <div className="text-[11px] text-gray-400 tabular-nums">
                        {r.time ?? "—"}
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
                    <td className="py-2.5 px-3">
                      <div>{r.bestLine.top.label}</div>
                      <div className="text-[11px] text-gray-400">
                        ({r.bestLine.top.juice})
                      </div>
                      {r.bestLineBook ? (
                        <div className="mt-1">
                          <SportsbookBadge book={r.bestLineBook} compact />
                        </div>
                      ) : null}
                    </td>
                    <td className="py-2.5 px-3">
                      <div>{r.bestOU.top.label}</div>
                      <div className="text-[11px] text-gray-400">
                        ({r.bestOU.top.juice})
                      </div>
                      {r.bestOUBook ? (
                        <div className="mt-1">
                          <SportsbookBadge book={r.bestOUBook} compact />
                        </div>
                      ) : null}
                    </td>
                    <td className="py-2.5 px-3">
                      <div
                        className={`rounded px-1 py-0.5 ${edgeCellClass(r.tagLine)}`}
                      >
                        <EdgeSideCell
                          edgeNum={r.edgeLineNum}
                          favor={r.edgeLineFavor}
                          tag={r.tagLine}
                        />
                      </div>
                      <div
                        className={`mt-1 rounded px-1 py-0.5 ${edgeCellClass(r.tagOU)}`}
                      >
                        <EdgeSideCell
                          edgeNum={r.edgeOUNum}
                          favor={r.edgeOUFavor}
                          tag={r.tagOU}
                        />
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <TagPlayCell tag={r.tagLine} play={r.playLine} compact />
                      <div className="mt-1">
                        <TagPlayCell
                          tag={r.tagOU}
                          play={r.playOU}
                          compact
                          caution={r.edgeOUCaution}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 text-xs text-gray-400">
            Best Line/O/U (book) • Edge Line + O/U • Tag • Overview
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
            Live books • Open + Best + juice • Edge vs {keiCode}
          </div>
          <div className="text-xs text-gray-500">
            {safeRows.length
              ? `${new Set(safeRows.map((r) => r?.game).filter(Boolean)).size} games`
              : "Waiting for slate"}
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
                  <HeaderStack a={keiCode} b="Line" />
                </th>
                <th className="py-2.5 px-3">
                  <HeaderStack a={keiCode} b="O/U" />
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
                      book={r.bestLineBook}
                    />
                  </td>
                  <td className="py-2.5 px-3 align-top">
                    <PriceCell
                      p={r.bestOU}
                      compact
                      valueClassName="text-gray-100 font-semibold"
                      book={r.bestOUBook}
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
                    className={`py-2.5 px-2 align-top rounded ${edgeCellClass(r.tagLine)}`}
                  >
                    <EdgeSideCell
                      edgeNum={r.edgeLineNum}
                      favor={r.edgeLineFavor}
                      tag={r.tagLine}
                    />
                  </td>
                  <td
                    className={`py-2.5 px-2 align-top rounded ${edgeCellClass(r.tagOU)}`}
                  >
                    <EdgeSideCell
                      edgeNum={r.edgeOUNum}
                      favor={r.edgeOUFavor}
                      tag={r.tagOU}
                    />
                  </td>
                  <td className="py-2.5 px-2 align-top text-center">
                    <TagPlayCell tag={r.tagLine} play={r.playLine} />
                  </td>
                  <td className="py-2.5 px-2 align-top text-center">
                    <TagPlayCell
                      tag={r.tagOU}
                      play={r.playOU}
                      caution={r.edgeOUCaution}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-3 text-[10px] text-gray-400 border-t border-white/10">
          {isNfl
            ? "NFL tags — PASS default. Spread PLAY ≥2.5 (LEAN off). Total PLAY only 2.5–3.0 (≥3 PASS). "
            : "Tags — PASS / LEAN (≥1) / PLAY (≥2.5). "}
          Edge shows pts + side favored. Tag shows the action at the best book.{" "}
          {keiCode}: Kos Edge Index.
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
          Add <strong>ODDS_API_KEY</strong> in Vercel → Project Settings →
          Environment Variables, then redeploy. Get a key at{" "}
          <a
            href="https://the-odds-api.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-kos-gold hover:underline"
          >
            the-odds-api.com
          </a>{" "}
          (500 req/mo free).
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
