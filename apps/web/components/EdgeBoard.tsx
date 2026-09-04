"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import SportsbookBadge from "@/components/SportsbookBadge";
import { sportIsMarketsOnlyEdgeBoard } from "@/lib/edge-board-kei-availability";
import { getKeiCode } from "@/lib/kei-brand";
import type { ActionLabel, ConfidenceBand } from "@/lib/nfl-decision-engine";
import {
  displayActionLabel,
  reachableActionLabels,
  reachableConfidenceBands,
} from "@/lib/nfl-dead-tiers";
import EdgeBoardStatDrop from "@/components/EdgeBoardStatDrop";
import type { StatDrop } from "@/lib/edge-board-stat-drop";
import { buildHomePreviewRows } from "@/lib/edge-board-home-preview";

/** Board revalidate cadence — matches Odds API cache TTL on /api/edge-board. */
const EDGE_BOARD_REFRESH_MS = 6 * 60 * 60 * 1000;
/** Stale if last odds capture older than this (same policy as refresh). */

type ExpandPanel = "overview" | "stats" | null;

// Flat API row format (from Odds API / model); kei = our projected line/total/ML
export type {
  FlatEdgeBoardRow,
  EdgeBoardRow,
  PriceSide,
  PricePair,
  TeamBlock,
  LegacyEdgeBoardRow,
} from "@/lib/flat-rows-to-legacy";
import {
  flatRowsToLegacy,
  type FlatEdgeBoardRow,
  type LegacyEdgeBoardRow,
  type PricePair,
  type Tag,
} from "@/lib/flat-rows-to-legacy";
export type { Tag } from "@/lib/flat-rows-to-legacy";
// Do NOT re-export flatRowsToLegacy from this client module — RSC edges/slate
// paths must import the server-safe lib directly (historical hydrate crash).

type Variant = "home" | "full";

const EMPTY_PAIR: PricePair = {
  top: { label: "—", juice: "—" },
  bottom: { label: "—", juice: "—" },
};

/**
 * Homepage eye-catcher — stamped CFB Week 1 chrome; tags via `cfbEdgeTag`
 * (sit-aware). Do not hardcode PLAY. Full live board stays off the hero.
 */
const homePreviewRows = buildHomePreviewRows();

/** Short team label for dense board cells (last word of full name). */

function tagClassName(tag: Tag, compact = false): string {
  const base = compact
    ? "inline-flex px-2.5 py-1 rounded-md text-[12px] font-bold tracking-wide"
    : "inline-flex items-center justify-center min-w-[3.5rem] px-2.5 py-1.5 rounded-md text-[13px] font-bold tracking-wide";
  if (tag === "PLAY") return `${base} bg-edge-green text-black`;
  if (tag === "LEAN") return `${base} bg-amber-500 text-black`;
  return `${base} bg-white/10 text-gray-400`;
}

/** Product surfaces: PLAY / LEAN / PASS only (no Best Bet / BEST VALUE chrome). */
type PublishActionLabel = "PLAY" | "LEAN" | "PASS";

function toPublishActionLabel(
  label: ActionLabel | null | undefined,
): PublishActionLabel | null {
  const shown = displayActionLabel(label);
  if (shown === "PLAY" || shown === "LEAN" || shown === "PASS") return shown;
  // Defensive: unreachable / legacy ActionLabel leftovers never paint.
  if (shown == null) return null;
  return "PASS";
}

