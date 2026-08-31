"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import SportsbookBadge from "@/components/SportsbookBadge";
import { cfbAwayBookToHome, trustCfbMarket } from "@/lib/cfb-trusted-market";
import { sportIsMarketsOnlyEdgeBoard } from "@/lib/edge-board-kei-availability";
import { getKeiCode } from "@/lib/kei-brand";
import type { ActionLabel, ConfidenceBand } from "@/lib/nfl-decision-engine";
import { nflPublishTag } from "@/lib/nfl-publish-policy";
import {
  formatAmericanOdds,
  isValidAmericanOdds,
  noVigHomeProb,
} from "@/lib/american-odds";
import EdgeBoardStatDrop from "@/components/EdgeBoardStatDrop";
import { buildMatchupContext } from "@/lib/edge-board-matchup-context";
import { buildMatchupOverview } from "@/lib/edge-board-matchup-overview";
import { buildStatDrop, type StatDrop } from "@/lib/edge-board-stat-drop";

/** Board revalidate cadence — matches Odds API cache TTL on /api/edge-board. */
const EDGE_BOARD_REFRESH_MS = 6 * 60 * 60 * 1000;
/** Stale if last odds capture older than this (same policy as refresh). */
const EDGE_BOARD_STALE_MS = EDGE_BOARD_REFRESH_MS;

type ExpandPanel = "overview" | "stats" | null;

// Flat API row format (from Odds API / model); kei = our projected line/total/ML
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

const sampleMatchupCtx = buildMatchupContext({
  gameId: "sample-duke-unc",
  awayName: "Duke",
  homeName: "UNC",
  week: 8,
  keiSpreadHome: -5.5,
  marketSpreadHome: -5.0,
  keiTotal: 150.5,
  marketTotal: 149.5,
});
const sampleOverview = buildMatchupOverview(sampleMatchupCtx);
const sampleStatDrop = buildStatDrop(sampleMatchupCtx);

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
    overview: sampleOverview.text,
    statDrop: sampleStatDrop,
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
    ? "inline-flex px-2.5 py-1 rounded-md text-[12px] font-bold tracking-wide"
    : "inline-flex items-center justify-center min-w-[3.5rem] px-2.5 py-1.5 rounded-md text-[13px] font-bold tracking-wide";
  if (tag === "PLAY") return `${base} bg-edge-green text-black`;
  if (tag === "LEAN") return `${base} bg-amber-500 text-black`;
  return `${base} bg-white/10 text-gray-400`;
}

function actionLabelClassName(label: ActionLabel, compact = false): string {
  const base = compact
    ? "inline-flex px-2 py-0.5 rounded-md text-[11px] font-bold tracking-wide"
    : "inline-flex items-center justify-center px-2 py-1 rounded-md text-[12px] font-bold tracking-wide";
  if (label === "BEST VALUE") return `${base} bg-kos-gold text-black`;
  if (label === "PLAY") return `${base} bg-edge-green text-black`;
  if (label === "LEAN") return `${base} bg-amber-500 text-black`;
  if (label === "ALERT") return `${base} bg-orange-500/90 text-black`;
  if (label === "STAY AWAY") return `${base} bg-red-500/80 text-white`;
  return `${base} bg-white/10 text-gray-400`;
}

function formatConfidenceLabel(
  band?: ConfidenceBand,
  score?: number,
  tierConstant?: boolean,
): string | null {
  if (!band) return null;
  // Tier-constant 0.72/MEDIUM (and penalty landings) are bands — not calibrated %.
  if (tierConstant || score == null) return `Conf ${band}`;
  return `Conf ${band} ${Math.round(score * 100)}%`;
}

function fmtSignedHalf(n: number): string {
  if (Object.is(n, -0) || n === 0) return "+0";
  return n > 0 ? `+${n}` : String(n);
}

