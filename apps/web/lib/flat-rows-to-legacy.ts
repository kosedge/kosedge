/**
 * Server-safe Edge Board flat → legacy row conversion.
 * Keep this module free of "use client" so RSC pages (overview, slate, edges)
 * can assemble tonight games without crossing the client boundary.
 */

import { cfbAwayBookToHome, trustCfbMarket } from "@/lib/cfb-trusted-market";
import {
  isNbaPreseason,
  nbaAwayBookToHome,
  nbaEdgeTag,
  trustNbaMarket,
} from "@/lib/nba-trusted-market";
import {
  isNhlPreseason,
  nhlAwayBookToHome,
  nhlEdgeTag,
} from "@/lib/nhl-trusted-market";
import { wnbaEdgeTag } from "@/lib/wnba-trusted-market";
import type { ActionLabel, ConfidenceBand } from "@/lib/nfl-decision-engine";
import { nflPublishTag } from "@/lib/nfl-publish-policy";
import {
  formatAmericanOdds,
  isValidAmericanOdds,
  noVigHomeProb,
} from "@/lib/american-odds";
import { buildMatchupContext } from "@/lib/edge-board-matchup-context";
import { buildMatchupOverview } from "@/lib/edge-board-matchup-overview";
import { buildStatDrop, type StatDrop } from "@/lib/edge-board-stat-drop";
import { sanitizeMarketCaptureIso } from "@/lib/market-asof-stamp";

/** Board revalidate cadence — matches Odds API cache TTL on /api/edge-board. */
const EDGE_BOARD_REFRESH_MS = 6 * 60 * 60 * 1000;
/** Stale if last odds capture older than this (same policy as refresh). */
const EDGE_BOARD_STALE_MS = EDGE_BOARD_REFRESH_MS;

export type FlatEdgeBoardRow = {
  id?: string;
  game?: string;
  time?: string;
  market?: string;
  open?: string;
  best?: string;
  book?: string;
  bookKey?: string;
  /** CFB: trust flag for Edge/Tag only — feed Best stays painted. */
  cfbMarketTrusted?: boolean;
  cfbTrustReason?: string;
  /** CFB footnote: `untrusted` | `no book` when not trusted. */
  cfbTrustLabel?: string;
  /** NBA Ch4: trust flag; Best cleared when untrusted. */
  nbaMarketTrusted?: boolean;
  nbaTrustReason?: string;
  nbaTrustLabel?: string;
  /** WNBA Ch4: trust flag; Best cleared when untrusted. */
  wnbaMarketTrusted?: boolean;
  wnbaTrustReason?: string;
  wnbaTrustLabel?: string;
  /** NHL Ch4: trust flag; Best cleared when untrusted. */
  nhlMarketTrusted?: boolean;
  nhlTrustReason?: string;
  nhlTrustLabel?: string;
  /** American odds juice for Open top (away / over). */
  openJuice?: string;
  /** American odds juice for Open bottom (home / under). */
  openJuiceHome?: string;
  bestJuice?: string;
  bestJuiceHome?: string;
  note?: string;
  commenceTime?: string;
  /** Stacked kickoff line 1 (e.g. 09/10). */
  kickoffDate?: string;
  /** Stacked kickoff line 2 (e.g. 8:35 PM). */
  kickoffTime?: string;
  /** ISO timestamp of latest odds capture — as-of / stale hint. */
  linesAsOf?: string;
  kei?: string;
  /** Research Model (pre-blend) when it diverges from published KEI handicap. */
  modelKei?: string;
  /** Fair away moneyline (American) when market is Moneyline. */
  keiAway?: string;
  /** Handicap (KEI) home win probability (0–1) for Moneyline edge in prob points. */
  homeWinProb?: number;
  awayWinProb?: number;
  /** REG / PRE / POST — PRE blocked from season PLAY under info desk. */
  seasonType?: string;
  week?: number;
  awayAbbr?: string;
  homeAbbr?: string;
  keiSpreadHome?: number;
  marketSpreadHome?: number;
  keiTotal?: number;
  marketTotal?: number;
  modelPowerAway?: number;
  modelPowerHome?: number;
  restDaysAway?: number;
  restDaysHome?: number;
  byeAway?: boolean;
  byeHome?: boolean;
  gamesPlayedAway?: number;
  gamesPlayedHome?: number;
  neutralSite?: boolean;
  neutralCity?: string;
  neutralVenue?: string;
  hfaPoints?: number;
  structuralTagAway?: string;
  structuralTagHome?: string;
  paceAway?: number;
  paceHome?: number;
  matchupOverview?: string;
  matchupVoice?: string;
  statDrop?: StatDrop;
  /** Authoritative server tag when present (fair-lines publish policy). */
  publishTag?: "PLAY" | "LEAN" | "PASS";
  /** Decision Engine action label (Model fair vs market) — NFL action layer. */
  actionLabel?: ActionLabel;
  /** Pure |model fair − market| — kept separate from confidence. */
  edgeMagnitude?: number;
  modelConfidenceScore?: number;
  modelConfidenceBand?: ConfidenceBand;
  modelConfidenceTierConstant?: boolean;
  coverProb?: number;
  playToNotes?: string;
  playToPlay?: number;
  playToLean?: number;
  playToPass?: number;
  fairLine?: number;
  decisionMarketLine?: number;
  isBestBet?: boolean;
  keyNumberCross?: boolean;
  weekRegime?: string;
};

