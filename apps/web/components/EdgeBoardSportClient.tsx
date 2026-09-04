"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import EdgeBoard, { type EdgeBoardRow } from "@/components/EdgeBoard";
import { MarketAsOfStamp } from "@/components/pro/MarketAsOfStamp";
import { TruthStateBadges } from "@/components/pro/TruthStateBadge";
import {
  EDGE_BOARD_ASSEMBLE_HONESTY_MS,
  edgeBoardAssembleHonestyCopy,
  recallEdgeBoardLinesAsOf,
  rememberEdgeBoardLinesAsOf,
  type EdgeBoardAssembleHonestyReason,
} from "@/lib/edge-board-assemble-honesty";
import { sportIsMarketsOnlyEdgeBoard } from "@/lib/edge-board-kei-availability";
import { getKeiCode, getKeiProductLabel } from "@/lib/kei-brand";
import { marketAsOfHeaderSuffix } from "@/lib/market-asof-stamp";
import { MODEL_TRANSPARENCY_HREF } from "@/lib/model-transparency-hub";
import { getSportOverviewHref } from "@/lib/sport-pro-nav";
import { SPORTS } from "@/lib/sports";

type AssemblePayload = {
  rows: EdgeBoardRow[];
  week0Count: number;
  week1Count: number;
  fullCount: number;
  weeks: number[];
  linesAsOf: string | null;
  games: number;
  error?: string;
};

type Props = {
  sportKey: string;
  sportName: string;
  slate: "week1" | "full";
  cfbWeek: 0 | 1;
};

type ClientState =
  | { status: "loading" }
  | {
      status: "slow";
      /** Last good as-of when known — never invent rows while waiting. */
      lastLinesAsOf: string | null;
    }
  | { status: "ready"; data: AssemblePayload }
  | {
      status: "error";
      reason: EdgeBoardAssembleHonestyReason;
      /** Last good as-of when known — never invent rows. */
      lastLinesAsOf: string | null;
    };

/**
 * Client-fetched Edge Board body.
 * Document HTML is not blocked on model-service / Odds (Alex waterfall fix).
 * As-of stamps (PR 416) fill after assemble returns.
 * Honesty: past EDGE_BOARD_ASSEMBLE_HONESTY_MS escalate copy (keep fetch; no invent).
 */