function ActionDecisionCell({
  actionLabel,
  publishTag,
  play,
  playToNotes,
  playToNum,
  leanToNum,
  fairKei,
  marketCurrent,
  edgeMagnitude,
  confidenceBand,
  confidenceScore,
  confidenceTierConstant,
  coverProb,
  compact = false,
  caution = false,
}: {
  actionLabel?: ActionLabel;
  publishTag?: Tag;
  play?: string;
  playToNotes?: string;
  playToNum?: number;
  leanToNum?: number;
  fairKei?: number;
  marketCurrent?: number;
  edgeMagnitude?: number;
  confidenceBand?: ConfidenceBand;
  confidenceScore?: number;
  /** When true, 72%/47% style scores are tier constants — show band only. */
  confidenceTierConstant?: boolean;
  coverProb?: number;
  compact?: boolean;
  caution?: boolean;
}) {
  if (!actionLabel && !publishTag) {
    return <span className="text-gray-500">—</span>;
  }
  const confLabel = formatConfidenceLabel(
    confidenceBand,
    confidenceScore,
    confidenceTierConstant,
  );
  const showLadder =
    actionLabel === "PLAY" ||
    actionLabel === "LEAN" ||
    actionLabel === "BEST VALUE" ||
    actionLabel === "ALERT";
  const ladderVerb =
    actionLabel === "LEAN"
      ? "Lean to"
      : actionLabel === "ALERT"
        ? "Was to"
        : "Play to";
  const ladderNum =
    actionLabel === "LEAN" && leanToNum != null
      ? leanToNum
      : playToNum != null
        ? playToNum
        : null;
  return (
    <div className={compact ? "leading-tight" : "leading-tight text-center"}>
      {actionLabel ? (
        <span className={actionLabelClassName(actionLabel, compact)}>
          {actionLabel}
        </span>
      ) : publishTag ? (
        <span className={tagClassName(publishTag, compact)}>{publishTag}</span>
      ) : null}
      {play &&
      actionLabel &&
      actionLabel !== "PASS" &&
      actionLabel !== "STAY AWAY" ? (
        <div
          className={`mt-1 text-[11px] font-bold truncate ${
            actionLabel === "PLAY" || actionLabel === "BEST VALUE"
              ? "text-edge-green"
              : actionLabel === "LEAN"
                ? "text-amber-400"
                : "text-orange-300"
          }`}
        >
          {play}
        </div>
      ) : null}
      {edgeMagnitude != null &&
      !(edgeMagnitude === 0 && marketCurrent == null) ? (
        <div className="mt-1 text-[10px] text-gray-300 tabular-nums">
          Edge {edgeMagnitude.toFixed(1)}
          {coverProb != null ? (
            <span className="text-gray-500">
              {" "}
              · {(coverProb * 100).toFixed(1)}%
            </span>
          ) : null}
        </div>
      ) : coverProb != null ? (
        <div className="mt-1 text-[10px] text-gray-500 tabular-nums">
          Cover {(coverProb * 100).toFixed(1)}%
        </div>
      ) : marketCurrent == null && fairKei != null ? (
        <div className="mt-1 text-[10px] text-gray-500">Edge —</div>
      ) : null}
      {confLabel ? (
        <div className="mt-0.5 text-[10px] text-gray-500">{confLabel}</div>
      ) : null}
      {fairKei != null || marketCurrent != null ? (
        <div className="mt-0.5 text-[9px] text-gray-500 tabular-nums">
          Fair KEI {fairKei != null ? fmtSignedHalf(fairKei) : "—"}
          {" · "}
          Mkt {marketCurrent != null ? fmtSignedHalf(marketCurrent) : "—"}
        </div>
      ) : null}
      {showLadder && ladderNum != null ? (
        <div
          className="mt-1 text-[10px] font-semibold text-gray-300 tabular-nums"
          title={playToNotes}
        >
          {ladderVerb} {fmtSignedHalf(ladderNum)}
        </div>
      ) : showLadder && playToNotes ? (
        <div
          className="mt-1 text-[9px] text-gray-400 leading-snug line-clamp-3"
          title={playToNotes}
        >
          {playToNotes}
        </div>
      ) : null}
      {caution && actionLabel && actionLabel !== "PASS" ? (
        <div className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-amber-300/90">
          Size down
        </div>
      ) : null}
      {publishTag && actionLabel && publishTag !== actionLabel ? (
        <div className="mt-1 text-[9px] text-gray-600">Desk {publishTag}</div>
      ) : null}
    </div>
  );
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
    return <span className="text-gray-500 text-sm">—</span>;
  }
  return (
    <div className="leading-tight">
      <div className="text-[17px] font-bold tabular-nums tracking-tight">
        {edgeNum.toFixed(1)}
      </div>
      {favor ? (
        <div
          className={`mt-1 text-[12px] font-bold truncate ${favorTextClass(tag)}`}
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
          className={`mt-1.5 text-[12px] font-bold truncate ${favorTextClass(tag)}`}
        >
          {play}
        </div>
      ) : null}
      {caution && tag !== "PASS" ? (
        <div className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-amber-300/90">
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
  trustLabel,
}: {
  p: PricePair;
  valueClassName?: string;
  compact?: boolean;
  /** Sportsbook that holds this best price (shown under the lines). */
  book?: string | null;
  /** CFB: `untrusted` / `no book` — shown with the number, never instead of it. */
  trustLabel?: string | null;
}) {
  const sep = compact ? "mt-1 h-px" : "mt-1.5 h-px";
  const topPad = compact ? "mt-1" : "mt-1.5";
  const valueLeading = compact ? "leading-[1.05]" : "leading-tight";
  const blank =
    p.top.label === "Coming soon" ||
    p.bottom.label === "Coming soon" ||
    p.top.label === "—" ||
    p.bottom.label === "—";
  const showTopJuice = Boolean(p.top.juice && p.top.juice !== "—");
  const showBottomJuice = Boolean(p.bottom.juice && p.bottom.juice !== "—");
  const trustNote =
    trustLabel === "untrusted" || trustLabel === "no book" ? trustLabel : null;
  const bookIsTrustOnly =
    book === "untrusted" || book === "no book" ? book : null;
  const footnote = trustNote || (blank ? bookIsTrustOnly : null);
  const showBookBadge =
    !blank && book && book !== "untrusted" && book !== "no book";

  return (
    <div className={valueLeading}>
      <div className={valueClassName}>{p.top.label}</div>
      {showTopJuice ? (
        <div className="text-[11px] text-gray-400">({p.top.juice})</div>
      ) : null}
      <div className={`${sep} bg-white/10`} />
      <div className={`${topPad} ${valueClassName}`}>{p.bottom.label}</div>
      {showBottomJuice ? (
        <div className="text-[11px] text-gray-400">({p.bottom.juice})</div>
      ) : null}
      {showBookBadge ? (
        <div className={`${topPad}`}>
          <SportsbookBadge book={book} compact />
        </div>
      ) : null}
      {footnote ? (
        <div className={`${topPad} text-[10px] text-gray-400`}>{footnote}</div>
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
 * MLB moneyline: probability-point edge — LEAN ≥1.5pp · PLAY ≥3.0pp
 * MLB totals: still run-point edge — legacy LEAN ≥1.0 · PLAY ≥2.5
 * Other sports keep the legacy 1.0 / 2.5 cut for both markets.
 */
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
  if (edgeNum == null) return undefined;
  if (sport === "cfb") {
    if (edgeNum >= 4.0) return "PLAY";
    if (edgeNum >= 2.5) return "LEAN";
    return "PASS";
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

/** Cell chrome matches the tag — muted PASS, amber LEAN, green PLAY. */
function edgeCellClass(tag: Tag | undefined): string {
  if (tag == null) return "bg-white/5 text-gray-500";
  if (tag === "PLAY") return "bg-edge-green/25 text-edge-green";
  if (tag === "LEAN") return "bg-amber-500/20 text-amber-400";
  return "bg-white/[0.04] text-gray-400";
}

function favorTextClass(tag: Tag | undefined): string {
  if (tag === "PLAY") return "text-edge-green";
  if (tag === "LEAN") return "text-amber-400";
  return "text-gray-400";
}

/** Market (Best) vs KEI handicap column chrome — contrast without card clutter. */
const COL_MARKET = "bg-white/[0.035] border-l border-white/10";
const COL_KEI = "bg-kos-gold/[0.07] border-l border-kos-gold/25";
/** @deprecated Use COL_KEI — kept as alias during migration. */
const COL_MODEL = COL_KEI;
const COL_DECISION = "border-l border-white/12";
const TH_BASE = "py-3 px-3";
const TD_BASE = "py-4 px-3 align-top";
/** pb-11 reserves room for absolute Overview/Stats at a shared baseline. */
const TD_GAME = "relative py-4 px-3 pb-11 align-top";
const TD_KICKOFF = "relative py-4 px-2 pb-11 align-top";
const TD_DECISION = "py-4 px-2.5 align-top";
const ROW_CTRL_BTN =
  "absolute bottom-2.5 min-h-9 rounded-lg text-[13px] font-medium text-kos-gold hover:bg-white/5 hover:underline";

const COL_WIDTHS = [
  "210px",
  "96px",
  "92px",
  "92px",
  "100px",
  "100px",
  "96px",
  "96px",
  "92px",
  "92px",
  "120px",
  "120px",
] as const;

function parseKickoffStack(args: {
  kickoffDate?: string;
  kickoffTime?: string;
  time?: string;
}): { date: string; time: string; local: string } {
  if (args.kickoffDate || args.kickoffTime) {
    return {
      date: args.kickoffDate || "—",
      time: args.kickoffTime || "—",
      local: "ET",
    };
  }
  const raw = String(args.time ?? "").trim();
  if (!raw || raw === "—") return { date: "—", time: "—", local: "" };
  // "09/10 8:35 PM ET" or similar
  const m = raw.match(/^(\d{1,2}\/\d{1,2})\s+(.+?)(?:\s+(ET|PT|CT|MT))?$/i);
  if (m) {
    return {
      date: m[1]!,
      time: m[2]!.trim(),
      local: (m[3] || "ET").toUpperCase(),
    };
  }
  return { date: raw, time: "", local: "" };
}

function KickoffStack({
  kickoffDate,
  kickoffTime,
  time,
}: {
  kickoffDate?: string;
  kickoffTime?: string;
  time?: string;
}) {
  const k = parseKickoffStack({ kickoffDate, kickoffTime, time });
  return (
    <div className="leading-snug tabular-nums">
      <div className="text-sm font-semibold text-gray-200">{k.date}</div>
      {k.time ? (
        <div className="mt-0.5 text-xs text-gray-400">
          {k.time}
          {k.local ? (
            <span className="ml-1 text-[10px] uppercase tracking-wide text-gray-500">
              {k.local}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
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
      // CFB: board Open/Best are away-signed; KEI + bestLine.bottom are home.
      // Prefer assemble-time trust flag; else recompute (same helper).
      const openHome = cfbAwayBookToHome(lineRow?.open);
      const bestHome = cfbAwayBookToHome(lineRow?.best) ?? bestSpreadNum;
      const cfbBookCount = openHome != null && bestHome != null ? 2 : 1;
      const cfbTrusted =
        String(sportKey).toLowerCase() !== "cfb"
          ? true
          : typeof lineRow?.cfbMarketTrusted === "boolean"
            ? lineRow.cfbMarketTrusted
            : trustCfbMarket({
                kei: lineRow?.kei ?? keiSpreadNum,
                best: bestHome,
                open: openHome,
                bookCount: cfbBookCount,
              }).trusted;
      signedLineEdge =
        hasSportsbookLine &&
        cfbTrusted &&
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
    const signedOUEdge =
      hasSportsbookTotal && bestTotalNum != null && keiTotalNum != null
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

    const tagLine = edgeToTag(
      edgeLineNum,
      "line",
      sportKey,
      lineRow?.seasonType ?? totalRow?.seasonType,
      lineRow?.publishTag,
    );
    const tagOU = edgeToTag(
      edgeOUNum,
      "total",
      sportKey,
      totalRow?.seasonType ?? lineRow?.seasonType,
      totalRow?.publishTag,
    );

    const src = (lineRow ?? totalRow) as FlatEdgeBoardRow | undefined;
    const srcSpread = entry.spread as FlatEdgeBoardRow | undefined;
    const srcTotal = entry.total as FlatEdgeBoardRow | undefined;
    const srcMl = entry.moneyline as FlatEdgeBoardRow | undefined;
    const pickField = <T,>(
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

    const linesAsOf = lineRow?.linesAsOf ?? totalRow?.linesAsOf ?? undefined;
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
      playLine,
      playOU,
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

export default function EdgeBoard({
  variant = "full",
  rows,
  sportKey = "ncaam",
  slateWeek = null,
  emptyHint,
}: {
  variant?: Variant;
  rows?: FlatEdgeBoardRow[] | null;
  /** Sport key drives the KEI column brand (KEICMB, KEINFL, …). Same board layout every sport. */
  sportKey?: string;
  /** Active board week (e.g. Week 1 tab) — backs season gates when row.week is missing. */
  slateWeek?: number | null;
  /** Optional empty-state copy (e.g. honest Week 1 empty). */
  emptyHint?: string;
}) {
  const router = useRouter();
  const safeRows = Array.isArray(rows) ? rows : [];
  const keiCode = getKeiCode(sportKey);
  const edgeGreen =
    "text-[#22c55e] font-bold drop-shadow-[0_0_10px_rgba(34,197,94,0.55)]";
  const hasRealData = safeRows.length > 0;
  const [expanded, setExpanded] = React.useState<{
    id: string;
    panel: Exclude<ExpandPanel, null>;
  } | null>(null);

  // Soft refresh Current lines on the Odds / fair-lines cadence (no redeploy).
  React.useEffect(() => {
    if (variant !== "full" || !hasRealData) return;
    const id = window.setInterval(() => {
      router.refresh();
    }, EDGE_BOARD_REFRESH_MS);
    return () => window.clearInterval(id);
  }, [variant, hasRealData, router]);

  const toggleExpand = React.useCallback(
    (id: string, panel: Exclude<ExpandPanel, null>) => {
      setExpanded((prev) =>
        prev?.id === id && prev.panel === panel ? null : { id, panel },
      );
    },
    [],
  );
  const inferredWeek = (() => {
    if (slateWeek != null && Number.isFinite(Number(slateWeek))) {
      return Math.trunc(Number(slateWeek));
    }
    const fromRows = safeRows
      .map((r) => Number(r?.week))
      .filter((w) => Number.isFinite(w));
    return fromRows.length ? Math.trunc(fromRows[0]!) : null;
  })();
  const legacy = hasRealData
    ? flatRowsToLegacy(safeRows, sportKey, inferredWeek)
    : sampleRows;
  const data = hasRealData ? legacy : sampleRows;
  const isNfl = String(sportKey).toLowerCase() === "nfl";
  const isMlb = String(sportKey).toLowerCase() === "mlb";
  const marketsOnly = sportIsMarketsOnlyEdgeBoard(sportKey);
  const lineLabel = isMlb ? "Moneyline" : "Line";
  // KEI = final handicap when a model exists. Markets-only sports leave cells "—".
  const keiLineHeader = "KEI";
  const keiOuHeader = "KEI";
  const edgeLineLabel = isMlb ? "ML edge" : "Spread edge";

  if (variant === "home") {
    return (
      <div className="lg:col-span-5">
        <div className="relative">
          <div className="absolute -inset-1 rounded-3xl bg-linear-to-r from-kos-gold/25 via-kos-green/15 to-kos-gold/25 blur-2xl opacity-80" />
          <div className="relative bg-black/40 border border-white/12 rounded-3xl p-5 sm:p-6 backdrop-blur-xl shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-3xl font-bebas text-edge-green">
                Edge Board
              </h2>
              <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-gray-400">
                Sample
              </span>
            </div>
            <div className="overflow-hidden rounded-2xl border border-white/10">
              <table className="w-full text-sm sm:text-base">
                <thead className="bg-white/5">
                  <tr className="text-left text-gray-300">
                    <th className="py-2.5 px-3">Game</th>
                    <th className="py-2.5 px-3">
                      {isMlb ? "Best Moneyline" : "Best Line"}
                    </th>
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
                      <td className="py-2.5 px-3 text-gray-500">—</td>
                      <td className="py-2.5 px-3 text-gray-500">—</td>
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
    <div className="lg:hidden mt-4 space-y-4">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-2xl font-bebas text-edge-green">Edge Board</h2>
        <span className="text-xs bg-white/5 px-2.5 py-1 rounded text-gray-400">
          {safeRows.length
            ? `${new Set(safeRows.map((r) => r?.game).filter(Boolean)).size} games`
            : "Live"}
        </span>
      </div>
      <p className="px-1 text-xs text-gray-400">
        {marketsOnly
          ? `Markets only · ${keiCode} handicap not shipped yet · ET`
          : `KEI handicap (${keiCode}) vs Market · Open + Current · ET`}
      </p>
      {marketsOnly ? (
        <p className="px-1 text-[11px] text-amber-200/80">
          Open/Current from books when available. KEI Line / O/U / Edge stay
          blank until a real model exists — we do not invent handicap numbers.
          {String(sportKey).toLowerCase() === "cfb"
            ? " Books ≠ KEI. Project Game stays MODEL research."
            : ""}
        </p>
      ) : null}
      {data.map((r) => {
        const overviewOpen =
          expanded?.id === r.id && expanded.panel === "overview";
        const statsOpen = expanded?.id === r.id && expanded.panel === "stats";
        return (
          <article
            key={r.id}
            className="rounded-2xl border border-white/14 bg-black/45 p-3.5 sm:p-4 backdrop-blur-xl"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-gray-100 leading-snug">
                  {r.isNeutral
                    ? `${r.teamA.name} vs ${r.teamB.name}`
                    : `${r.teamA.name} @ ${r.teamB.name}`}
                </h3>
                <div className="mt-1">
                  <KickoffStack
                    kickoffDate={r.kickoffDate}
                    kickoffTime={r.kickoffTime}
                    time={r.time}
                  />
                </div>
                {r.siteLabel ? (
                  <p className="mt-1 text-[11px] text-amber-200/90">
                    {r.siteLabel}
                  </p>
                ) : (
                  <p className="mt-1 text-[11px] text-gray-400">
                    {r.teamA.site} / {r.teamB.site}
                  </p>
                )}
                {r.linesStale && r.linesAsOf ? (
                  <p className="mt-1 text-[10px] text-amber-300/80">
                    Lines as of{" "}
                    {new Date(r.linesAsOf).toLocaleString("en-US", {
                      month: "2-digit",
                      day: "2-digit",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </p>
                ) : null}
              </div>
              <div className="shrink-0 text-right">
                {isNfl ? (
                  <ActionDecisionCell
                    actionLabel={r.actionLabelLine}
                    publishTag={r.tagLine}
                    play={r.playLine}
                    playToNotes={r.playToLine}
                    playToNum={r.playToLineNum}
                    leanToNum={r.leanToLineNum}
                    fairKei={r.fairLineKei}
                    marketCurrent={r.marketLineCurrent}
                    edgeMagnitude={r.edgeMagnitudeLine}
                    confidenceBand={r.modelConfidenceBand}
                    confidenceScore={r.modelConfidenceScore}
                    confidenceTierConstant={r.modelConfidenceTierConstant}
                    coverProb={r.coverProbLine}
                    compact
                  />
                ) : (
                  <TagPlayCell tag={r.tagLine} play={r.playLine} compact />
                )}
              </div>
            </div>

            <div className="mt-3 -mx-1 overflow-x-auto px-1">
              <div className="grid min-w-[280px] grid-cols-2 gap-2.5">
                <div
                  className={`rounded-xl border border-white/10 p-2.5 ${COL_MARKET}`}
                >
                  <div className="text-[10px] uppercase tracking-wide text-gray-500">
                    Current
                  </div>
                  <div className="mt-1.5 font-semibold text-gray-50">
                    {r.bestLine.top.label}{" "}
                    <span className="text-[11px] font-normal text-gray-400">
                      ({r.bestLine.top.juice})
                    </span>
                  </div>
                  <div className="mt-1.5 font-semibold text-gray-50">
                    {r.bestOU.top.label}{" "}
                    <span className="text-[11px] font-normal text-gray-400">
                      ({r.bestOU.top.juice})
                    </span>
                  </div>
                  <div className="mt-2 text-[10px] text-gray-500">
                    Open {r.openLine.top.label} / {r.openOU.top.label}
                  </div>
                  {r.bestLineTrustLabel === "untrusted" ||
                  r.bestLineTrustLabel === "no book" ? (
                    <div className="mt-2 text-[10px] text-gray-400">
                      {r.bestLineTrustLabel}
                    </div>
                  ) : null}
                  {r.bestLineBook === "untrusted" ||
                  r.bestLineBook === "no book" ? (
                    <div className="mt-2 text-[10px] text-gray-400">
                      {r.bestLineBook}
                    </div>
                  ) : r.bestLineBook ? (
                    <div className="mt-2">
                      <SportsbookBadge book={r.bestLineBook} compact />
                    </div>
                  ) : null}
                </div>
                <div
                  className={`rounded-xl border border-kos-gold/25 p-2.5 ${COL_KEI}`}
                >
                  <div className="text-[10px] uppercase tracking-wide text-kos-gold/80">
                    KEI · {keiCode}
                  </div>
                  <div className="mt-1.5 font-semibold text-kos-gold">
                    {(r.keiLine ?? EMPTY_PAIR).top.label}
                  </div>
                  <div className="mt-1.5 font-semibold text-kos-gold">
                    {(r.keiOU ?? EMPTY_PAIR).top.label}
                  </div>
                  {r.modelLine || r.modelOU ? (
                    <div className="mt-2 text-[10px] leading-snug text-gray-400">
                      Model {r.modelLine ? r.modelLine.top.label : "—"} /{" "}
                      {r.modelOU ? r.modelOU.top.label : "—"}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-3">
              <div
                className={`rounded-xl border border-white/10 px-3 py-2.5 ${edgeCellClass(r.tagLine)}`}
              >
                <div className="text-[10px] uppercase text-gray-500">
                  {edgeLineLabel}
                </div>
                <EdgeSideCell
                  edgeNum={r.edgeLineNum}
                  favor={r.edgeLineFavor}
                  tag={r.tagLine}
                />
              </div>
              <div
                className={`rounded-xl border border-white/10 px-3 py-2.5 ${edgeCellClass(r.tagOU)}`}
              >
                <div className="text-[10px] uppercase text-gray-500">
                  Total edge
                </div>
                <EdgeSideCell
                  edgeNum={r.edgeOUNum}
                  favor={r.edgeOUFavor}
                  tag={r.tagOU}
                />
                <div className="mt-1">
                  {isNfl ? (
                    <ActionDecisionCell
                      actionLabel={r.actionLabelOU}
                      publishTag={r.tagOU}
                      play={r.playOU}
                      playToNotes={r.playToOU}
                      playToNum={r.playToOUNum}
                      leanToNum={r.leanToOUNum}
                      fairKei={r.fairOUKei}
                      marketCurrent={r.marketOUCurrent}
                      edgeMagnitude={r.edgeMagnitudeOU}
                      confidenceBand={r.modelConfidenceBand}
                      confidenceScore={r.modelConfidenceScore}
                      confidenceTierConstant={r.modelConfidenceTierConstant}
                      coverProb={r.coverProbOU}
                      compact
                      caution={r.edgeOUCaution}
                    />
                  ) : (
                    <TagPlayCell
                      tag={r.tagOU}
                      play={r.playOU}
                      compact
                      caution={r.edgeOUCaution}
                    />
                  )}
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-end gap-2">
              <button
                type="button"
                onClick={() => toggleExpand(r.id, "overview")}
                aria-expanded={overviewOpen}
                className="min-h-11 min-w-[7.5rem] rounded-xl border border-white/12 bg-white/5 px-3 text-xs font-semibold text-kos-gold hover:border-kos-gold/40"
              >
                {overviewOpen ? "Overview ▴" : "Overview ▾"}
              </button>
              <button
                type="button"
                onClick={() => toggleExpand(r.id, "stats")}
                aria-expanded={statsOpen}
                className="min-h-11 min-w-[7.5rem] rounded-xl border border-white/12 bg-white/5 px-3 text-xs font-semibold text-kos-gold hover:border-kos-gold/40"
              >
                {statsOpen ? "Stats ▴" : "Stats ▾"}
              </button>
            </div>

            {overviewOpen ? (
              <div className="mt-3 rounded-lg border border-white/10 bg-black/60 p-3.5 text-[11px] leading-relaxed whitespace-pre-wrap text-gray-300">
                {r.siteLabel ? (
                  <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-amber-200/90">
                    {r.siteLabel}
                  </div>
                ) : null}
                {r.overview ?? "No overview available."}
              </div>
            ) : null}
            {statsOpen ? (
              <div className="mt-3 rounded-lg border border-white/10 bg-black/70 p-3">
                {r.statDrop ? (
                  <EdgeBoardStatDrop drop={r.statDrop} />
                ) : (
                  <div className="text-xs text-gray-500">
                    Stat Drop unavailable.
                  </div>
                )}
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );

  const DesktopTable = (
    <div className="hidden lg:block mt-4">
      {marketsOnly ? (
        <div className="mb-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100/90">
          <span className="font-semibold text-amber-200">Markets only.</span>{" "}
          {keiCode} handicap is not shipped for this sport yet — KEI / Edge /
          Tag stay blank. We do not invent handicap numbers.
          {String(sportKey).toLowerCase() === "cfb"
            ? " Live books only — not KEI. Project Game is MODEL research, not an Edge Board line."
            : ""}
        </div>
      ) : null}
      <div className="bg-black/30 border border-white/12 rounded-2xl backdrop-blur-xl shadow-xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div className="text-sm text-gray-300">
            {marketsOnly
              ? `Live books • Open + Current + juice · ${keiCode} pending model`
              : `Live books • Open + Current + juice • Edge vs ${keiCode}`}
          </div>
          <div className="text-xs text-gray-500 text-right">
            <div>
              {safeRows.length
                ? `${new Set(safeRows.map((r) => r?.game).filter(Boolean)).size} games`
                : "Waiting for slate"}
            </div>
            <div className="mt-0.5 text-[10px] text-gray-600">
              Current refreshes every 6h · Open is first capture
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-[1280px] w-full table-fixed text-[13px] tabular-nums">
            <colgroup>
              {COL_WIDTHS.map((w, i) => (
                <col key={i} style={{ width: w }} />
              ))}
            </colgroup>
            <thead className="bg-white/5 text-gray-300 uppercase tracking-wide text-[12px]">
              <tr className="text-left text-[10px] tracking-[0.14em] text-gray-500 normal-case">
                <th className={`${TH_BASE} pb-0`} colSpan={4} />
                <th
                  className={`${TH_BASE} pb-0 ${COL_MARKET} text-gray-400`}
                  colSpan={2}
                >
                  Market
                </th>
                <th
                  className={`${TH_BASE} pb-0 ${COL_KEI} text-kos-gold`}
                  colSpan={2}
                >
                  KEI
                </th>
                <th
                  className={`${TH_BASE} pb-0 ${COL_DECISION} text-gray-300`}
                  colSpan={4}
                >
                  Decision
                </th>
              </tr>
              <tr className="text-left">
                <th className={TH_BASE}>
                  <HeaderStack a="Game" />
                </th>
                <th className={TH_BASE}>
                  <HeaderStack a="Kickoff" />
                </th>
                <th className={TH_BASE}>
                  <HeaderStack a="Open" b="O/U" />
                </th>
                <th className={TH_BASE}>
                  <HeaderStack a="Open" b={lineLabel} />
                </th>
                <th className={`${TH_BASE} ${COL_MARKET} text-gray-100`}>
                  <HeaderStack a="Current" b={lineLabel} />
                </th>
                <th className={`${TH_BASE} ${COL_MARKET} text-gray-100`}>
                  <HeaderStack a="Current" b="O/U" />
                </th>
                <th className={`${TH_BASE} ${COL_KEI} text-kos-gold`}>
                  <HeaderStack a={keiLineHeader} b={lineLabel} />
                </th>
                <th className={`${TH_BASE} ${COL_KEI} text-kos-gold`}>
                  <HeaderStack a={keiOuHeader} b="O/U" />
                </th>
                <th
                  className={`${TH_BASE} ${COL_DECISION} text-[14px] font-bold text-white normal-case tracking-normal`}
                >
                  <HeaderStack a="Edge" b={isMlb ? "ML" : "Line"} />
                </th>
                <th
                  className={`${TH_BASE} text-[14px] font-bold text-white normal-case tracking-normal`}
                >
                  <HeaderStack a="Edge" b="O/U" />
                </th>
                <th
                  className={`${TH_BASE} text-center text-[14px] font-bold text-white normal-case tracking-normal`}
                >
                  <HeaderStack
                    a={isNfl ? "Action" : "Tag"}
                    b={isMlb ? "ML" : "Line"}
                  />
                </th>
                <th
                  className={`${TH_BASE} text-center text-[14px] font-bold text-white normal-case tracking-normal`}
                >
                  <HeaderStack a={isNfl ? "Action" : "Tag"} b="O/U" />
                </th>
              </tr>
            </thead>
            <tbody className="text-gray-200">
              {data.map((r) => {
                const overviewOpen =
                  expanded?.id === r.id && expanded.panel === "overview";
                const statsOpen =
                  expanded?.id === r.id && expanded.panel === "stats";
                const panelOpen = overviewOpen || statsOpen;
                return (
                  <React.Fragment key={r.id}>
                    <tr
                      className={`border-t border-white/[0.14] hover:bg-white/[0.035] transition ${
                        panelOpen ? "bg-white/[0.02]" : ""
                      }`}
                    >
                      <td className={TD_GAME}>
                        <div className="font-semibold leading-snug">
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
                        <div className="mt-0.5 text-xs text-gray-400 leading-relaxed">
                          {r.isNeutral ? "Away" : r.teamA.site}
                          {r.teamA.record ? ` • ${r.teamA.record}` : ""}
                          {r.teamA.confRecord ? ` (${r.teamA.confRecord})` : ""}
                        </div>
                        <div className="mt-2.5 font-semibold leading-snug">
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
                        <div className="mt-0.5 text-xs text-gray-400 leading-relaxed">
                          {r.isNeutral
                            ? r.siteLabel || "Neutral"
                            : r.teamB.site}
                          {r.teamB.record ? ` • ${r.teamB.record}` : ""}
                          {r.teamB.confRecord ? ` (${r.teamB.confRecord})` : ""}
                        </div>
                        <button
                          type="button"
                          onClick={() => toggleExpand(r.id, "overview")}
                          aria-expanded={overviewOpen}
                          className={`${ROW_CTRL_BTN} left-3 px-2`}
                        >
                          {overviewOpen ? "Overview ▴" : "Overview ▾"}
                        </button>
                      </td>
                      <td className={TD_KICKOFF}>
                        <KickoffStack
                          kickoffDate={r.kickoffDate}
                          kickoffTime={r.kickoffTime}
                          time={r.time}
                        />
                        {r.linesStale && r.linesAsOf ? (
                          <div className="mt-1 text-[10px] text-amber-300/80">
                            as of{" "}
                            {new Date(r.linesAsOf).toLocaleString("en-US", {
                              month: "2-digit",
                              day: "2-digit",
                              hour: "numeric",
                              minute: "2-digit",
                            })}
                          </div>
                        ) : null}
                        <button
                          type="button"
                          onClick={() => toggleExpand(r.id, "stats")}
                          aria-expanded={statsOpen}
                          className={`${ROW_CTRL_BTN} inset-x-1 px-1 text-center`}
                        >
                          {statsOpen ? "Stats ▴" : "Stats ▾"}
                        </button>
                      </td>
                      <td className={`${TD_BASE} text-gray-400`}>
                        <PriceCell
                          p={r.openOU}
                          compact
                          valueClassName="text-gray-400 font-medium"
                        />
                      </td>
                      <td className={`${TD_BASE} text-gray-400`}>
                        <PriceCell
                          p={r.openLine}
                          compact
                          valueClassName="text-gray-400 font-medium"
                        />
                      </td>
                      <td className={`${TD_BASE} ${COL_MARKET}`}>
                        <PriceCell
                          p={r.bestLine}
                          compact
                          valueClassName="text-gray-50 font-semibold"
                          book={r.bestLineBook}
                          trustLabel={r.bestLineTrustLabel}
                        />
                      </td>
                      <td className={`${TD_BASE} ${COL_MARKET}`}>
                        <PriceCell
                          p={r.bestOU}
                          compact
                          valueClassName="text-gray-50 font-semibold"
                          book={r.bestOUBook}
                        />
                      </td>
                      <td className={`${TD_DECISION} ${COL_MODEL}`}>
                        <PriceCell
                          p={r.keiLine ?? EMPTY_PAIR}
                          compact
                          valueClassName="text-kos-gold font-semibold"
                        />
                        {r.modelLine ? (
                          <div className="mt-1 text-[10px] text-gray-400">
                            Model {r.modelLine.bottom.label}
                          </div>
                        ) : null}
                      </td>
                      <td className={`${TD_DECISION} ${COL_MODEL}`}>
                        <PriceCell
                          p={r.keiOU ?? EMPTY_PAIR}
                          compact
                          valueClassName="text-kos-gold font-semibold"
                        />
                        {r.modelOU ? (
                          <div className="mt-1 text-[10px] text-gray-400">
                            Model {r.modelOU.top.label}
                          </div>
                        ) : null}
                      </td>
                      <td
                        className={`${TD_DECISION} ${COL_DECISION} ${edgeCellClass(r.tagLine)}`}
                      >
                        <EdgeSideCell
                          edgeNum={r.edgeLineNum}
                          favor={r.edgeLineFavor}
                          tag={r.tagLine}
                        />
                      </td>
                      <td
                        className={`${TD_DECISION} ${edgeCellClass(r.tagOU)}`}
                      >
                        <EdgeSideCell
                          edgeNum={r.edgeOUNum}
                          favor={r.edgeOUFavor}
                          tag={r.tagOU}
                        />
                      </td>
                      <td className={`${TD_DECISION} text-center`}>
                        {isNfl ? (
                          <ActionDecisionCell
                            actionLabel={r.actionLabelLine}
                            publishTag={r.tagLine}
                            play={r.playLine}
                            playToNotes={r.playToLine}
                            playToNum={r.playToLineNum}
                            leanToNum={r.leanToLineNum}
                            fairKei={r.fairLineKei}
                            marketCurrent={r.marketLineCurrent}
                            edgeMagnitude={r.edgeMagnitudeLine}
                            confidenceBand={r.modelConfidenceBand}
                            confidenceScore={r.modelConfidenceScore}
                            confidenceTierConstant={
                              r.modelConfidenceTierConstant
                            }
                            coverProb={r.coverProbLine}
                          />
                        ) : (
                          <TagPlayCell tag={r.tagLine} play={r.playLine} />
                        )}
                      </td>
                      <td className={`${TD_DECISION} text-center`}>
                        {isNfl ? (
                          <ActionDecisionCell
                            actionLabel={r.actionLabelOU}
                            publishTag={r.tagOU}
                            play={r.playOU}
                            playToNotes={r.playToOU}
                            playToNum={r.playToOUNum}
                            leanToNum={r.leanToOUNum}
                            fairKei={r.fairOUKei}
                            marketCurrent={r.marketOUCurrent}
                            edgeMagnitude={r.edgeMagnitudeOU}
                            confidenceBand={r.modelConfidenceBand}
                            confidenceScore={r.modelConfidenceScore}
                            confidenceTierConstant={
                              r.modelConfidenceTierConstant
                            }
                            coverProb={r.coverProbOU}
                            caution={r.edgeOUCaution}
                          />
                        ) : (
                          <TagPlayCell
                            tag={r.tagOU}
                            play={r.playOU}
                            caution={r.edgeOUCaution}
                          />
                        )}
                      </td>
                    </tr>
                    {panelOpen ? (
                      <tr className="border-t border-white/[0.06] bg-black/55">
                        <td colSpan={12} className="px-4 py-3.5">
                          {overviewOpen ? (
                            <div className="rounded-xl border border-white/12 bg-black/70 p-3.5 text-xs text-gray-300 leading-relaxed whitespace-pre-wrap">
                              {r.siteLabel ? (
                                <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-amber-200/90">
                                  {r.siteLabel}
                                </div>
                              ) : null}
                              {r.overview ?? "No overview available."}
                            </div>
                          ) : null}
                          {statsOpen ? (
                            <div className="rounded-xl border border-white/12 bg-black/70 p-3.5">
                              {r.statDrop ? (
                                <EdgeBoardStatDrop drop={r.statDrop} />
                              ) : (
                                <div className="text-xs text-gray-500">
                                  Stat Drop unavailable.
                                </div>
                              )}
                            </div>
                          ) : null}
                        </td>
                      </tr>
                    ) : null}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-3.5 text-[10px] text-gray-400 border-t border-white/10">
          {marketsOnly
            ? `Markets-only board — ${keiCode} handicap model not shipped. KEI / Edge / Tag stay empty (no invented numbers). Open/Best from sportsbooks or shipped fallback snapshots.`
            : isNfl
              ? "We bet prices, not teams. Action = KEI vs Current (stakeable book when present). Edge magnitude and confidence stay separate. "
              : isMlb
                ? "MLB tags — ML PASS / LEAN (≥1.5pp) / PLAY (≥3.0pp) vs no-vig market. Totals keep run-point LEAN ≥1.0 / PLAY ≥2.5. "
                : String(sportKey).toLowerCase() === "cfb"
                  ? "CFB tags — PASS default · LEAN ≥2.5 · PLAY ≥4.0 vs trusted Best only. Current paints the feed; untrusted / no book is a footnote — never invent Open. "
                  : "Tags — PASS / LEAN (≥1) / PLAY (≥2.5). "}
          {!marketsOnly &&
            (isMlb
              ? "ML edge is KEI handicap win-prob minus market no-vig (percentage points). "
              : isNfl
                ? `${keiCode} Edge column and Action use the same market input. Open is first capture — never copied from Current. `
                : String(sportKey).toLowerCase() === "cfb"
                  ? "Open/Best from The Odds API (americanfootball_ncaaf) or — when empty. Never invented. "
                  : "Edge shows pts + side favored vs KEI handicap. ")}
          {!marketsOnly
            ? isNfl
              ? "Methods → Model transparency."
              : `Tag shows the action at the best book. ${keiCode}: Kos Edge Index (handicap).`
            : null}
        </div>
      </div>
    </div>
  );

  // Empty state for full variant when no real data (avoids misleading sample /
  // "Coming soon" placeholders). Honest offseason / upstream empty.
  if (variant === "full" && !hasRealData) {
    return (
      <div className="mt-6 rounded-2xl border border-white/10 bg-black/30 backdrop-blur-xl p-8 sm:p-12 text-center">
        <div className="text-kos-gold text-2xl font-bebas tracking-wide mb-2">
          No Slate Yet
        </div>
        <p className="text-gray-400 text-sm max-w-md mx-auto">
          {emptyHint
            ? emptyHint
            : isNfl
              ? "No regular-season fair-lines in the pull window yet (common in early preseason or upstream timeout). We do not invent Open/Best or KEINFL prices, and we do not fill the board with preseason odds-only games."
              : "No fair-lines or sportsbook rows for this sport right now (often offseason or upstream timeout). We do not invent Open/Best or KEI prices. When the model service or Odds API returns a slate, this board populates automatically."}
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