export type EdgeBoardRow = FlatEdgeBoardRow;

export type Tag = "PLAY" | "LEAN" | "PASS";
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
  kickoffDate?: string;
  kickoffTime?: string;
  linesAsOf?: string;
  linesStale?: boolean;
  teamA: TeamBlock;
  teamB: TeamBlock;
  openOU: PricePair;
  openLine: PricePair;
  bestLine: PricePair;
  bestOU: PricePair;
  bestLineBook?: string;
  bestOUBook?: string;
  /** CFB: show beside Current when feed exists but trust failed. */
  bestLineTrustLabel?: string;
  /** CFB totals: same untrusted / no book footnote as spreads. */
  bestOUTrustLabel?: string;
  keiLine?: PricePair;
  keiOU?: PricePair;
  /** Optional Model (pre-blend) pair when it differs from KEI. */
  modelLine?: PricePair;
  modelOU?: PricePair;
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
  /** Tag policy (KEI vs market) — Action Labels + Play-To. */
  actionLabelLine?: ActionLabel;
  actionLabelOU?: ActionLabel;
  fairLineKei?: number;
  fairOUKei?: number;
  marketLineCurrent?: number;
  marketOUCurrent?: number;
  playToLineNum?: number;
  playToOUNum?: number;
  leanToLineNum?: number;
  leanToOUNum?: number;
  edgeMagnitudeLine?: number;
  edgeMagnitudeOU?: number;
  modelConfidenceScore?: number;
  modelConfidenceBand?: ConfidenceBand;
  modelConfidenceTierConstant?: boolean;
  coverProbLine?: number;
  coverProbOU?: number;
  playToLine?: string;
  playToOU?: string;
  isBestBetLine?: boolean;
  isBestBetOU?: boolean;
  overview?: string;
  statDrop?: StatDrop;
  isNeutral?: boolean;
  siteLabel?: string;
};

/** Empty market / KEI / edge cell — never show “Coming soon” on live boards. */

const EMPTY_PAIR: PricePair = {
  top: { label: "—", juice: "—" },
  bottom: { label: "—", juice: "—" },
};

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

export type EdgeMarket = "line" | "total";
function edgeToTag(
  edgeNum: number | undefined,
  market: EdgeMarket,
  sportKey = "ncaam",
  seasonType?: string | null,
  serverPublishTag?: Tag | null,
): Tag | undefined {
  if (edgeNum == null && !serverPublishTag) return undefined;
  const sport = String(sportKey).toLowerCase();
  const nfl = sport === "nfl";
  if (nfl) {
    // Prefer model-service publish tags when present (includes PRE block).
    if (
      serverPublishTag === "PLAY" ||
      serverPublishTag === "LEAN" ||
      serverPublishTag === "PASS"
    ) {
      return serverPublishTag;
    }
    if (edgeNum == null) return undefined;
    const pub = nflPublishTag(
      market === "total" ? "total" : "spread",
      edgeNum,
      "YELLOW",
      seasonType,
    );
    return pub.tag;
  }
  if (edgeNum == null && sport !== "cfb") return undefined;
  if (sport === "cfb") {
    // Edge Board honesty: only paint tags assemble already published.
    // Never invent PLAY/LEAN/PASS from edge when publishTag is absent.
    if (
      serverPublishTag === "PLAY" ||
      serverPublishTag === "LEAN" ||
      serverPublishTag === "PASS"
    ) {
      return serverPublishTag;
    }
    return undefined;
  }
  if (edgeNum == null) return undefined;
  if (sport === "nba") {
    // Chapter 4: LEAN ≥ 2.5 / PLAY ≥ 4.0 (trusted Best only; caller gates trust).
    return nbaEdgeTag(edgeNum);
  }
  if (sport === "wnba") {
    // Chapter 4: LEAN ≥ 2.5 / PLAY ≥ 4.0 (trusted Best only; caller gates trust).
    return wnbaEdgeTag(edgeNum);
  }
  if (sport === "nhl") {
    // Chapter 4: LEAN ≥ 2.5 / PLAY ≥ 4.0 goal units (trusted Best only).
    return nhlEdgeTag(edgeNum);
  }
  if (sport === "mlb" && market === "line") {
    if (edgeNum >= 3.0) return "PLAY";
    if (edgeNum >= 1.5) return "LEAN";
    return "PASS";
  }
  if (edgeNum >= 2.5) return "PLAY";
  if (edgeNum >= 1.0) return "LEAN";
  return "PASS";
}

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