export default function EdgeBoardSportClient({
  sportKey,
  sportName,
  slate,
  cfbWeek,
}: Props) {
  const [state, setState] = useState<ClientState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const honestyTimer = setTimeout(() => {
      if (cancelled) return;
      setState((prev) =>
        prev.status === "loading"
          ? {
              status: "slow",
              lastLinesAsOf: recallEdgeBoardLinesAsOf(sportKey),
            }
          : prev,
      );
    }, EDGE_BOARD_ASSEMBLE_HONESTY_MS);

    const qs = new URLSearchParams();
    if (sportKey === "nfl") qs.set("slate", slate);
    if (sportKey === "cfb") qs.set("week", String(cfbWeek));
    const q = qs.toString();

    async function load() {
      setState({ status: "loading" });
      try {
        const res = await fetch(
          `/api/edge-board/${sportKey}/assemble${q ? `?${q}` : ""}`,
          {
            cache: "no-store",
            headers: { accept: "application/json" },
            signal: controller.signal,
          },
        );
        if (!res.ok) throw new Error(`assemble ${res.status}`);
        const data = (await res.json()) as AssemblePayload;
        if (cancelled) return;
        const linesAsOf = data.linesAsOf ?? null;
        rememberEdgeBoardLinesAsOf(sportKey, linesAsOf);
        setState({
          status: "ready",
          data: {
            rows: Array.isArray(data.rows) ? data.rows : [],
            week0Count: data.week0Count ?? 0,
            week1Count: data.week1Count ?? 0,
            fullCount: data.fullCount ?? 0,
            weeks: Array.isArray(data.weeks) ? data.weeks : [],
            linesAsOf,
            games: data.games ?? 0,
          },
        });
      } catch {
        if (cancelled || controller.signal.aborted) return;
        const lastLinesAsOf = recallEdgeBoardLinesAsOf(sportKey);
        setState({
          status: "error",
          reason: "unavailable",
          lastLinesAsOf,
        });
      }
    }

    void load();
    return () => {
      cancelled = true;
      clearTimeout(honestyTimer);
      controller.abort();
    };
  }, [sportKey, slate, cfbWeek]);

  const isNfl = sportKey === "nfl";
  const marketsOnly = sportIsMarketsOnlyEdgeBoard(sportKey);
  const keiCode = getKeiCode(sportKey);
  const slateLabel =
    sportKey === "nfl" || sportKey === "cfb" ? "Weekly Slate" : "Daily Slate";

  const rows = state.status === "ready" ? state.data.rows : [];
  const week0Count = state.status === "ready" ? state.data.week0Count : 0;
  const week1Count = state.status === "ready" ? state.data.week1Count : 0;
  const fullCount = state.status === "ready" ? state.data.fullCount : 0;
  const games = state.status === "ready" ? state.data.games : 0;
  const nflWeeks = state.status === "ready" ? state.data.weeks : [];
  const boardLinesAsOf =
    state.status === "ready"
      ? state.data.linesAsOf
      : state.status === "error" || state.status === "slow"
        ? state.lastLinesAsOf
        : null;
  // Always stamp from assemble linesAsOf (or last good) — never invent "as of now".
  const headerAsOf =
    state.status === "loading"
      ? "…"
      : marketAsOfHeaderSuffix({ asOf: boardLinesAsOf, kind: "lines" });

  return (
    <div data-testid="edge-board-client">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
        <div>
          <div className="text-sm text-gray-400">
            {sportName} ·{" "}
            {marketsOnly
              ? "Markets only"
              : `KEI vs Market · ${getKeiProductLabel(sportKey)}`}
            <> · {headerAsOf}</>
          </div>
          {marketsOnly ? (
            <div className="mt-2">
              <TruthStateBadges
                states={["LIVE"]}
                testId={sportKey === "cfb" ? "cfb-truth-state" : "truth-state"}
              />
            </div>
          ) : null}
          <h1 className="text-3xl sm:text-5xl font-semibold tracking-tight text-edge-green">
            {sportName} Edge Board
          </h1>
          {!isNfl ? (
            <p className="mt-2 text-sm sm:text-base text-gray-200/80 max-w-3xl">
              {marketsOnly
                ? `${keiCode} handicap is not shipped — KEI stays blank (books ≠ KEI). Research board, not picks.`
                : `KEI vs market. Model is research-fair. Tags never use Model vs market.`}{" "}
              <Link
                href={MODEL_TRANSPARENCY_HREF}
                className="text-kos-gold/80 hover:text-kos-gold hover:underline"
              >
                Model transparency
              </Link>
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            href={getSportOverviewHref(sportKey)}
            className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
          >
            {sportName} Overview
          </Link>
          <Link
            href={`/pro/${sportKey}/slate/today`}
            className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
          >
            {slateLabel}
          </Link>
          <Link
            href={`/odds/${sportKey}`}
            className="min-h-11 px-4 py-2 rounded-xl bg-white/5 border border-white/12 hover:border-kos-gold/35 hover:bg-white/10 transition text-center font-semibold inline-flex items-center"
          >
            Compare Odds
          </Link>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {SPORTS.map((s) => (
          <Link
            key={s.key}
            href={`/edge-board/${s.key}`}
            className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
              s.key === sportKey
                ? "bg-edge-green/20 border border-edge-green/50 text-edge-green shadow-[0_0_16px_rgba(57,255,20,0.2)]"
                : "bg-black/30 border border-white/12 hover:border-edge-green/35 text-gray-300"
            }`}
          >
            {s.label}
          </Link>
        ))}
      </div>

      {sportKey === "cfb" ? (
        <div className="mt-3 space-y-1.5">
          <div
            className="flex flex-wrap gap-2"
            role="tablist"
            aria-label="CFB week"
          >
            <Link
              href="/edge-board/cfb?week=0"
              role="tab"
              aria-selected={cfbWeek === 0}
              className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
                cfbWeek === 0
                  ? "bg-edge-green/20 border border-edge-green/40 text-edge-green"
                  : "bg-black/30 border border-white/12 text-gray-300"
              }`}
            >
              Week 0{week0Count ? ` (${week0Count})` : ""}
            </Link>
            <Link
              href="/edge-board/cfb?week=1"
              role="tab"
              aria-selected={cfbWeek === 1}
              className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
                cfbWeek === 1
                  ? "bg-edge-green/20 border border-edge-green/40 text-edge-green"
                  : "bg-black/30 border border-white/12 text-gray-300"
              }`}
            >
              Week 1{week1Count ? ` (${week1Count})` : ""}
            </Link>
          </div>
          <p className="text-[11px] text-gray-500">
            Week {cfbWeek} · Research board · Tags only when assemble publishes
            them (never invented from edge) · Model is research-only ·{" "}
            <Link
              href={MODEL_TRANSPARENCY_HREF}
              className="text-kos-gold/80 hover:text-kos-gold hover:underline"
            >
              Model transparency
            </Link>
          </p>
        </div>
      ) : null}

      {sportKey === "nfl" ? (
        <div
          className="mt-3 flex flex-wrap gap-2"
          role="tablist"
          aria-label="NFL Edge Board slate"
        >
          <Link
            href="/edge-board/nfl?slate=week1"
            role="tab"
            aria-selected={slate === "week1"}
            className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
              slate === "week1"
                ? "bg-edge-green/20 border border-edge-green/40 text-edge-green shadow-[0_0_16px_rgba(57,255,20,0.2)]"
                : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
            }`}
          >
            Week 1{week1Count ? ` (${week1Count})` : ""}
          </Link>
          <Link
            href="/edge-board/nfl?slate=full"
            role="tab"
            aria-selected={slate === "full"}
            className={`min-h-11 rounded-xl px-4 py-2.5 text-sm font-semibold transition inline-flex items-center ${
              slate === "full"
                ? "bg-edge-green/20 border border-edge-green/40 text-edge-green shadow-[0_0_16px_rgba(57,255,20,0.2)]"
                : "bg-black/30 border border-white/12 hover:border-kos-gold/35 text-gray-300"
            }`}
          >
            Full slate{fullCount ? ` (${fullCount})` : ""}
          </Link>
        </div>
      ) : null}

      {state.status === "ready" ||
      state.status === "error" ||
      state.status === "slow" ? (
        <MarketAsOfStamp
          className="mt-3"
          asOf={boardLinesAsOf}
          kind="lines"
          data-testid="edge-board-asof"
        />
      ) : null}

      {state.status === "loading" ? (
        <div
          className="mt-6 rounded-2xl border border-white/12 bg-black/30 p-12 text-center text-gray-400"
          data-testid="edge-board-loading"
        >
          Loading board…
        </div>
      ) : null}

      {state.status === "slow" ? (
        <div
          className="mt-6 rounded-2xl border border-amber-200/25 bg-black/30 p-12 text-center text-amber-100/90"
          data-testid="edge-board-slow"
        >
          {edgeBoardAssembleHonestyCopy("timeout")}
        </div>
      ) : null}

      {state.status === "error" ? (
        <div
          className="mt-6 rounded-2xl border border-amber-200/25 bg-black/30 p-12 text-center text-amber-100/90"
          data-testid="edge-board-unavailable"
          data-reason={state.reason}
        >
          {edgeBoardAssembleHonestyCopy(state.reason)}
        </div>
      ) : null}

      {state.status === "ready" ? (
        <>
          <EdgeBoard
            variant="full"
            rows={rows}
            sportKey={sportKey}
            slateWeek={slate === "week1" ? 1 : (nflWeeks[0] ?? null)}
            emptyHint={
              isNfl && slate === "week1"
                ? "No Week 1 REG schedule games resolved. We do not fall through to later weeks or the full slate. Switch to Full slate for the multi-week board."
                : sportKey === "cfb"
                  ? "KEI vs trusted market when books clear. Tags stay blank until assemble publishes PLAY/LEAN/PASS — we do not invent tags from edge. Open/Best stay empty until The Odds API returns NCAAF."
                  : undefined
            }
          />
          <p className="mt-6 text-xs text-gray-500">
            {rows.length
              ? `${games} games${
                  sportKey === "nfl"
                    ? slate === "week1"
                      ? " · Week 1 REG"
                      : " · full slate"
                    : sportKey === "cfb"
                      ? ` · Week ${cfbWeek}${
                          rows.some((r) => r.best || r.open)
                            ? ""
                            : " · waiting on Odds API for Open/Best"
                        }`
                      : ""
                }`
              : isNfl && slate === "week1"
                ? "No Week 1 REG games yet — board stays empty (no silent full-slate fallthrough)."
                : "No slate rows yet — waiting on fair-lines / Odds (or offseason empty). Boards never invent book prices."}
          </p>
        </>
      ) : null}
    </div>
  );
}