function actionLabelClassName(
  label: PublishActionLabel,
  compact = false,
): string {
  const base = compact
    ? "inline-flex px-2 py-0.5 rounded-md text-[11px] font-bold tracking-wide"
    : "inline-flex items-center justify-center px-2 py-1 rounded-md text-[12px] font-bold tracking-wide";
  if (label === "PLAY") return `${base} bg-edge-green text-black`;
  if (label === "LEAN") return `${base} bg-amber-500 text-black`;
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
  const shownLabel =
    publishTag === "PLAY" || publishTag === "LEAN" || publishTag === "PASS"
      ? publishTag
      : toPublishActionLabel(actionLabel);
  const confLabel = formatConfidenceLabel(
    confidenceBand,
    confidenceScore,
    confidenceTierConstant,
  );
  const showLadder = shownLabel === "PLAY" || shownLabel === "LEAN";
  const ladderVerb = shownLabel === "LEAN" ? "Lean to" : "Play to";
  const ladderNum =
    shownLabel === "LEAN" && leanToNum != null
      ? leanToNum
      : playToNum != null
        ? playToNum
        : null;
  return (
    <div className={compact ? "leading-tight" : "leading-tight text-center"}>
      {shownLabel ? (
        <span className={actionLabelClassName(shownLabel, compact)}>
          {shownLabel}
        </span>
      ) : publishTag ? (
        <span className={tagClassName(publishTag, compact)}>{publishTag}</span>
      ) : null}
      {play && shownLabel && shownLabel !== "PASS" ? (
        <div
          className={`mt-1 text-[11px] font-bold truncate ${
            shownLabel === "PLAY"
              ? "text-edge-green"
              : shownLabel === "LEAN"
                ? "text-amber-400"
                : "text-gray-400"
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
      {caution && shownLabel && shownLabel !== "PASS" ? (
        <div className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-amber-300/90">
          Size down
        </div>
      ) : null}
      {publishTag && shownLabel && publishTag !== shownLabel ? (
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

/** Oversized total edges: still PLAY when ≥2.5, but stake down when ≥3.0. */

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
    : [];
  const data = hasRealData ? legacy : [];
  const isNfl = String(sportKey).toLowerCase() === "nfl";
  const isMlb = String(sportKey).toLowerCase() === "mlb";
  const marketsOnly = sportIsMarketsOnlyEdgeBoard(sportKey);
  const lineLabel = isMlb ? "Moneyline" : "Line";
  // KEI = final handicap when a model exists. Markets-only sports leave cells "—".
  const keiLineHeader = "KEI";
  const keiOuHeader = "KEI";
  const edgeLineLabel = isMlb ? "ML edge" : "Spread edge";

  if (variant === "home") {
    // Compact-but-readable pills — must stay inside Tag track (wider than "—").
    const homeTagClass = (tag: Tag) => {
      const base =
        "inline-flex px-2.5 py-0.5 rounded-md text-xs font-bold tracking-wide";
      if (tag === "PLAY") return `${base} bg-edge-green text-black`;
      if (tag === "LEAN") return `${base} bg-amber-500 text-black`;
      return `${base} bg-white/10 text-gray-400`;
    };
    // CSS grid (not <table>) so fr tracks honor minmax(0,…) and Tag never
    // spills past the card — table-fixed still let cell content paint outside.
    // Tag track a bit wider so text-xs PLAY/PASS keep a few px inside the border.
    const homeGrid =
      "grid w-full grid-cols-[minmax(0,1.25fr)_minmax(0,0.9fr)_minmax(0,0.7fr)_minmax(0,0.55fr)_minmax(0,0.85fr)] gap-x-2 text-[15px]";
    return (
      <div className="lg:col-span-5 self-start min-w-0">
        {/*
          Padding keeps the absolute gold/green glow inside the layout box so
          the hero row grows with the taller 3-row card and nothing bleeds onto
          the lower section. Do not overflow-hide the board chrome.
        */}
        <div className="relative p-3 sm:p-4 min-w-0">
          <div className="pointer-events-none absolute inset-0 rounded-3xl bg-linear-to-r from-kos-gold/25 via-kos-green/15 to-kos-gold/25 blur-2xl opacity-80" />
          <div className="relative bg-black/40 border border-white/12 rounded-3xl p-5 sm:p-6 backdrop-blur-xl shadow-2xl min-w-0">
            <div className="mb-5">
              <h2 className="text-3xl font-bebas text-edge-green">
                Edge Board
              </h2>
            </div>
            <div className="rounded-2xl border border-white/10 min-w-0">
              <div className={`${homeGrid} bg-white/5 text-left text-gray-300`}>
                <div className="py-3 pl-3 pr-1.5 font-medium">Game</div>
                <div className="py-3 px-1.5 font-medium">Best Line</div>
                <div className="py-3 px-1.5 font-medium">Best O/U</div>
                <div className="py-3 px-1.5 font-medium">Edge</div>
                <div className="py-3 pl-1.5 pr-3 font-medium">Tag</div>
              </div>
              <div className="divide-y divide-white/10 text-gray-200">
                {homePreviewRows.map((r) => (
                  <div
                    key={r.id}
                    className={`${homeGrid} hover:bg-white/5 transition`}
                  >
                    <div className="py-3.5 pl-3 pr-1.5 font-semibold leading-snug break-words">
                      {r.teamA.name} @ {r.teamB.name}
                    </div>
                    <div className="py-3.5 px-1.5 font-semibold leading-snug">
                      {r.bestLine.top.label}
                    </div>
                    <div className="py-3.5 px-1.5 font-semibold leading-snug">
                      {r.bestOU.top.label}
                    </div>
                    <div className="py-3.5 px-1.5 font-bold tabular-nums">
                      {r.edgeLineNum != null ? r.edgeLineNum.toFixed(1) : "—"}
                    </div>
                    <div className="py-3.5 pl-1.5 pr-3 min-w-0">
                      {r.tagLine ? (
                        <span className={homeTagClass(r.tagLine)}>
                          {r.tagLine}
                        </span>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
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
                {r.linesAsOf ? (
                  <p
                    className={`mt-1 text-[10px] ${
                      r.linesStale ? "text-amber-300/80" : "text-gray-500"
                    }`}
                  >
                    Lines as of{" "}
                    {new Date(r.linesAsOf).toLocaleString("en-US", {
                      month: "2-digit",
                      day: "2-digit",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                    {r.linesStale ? " · stale" : ""}
                  </p>
                ) : isNfl ? (
                  <p className="mt-1 text-[10px] text-amber-200/80">
                    Market as-of unavailable
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
                  {r.bestOUTrustLabel === "untrusted" ||
                  r.bestOUTrustLabel === "no book" ? (
                    <div className="mt-2 text-[10px] text-gray-400">
                      O/U {r.bestOUTrustLabel}
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
                        {r.linesAsOf ? (
                          <div
                            className={`mt-1 text-[10px] ${
                              r.linesStale
                                ? "text-amber-300/80"
                                : "text-gray-500"
                            }`}
                          >
                            as of{" "}
                            {new Date(r.linesAsOf).toLocaleString("en-US", {
                              month: "2-digit",
                              day: "2-digit",
                              hour: "numeric",
                              minute: "2-digit",
                            })}
                            {r.linesStale ? " · stale" : ""}
                          </div>
                        ) : isNfl ? (
                          <div className="mt-1 text-[10px] text-amber-200/80">
                            Market as-of unavailable
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
                          trustLabel={r.bestOUTrustLabel}
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
              ? `We bet prices, not teams. Action = KEI vs Current (stakeable book when present). Labels: ${reachableActionLabels().join(" / ")}. Confidence bands: ${reachableConfidenceBands().join(" / ")}. Edge magnitude and confidence stay separate. `
              : isMlb
                ? "MLB tags — ML PASS / LEAN (≥1.5pp) / PLAY (≥3.0pp) vs no-vig market. Totals keep run-point LEAN ≥1.0 / PLAY ≥2.5. "
                : String(sportKey).toLowerCase() === "cfb"
                  ? "CFB research board — tags paint only when assemble publishes PLAY/LEAN/PASS (never invented from edge). Current paints the feed; untrusted / no book is a footnote — never invent Open. "
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