function isLinesStale(linesAsOf?: string | null): boolean {
  if (!linesAsOf) return false;
  const ts = Date.parse(linesAsOf);
  if (!Number.isFinite(ts)) return false;
  return Date.now() - ts > EDGE_BOARD_STALE_MS;
}

function parseAmericanLabel(s: string | undefined): number | null {
  if (s == null || s === "" || s === "—") return null;
  const n = Number(String(s).replace(/^\+/, "").trim());
  return Number.isFinite(n) && n !== 0 ? n : null;
}

export function flatRowsToLegacy(
  flat: FlatEdgeBoardRow[],
  sportKey = "ncaam",
  slateWeek: number | null = null,
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
    {
      moneyline?: FlatEdgeBoardRow;
      spread?: FlatEdgeBoardRow;
      total?: FlatEdgeBoardRow;
    }
  >();
  for (const r of sorted) {
    const key = String(r?.game ?? r?.id ?? "unknown").trim() || "unknown";
    const entry = byGame.get(key) ?? {};
    if (r?.market === "Moneyline") entry.moneyline = r;
    else if (r?.market === "Spread") entry.spread = r;
    else if (r?.market === "Total") entry.total = r;
    byGame.set(key, entry);
  }
  const result: LegacyEdgeBoardRow[] = [];
  for (const [gameKey, entry] of byGame) {
    const lineRow = entry.moneyline ?? entry.spread;
    const isMoneyline = Boolean(entry.moneyline);
    const total = entry.total ?? lineRow;
    if (!lineRow && !total) continue;
    const game = String(lineRow?.game ?? total?.game ?? gameKey ?? "");
    const parts = game.includes(" @ ") ? game.split(" @ ") : game.split(" vs ");
    const away = (parts[0] ?? "Away").trim() || "Away";
    const home = (parts[1] ?? "Home").trim() || "Home";
    const time = (lineRow ?? total)?.time ?? "—";
    const flipSpread = (s: string | undefined): string => {
      const str = String(s ?? "").trim();
      if (!str) return "—";
      if (str.startsWith("+")) return `-${str.slice(1)}`;
      const n = parseFloat(str);
      return Number.isFinite(n) ? (n <= 0 ? `+${Math.abs(n)}` : `-${n}`) : "—";
    };
    const totalRow = total as FlatEdgeBoardRow | undefined;
    const juiceOr = (v: string | undefined) => {
      if (!v || v === "—") return "—";
      const n = Number(String(v).replace(/^\+/, ""));
      if (!Number.isFinite(n)) return "—";
      return isValidAmericanOdds(n) ? formatAmericanOdds(n) : "—";
    };

    let openLine: PricePair = EMPTY_PAIR;
    let bestLine: PricePair = EMPTY_PAIR;
    if (isMoneyline && lineRow) {
      // Americans are the price — do not flip like spreads.
      const openAway = lineRow.open ?? lineRow.openJuice;
      const openHome = lineRow.openJuiceHome;
      const bestAway = lineRow.best ?? lineRow.bestJuice ?? openAway;
      const bestHome = lineRow.bestJuiceHome ?? openHome;
      openLine = openAway
        ? {
            top: { label: openAway, juice: "—" },
            bottom: { label: openHome || "—", juice: "—" },
          }
        : EMPTY_PAIR;
      bestLine = bestAway
        ? {
            top: { label: bestAway, juice: "—" },
            bottom: { label: bestHome || "—", juice: "—" },
          }
        : EMPTY_PAIR;
    } else if (lineRow?.open || lineRow?.best) {
      openLine = lineRow?.open
        ? {
            top: { label: lineRow.open, juice: juiceOr(lineRow.openJuice) },
            bottom: {
              label: flipSpread(lineRow.open),
              juice: juiceOr(lineRow.openJuiceHome),
            },
          }
        : EMPTY_PAIR;
      bestLine = lineRow?.best
        ? {
            top: { label: lineRow.best, juice: juiceOr(lineRow.bestJuice) },
            bottom: {
              label: flipSpread(lineRow.best),
              juice: juiceOr(lineRow.bestJuiceHome),
            },
          }
        : EMPTY_PAIR;
    }
    // Open total only from true open — never invent open = current.
    const openTotalRaw = totalRow?.open;
    const openOU: PricePair =
      openTotalRaw && openTotalRaw !== "—"
        ? {
            top: {
              label: `o${openTotalRaw}`,
              juice: juiceOr(totalRow?.openJuice),
            },
            bottom: {
              label: `u${openTotalRaw}`,
              juice: juiceOr(totalRow?.openJuiceHome),
            },
          }
        : EMPTY_PAIR;
    const currentTotalRaw = totalRow?.best;
    const bestOU: PricePair =
      currentTotalRaw && currentTotalRaw !== "—"
        ? {
            top: {
              label: `o${currentTotalRaw}`,
              juice: juiceOr(totalRow?.bestJuice),
            },
            bottom: {
              label: `u${currentTotalRaw}`,
              juice: juiceOr(totalRow?.bestJuiceHome),
            },
          }
        : EMPTY_PAIR;

    const lineKei = lineRow?.kei;
    const totalKei = totalRow?.kei;
    let keiLine: PricePair = EMPTY_PAIR;
    if (isMoneyline) {
      const keiHome = lineKei;
      const keiAway = lineRow?.keiAway;
      if (keiHome || keiAway) {
        keiLine = {
          top: { label: keiAway || "—", juice: "—" },
          bottom: { label: keiHome || "—", juice: "—" },
        };
      }
    } else if (lineKei) {
      // KEI spread is home-side; flip so Away (top) / Home (bottom) match Open/Best.
      keiLine = {
        top: { label: flipSpread(lineKei), juice: "—" },
        bottom: { label: lineKei, juice: "—" },
      };
    }
    const keiOU: PricePair = totalKei
      ? {
          top: { label: `o${totalKei}`, juice: "—" },
          bottom: { label: `u${totalKei}`, juice: "—" },
        }
      : EMPTY_PAIR;

    const lineModel = (lineRow as FlatEdgeBoardRow | undefined)?.modelKei;
    const totalModel = (totalRow as FlatEdgeBoardRow | undefined)?.modelKei;
    let modelLine: PricePair | undefined;
    if (
      !isMoneyline &&
      lineModel &&
      lineKei &&
      String(lineModel) !== String(lineKei)
    ) {
      modelLine = {
        top: { label: flipSpread(lineModel), juice: "—" },
        bottom: { label: lineModel, juice: "—" },
      };
    }
    let modelOU: PricePair | undefined;
    if (totalModel && totalKei && String(totalModel) !== String(totalKei)) {
      modelOU = {
        top: { label: `o${totalModel}`, juice: "—" },
        bottom: { label: `u${totalModel}`, juice: "—" },
      };
    }

    const parseSpread = (s: string): number | null => {
      const n = parseFloat(String(s).replace(/[^+\-\d.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    const parseTotal = (s: string): number | null => {
      const n = parseFloat(String(s).replace(/[^\d.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    // Edge only vs a real sportsbook/market best — never vs KEINFL provisional.
    const lineBookKey = String(lineRow?.bookKey ?? "").toLowerCase();
    const totalBookKey = String(totalRow?.bookKey ?? "").toLowerCase();
    const hasSportsbookLine =
      Boolean(lineRow?.best || (isMoneyline && lineRow?.bestJuiceHome)) &&
      lineBookKey !== "" &&
      lineBookKey !== "keinfl";
    const hasSportsbookTotal =
      Boolean(totalRow?.best) &&
      totalBookKey !== "" &&
      totalBookKey !== "keinfl";

    let signedLineEdge: number | null = null;
    let edgeLineNum: number | undefined;
    let leanHome: boolean | null = null;

    if (isMoneyline) {
      // Prob-point edge: model home win prob − market no-vig home (same book pair).
      const modelHomeProb = lineRow?.homeWinProb;
      const bestAwayAm = parseAmericanLabel(bestLine.top.label);
      const bestHomeAm = parseAmericanLabel(bestLine.bottom.label);
      const marketHome =
        bestHomeAm != null && bestAwayAm != null
          ? noVigHomeProb(bestHomeAm, bestAwayAm)
          : null;
      if (
        hasSportsbookLine &&
        modelHomeProb != null &&
        Number.isFinite(modelHomeProb) &&
        marketHome != null
      ) {
        const signedProb = modelHomeProb - marketHome;
        signedLineEdge = signedProb;
        // Display / tag thresholds use percentage points (MLB: ≥1.5 LEAN / ≥3.0 PLAY).
        edgeLineNum = Math.abs(signedProb) * 100;
        leanHome = signedProb !== 0 ? signedProb > 0 : null; // +model vs market ⇒ Home
      }
    } else {
      // Compare home-side market vs home-side KEI.
      // Signed edge matches fair-lines / nfl-edges: kei_home - market_home.
      // Negative => model likes Home more; positive => Away.
      const bestSpreadNum = parseSpread(bestLine.bottom.label);
      const keiSpreadNum = parseSpread(keiLine.bottom.label);
      const sportLc = String(sportKey).toLowerCase();
      // CFB/NBA/NHL: board Open/Best are away-signed; KEI + bestLine.bottom are home.
      const openHome =
        sportLc === "nba"
          ? nbaAwayBookToHome(lineRow?.open)
          : sportLc === "nhl"
            ? nhlAwayBookToHome(lineRow?.open)
            : cfbAwayBookToHome(lineRow?.open);
      const bestHome =
        (sportLc === "nba"
          ? nbaAwayBookToHome(lineRow?.best)
          : sportLc === "nhl"
            ? nhlAwayBookToHome(lineRow?.best)
            : cfbAwayBookToHome(lineRow?.best)) ?? bestSpreadNum;
      const bookCount = openHome != null && bestHome != null ? 2 : 1;
      let marketTrusted = true;
      if (sportLc === "cfb") {
        marketTrusted =
          typeof lineRow?.cfbMarketTrusted === "boolean"
            ? lineRow.cfbMarketTrusted
            : trustCfbMarket({
                kei: lineRow?.kei ?? keiSpreadNum,
                best: bestHome,
                open: openHome,
                bookCount,
              }).trusted;
      } else if (sportLc === "nba") {
        marketTrusted =
          typeof lineRow?.nbaMarketTrusted === "boolean"
            ? lineRow.nbaMarketTrusted
            : trustNbaMarket({
                kei: lineRow?.kei ?? keiSpreadNum,
                best: bestHome,
                open: openHome,
                bookCount,
                preseason: isNbaPreseason(),
              }).trusted;
      } else if (sportLc === "nhl") {
        marketTrusted =
          typeof lineRow?.nhlMarketTrusted === "boolean"
            ? lineRow.nhlMarketTrusted
            : true;
      }
      signedLineEdge =
        hasSportsbookLine &&
        marketTrusted &&
        bestSpreadNum != null &&
        keiSpreadNum != null
          ? keiSpreadNum - bestSpreadNum
          : null;
      edgeLineNum =
        signedLineEdge != null ? Math.abs(signedLineEdge) : undefined;
      leanHome =
        signedLineEdge != null && signedLineEdge !== 0
          ? signedLineEdge < 0
          : null;
    }

    const bestTotalNum = parseTotal(bestOU.top.label);
    const keiTotalNum = parseTotal(keiOU.top.label);
    // CFB/NBA totals: absurd / single-book gate (no sign flip).
    const openTotalNum =
      totalRow?.open != null && String(totalRow.open) !== ""
        ? parseTotal(String(totalRow.open))
        : null;
    const bestTotalFromRow =
      totalRow?.best != null && String(totalRow.best) !== ""
        ? parseTotal(String(totalRow.best))
        : null;
    const totalBookCount =
      openTotalNum != null && (bestTotalFromRow ?? bestTotalNum) != null
        ? 2
        : 1;
    const sportLcTotal = String(sportKey).toLowerCase();
    let totalTrusted = true;
    if (sportLcTotal === "cfb") {
      totalTrusted =
        typeof totalRow?.cfbMarketTrusted === "boolean"
          ? totalRow.cfbMarketTrusted
          : trustCfbMarket({
              kei: totalRow?.kei ?? keiTotalNum,
              best: bestTotalFromRow ?? bestTotalNum,
              open: openTotalNum,
              bookCount: totalBookCount,
            }).trusted;
    } else if (sportLcTotal === "nba") {
      totalTrusted =
        typeof totalRow?.nbaMarketTrusted === "boolean"
          ? totalRow.nbaMarketTrusted
          : trustNbaMarket({
              kei: totalRow?.kei ?? keiTotalNum,
              best: bestTotalFromRow ?? bestTotalNum,
              open: openTotalNum,
              bookCount: totalBookCount,
              preseason: isNbaPreseason(),
            }).trusted;
    } else if (sportLcTotal === "nhl") {
      totalTrusted =
        typeof totalRow?.nhlMarketTrusted === "boolean"
          ? totalRow.nhlMarketTrusted
          : true;
    }
    const signedOUEdge =
      hasSportsbookTotal &&
      totalTrusted &&
      bestTotalNum != null &&
      keiTotalNum != null
        ? keiTotalNum - bestTotalNum
        : null;
    const edgeOUNum = signedOUEdge != null ? Math.abs(signedOUEdge) : undefined;

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
        : EMPTY_PAIR;
    const edgeOUDisplay: PricePair =
      edgeOUNum != null
        ? {
            top: { label: edgeOUNum.toFixed(1), juice: "—" },
            bottom: { label: edgeOUNum.toFixed(1), juice: "—" },
          }
        : EMPTY_PAIR;

    const tagLineRaw = edgeToTag(
      edgeLineNum,
      "line",
      sportKey,
      lineRow?.seasonType ?? totalRow?.seasonType,
      lineRow?.publishTag,
    );
    const tagOURaw = edgeToTag(
      edgeOUNum,
      "total",
      sportKey,
      totalRow?.seasonType ?? lineRow?.seasonType,
      totalRow?.publishTag,
    );
    // CFB Week 0 is the close tape — finals stay visible, never PLAY/LEAN.
    // NBA preseason / untrusted Best → PASS.
    // WNBA untrusted Best / Aug-1 leftovers → PASS.
    // NHL preseason / untrusted Best → PASS.
    const rowWeek = Number(lineRow?.week ?? totalRow?.week);
    const cfbFinalTape =
      String(sportKey).toLowerCase() === "cfb" && rowWeek === 0;
    const nbaForcePass =
      String(sportKey).toLowerCase() === "nba" &&
      (isNbaPreseason() ||
        lineRow?.nbaMarketTrusted === false ||
        totalRow?.nbaMarketTrusted === false);
    const wnbaForcePass =
      String(sportKey).toLowerCase() === "wnba" &&
      (lineRow?.wnbaMarketTrusted === false ||
        totalRow?.wnbaMarketTrusted === false);
    const nhlForcePass =
      String(sportKey).toLowerCase() === "nhl" &&
      (isNhlPreseason() ||
        lineRow?.nhlMarketTrusted === false ||
        totalRow?.nhlMarketTrusted === false);
    const forcePass =
      cfbFinalTape || nbaForcePass || wnbaForcePass || nhlForcePass;
    // CFB: never invent PASS when assemble omitted publishTag (research-only).
    // NBA / NHL / WNBA: untrusted / preseason is an explicit PASS posture.
    const tagLine = forcePass
      ? cfbFinalTape
        ? tagLineRaw
          ? ("PASS" as Tag)
          : undefined
        : ("PASS" as Tag)
      : tagLineRaw;
    const tagOU = forcePass
      ? cfbFinalTape
        ? tagOURaw
          ? ("PASS" as Tag)
          : undefined
        : ("PASS" as Tag)
      : tagOURaw;
    const playLineOut = forcePass ? undefined : playLine;
    const playOUOut = forcePass ? undefined : playOU;

    const src = (lineRow ?? totalRow) as FlatEdgeBoardRow | undefined;
    const srcSpread = entry.spread as FlatEdgeBoardRow | undefined;
    const srcTotal = entry.total as FlatEdgeBoardRow | undefined;
    const srcMl = entry.moneyline as FlatEdgeBoardRow | undefined;
    const pickField = <T>(
      getter: (r: FlatEdgeBoardRow | undefined) => T | null | undefined,
    ): T | null => {
      for (const r of [src, srcSpread, srcTotal, srcMl]) {
        const v = getter(r);
        if (v != null && v !== ("" as unknown)) return v as T;
      }
      return null;
    };
    const parseSignedNum = (s: string | undefined): number | null => {
      if (!s || s === "—") return null;
      const n = parseFloat(String(s).replace(/[^+\-\d.]/g, ""));
      return Number.isFinite(n) ? n : null;
    };
    // Current for Action Mkt: dedicated decision market, else home-side Current.
    const marketLineFromCurrent = !isMoneyline
      ? parseSignedNum(bestLine.bottom.label)
      : null;
    const marketOUFromCurrent = parseTotal(bestOU.top.label);
    const resolveActionMarket = (
      decisionMkt: number | null | undefined,
      fromCurrent: number | null,
    ): number | undefined => {
      if (decisionMkt != null && Number.isFinite(decisionMkt))
        return decisionMkt;
      if (fromCurrent != null && Number.isFinite(fromCurrent))
        return fromCurrent;
      return undefined;
    };
    const resolveActionEdge = (
      decisionEdge: number | null | undefined,
      displayEdge: number | undefined,
      market: number | undefined,
    ): number | undefined => {
      if (market == null) return undefined;
      if (decisionEdge != null && Number.isFinite(decisionEdge)) {
        // Stale 0.0 while display edge is non-zero → prefer display (KEI vs Current).
        if (decisionEdge === 0 && displayEdge != null && displayEdge > 0) {
          return displayEdge;
        }
        return decisionEdge;
      }
      return displayEdge;
    };
    const keiSpreadHome =
      pickField((r) => r?.keiSpreadHome) ??
      (!isMoneyline ? parseSignedNum(keiLine.bottom.label) : null);
    const marketSpreadHome =
      pickField((r) => r?.marketSpreadHome) ??
      (!isMoneyline ? parseSignedNum(bestLine.bottom.label) : null);
    const matchupKeiTotal = pickField((r) => r?.keiTotal) ?? keiTotalNum;
    const matchupMarketTotal = pickField((r) => r?.marketTotal) ?? bestTotalNum;
    const weekNum = (() => {
      const w = pickField((r) => r?.week as number | null | undefined);
      if (w != null) {
        const n = Number(w);
        if (Number.isFinite(n)) return Math.trunc(n);
      }
      if (slateWeek != null && Number.isFinite(Number(slateWeek))) {
        return Math.trunc(Number(slateWeek));
      }
      return null;
    })();

    const matchupCtx = buildMatchupContext({
      gameId: String(src?.id ?? gameKey).replace(/-spread$|-total$/, ""),
      awayName: away,
      homeName: home,
      awayAbbr: pickField((r) => r?.awayAbbr) ?? undefined,
      homeAbbr: pickField((r) => r?.homeAbbr) ?? undefined,
      week: weekNum,
      seasonType: pickField((r) => r?.seasonType) ?? null,
      gamesPlayedAway: pickField((r) => r?.gamesPlayedAway) ?? null,
      gamesPlayedHome: pickField((r) => r?.gamesPlayedHome) ?? null,
      keiSpreadHome,
      marketSpreadHome,
      keiTotal: matchupKeiTotal,
      marketTotal: matchupMarketTotal,
      homeWinProb: pickField((r) => r?.homeWinProb),
      awayWinProb: pickField((r) => r?.awayWinProb),
      restDaysAway: pickField((r) => r?.restDaysAway),
      restDaysHome: pickField((r) => r?.restDaysHome),
      byeAway: Boolean(pickField((r) => r?.byeAway)),
      byeHome: Boolean(pickField((r) => r?.byeHome)),
      modelPowerAway: pickField((r) => r?.modelPowerAway),
      modelPowerHome: pickField((r) => r?.modelPowerHome),
      neutralSite: pickField((r) => r?.neutralSite),
      neutralCity: pickField((r) => r?.neutralCity),
      neutralVenue: pickField((r) => r?.neutralVenue),
      hfaPoints: pickField((r) => r?.hfaPoints),
      publishTagSpread: pickField((r) => r?.publishTag),
      edgeSpreadAbs: edgeLineNum ?? null,
    });
    // Always rebuild from context so season/neutral gates stay honest even if
    // an upstream enrich pass missed week / site fields.
    const overviewText = buildMatchupOverview(matchupCtx).text;
    const statDrop = buildStatDrop(matchupCtx);
    const homeSiteLabel: "Away" | "Home" = matchupCtx.isNeutral
      ? "Home"
      : "Home";
    const awaySiteLabel: "Away" | "Home" = "Away";

    const linesAsOf =
      sanitizeMarketCaptureIso(
        lineRow?.linesAsOf ?? totalRow?.linesAsOf ?? undefined,
      ) ?? undefined;
    result.push({
      id: String(lineRow?.id ?? total?.id ?? gameKey),
      time,
      kickoffDate: lineRow?.kickoffDate ?? totalRow?.kickoffDate,
      kickoffTime: lineRow?.kickoffTime ?? totalRow?.kickoffTime,
      linesAsOf,
      linesStale: isLinesStale(linesAsOf),
      teamA: {
        name: away,
        site: awaySiteLabel,
        keiNumber: keiLine.top.label !== "—" ? keiLine.top.label : undefined,
      },
      teamB: {
        name: home,
        site: homeSiteLabel,
        keiNumber:
          keiLine.bottom.label !== "—" ? keiLine.bottom.label : undefined,
      },
      openOU,
      openLine,
      bestLine,
      bestOU,
      // Prefer bookKey; fall through to book for sportsbook chip.
      bestLineBook: lineRow?.bookKey || lineRow?.book,
      bestOUBook: totalRow?.bookKey || totalRow?.book,
      bestLineTrustLabel: lineRow?.cfbTrustLabel,
      bestOUTrustLabel: totalRow?.cfbTrustLabel,
      keiLine,
      keiOU,
      modelLine,
      modelOU,
      edgeLine: edgeLineDisplay,
      edgeOU: edgeOUDisplay,
      edgeLineNum,
      edgeOUNum,
      edgeLineFavor,
      edgeOUFavor,
      playLine: playLineOut,
      playOU: playOUOut,
      edgeOUCaution: isNflTotalCaution(edgeOUNum, sportKey),
      tagLine,
      tagOU,
      actionLabelLine: lineRow?.actionLabel,
      actionLabelOU: totalRow?.actionLabel,
      edgeMagnitudeLine: resolveActionEdge(
        lineRow?.edgeMagnitude,
        edgeLineNum,
        resolveActionMarket(lineRow?.decisionMarketLine, marketLineFromCurrent),
      ),
      edgeMagnitudeOU: resolveActionEdge(
        totalRow?.edgeMagnitude,
        edgeOUNum,
        resolveActionMarket(totalRow?.decisionMarketLine, marketOUFromCurrent),
      ),
      modelConfidenceScore:
        lineRow?.modelConfidenceScore ?? totalRow?.modelConfidenceScore,
      modelConfidenceBand:
        lineRow?.modelConfidenceBand ?? totalRow?.modelConfidenceBand,
      modelConfidenceTierConstant:
        lineRow?.modelConfidenceTierConstant ??
        totalRow?.modelConfidenceTierConstant,
      coverProbLine: lineRow?.coverProb,
      coverProbOU: totalRow?.coverProb,
      playToLine: lineRow?.playToNotes,
      playToOU: totalRow?.playToNotes,
      playToLineNum: lineRow?.playToPlay,
      playToOUNum: totalRow?.playToPlay,
      leanToLineNum: lineRow?.playToLean,
      leanToOUNum: totalRow?.playToLean,
      fairLineKei: lineRow?.fairLine ?? undefined,
      fairOUKei: totalRow?.fairLine ?? undefined,
      marketLineCurrent: resolveActionMarket(
        lineRow?.decisionMarketLine,
        marketLineFromCurrent,
      ),
      marketOUCurrent: resolveActionMarket(
        totalRow?.decisionMarketLine,
        marketOUFromCurrent,
      ),
      isBestBetLine: lineRow?.isBestBet,
      isBestBetOU: totalRow?.isBestBet,
      overview: overviewText,
      statDrop,
      isNeutral: matchupCtx.isNeutral,
      siteLabel: matchupCtx.isNeutral
        ? `Neutral${matchupCtx.siteCity ? ` · ${matchupCtx.siteCity}` : ""}`
        : undefined,
    });
  }
  return result;
}
