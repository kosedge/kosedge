"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import EdgeBoard, { type EdgeBoardRow } from "@/components/EdgeBoard";
import { MarketAsOfStamp } from "@/components/pro/MarketAsOfStamp";
import { TruthStateBadges } from "@/components/pro/TruthStateBadge";
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
  displayHonesty?: {
    nfl_game_confidence_band_display?: "on" | "off";
    display_suppression_note?: string | null;
    suppressGameConfidenceBand?: boolean;
  };
};

type Props = {
  sportKey: string;
  sportName: string;
  slate: "week1" | "full";
  cfbWeek: 0 | 1;
};

/**
 * Client-fetched Edge Board body.
 * Document HTML is not blocked on model-service / Odds (Alex waterfall fix).
 * As-of stamps (PR 416) fill after assemble returns.
 */
export default function EdgeBoardSportClient({
  sportKey,
  sportName,
  slate,
  cfbWeek,
}: Props) {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; data: AssemblePayload }
    | { status: "error" }
  >({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
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
        setState({
          status: "ready",
          data: {
            rows: Array.isArray(data.rows) ? data.rows : [],
            week0Count: data.week0Count ?? 0,
            week1Count: data.week1Count ?? 0,
            fullCount: data.fullCount ?? 0,
            weeks: Array.isArray(data.weeks) ? data.weeks : [],
            linesAsOf: data.linesAsOf ?? null,
            games: data.games ?? 0,
            displayHonesty: data.displayHonesty,
          },
        });
      } catch {
        if (cancelled || controller.signal.aborted) return;
        setState({ status: "error" });
      }
    }

    void load();
    return () => {
      cancelled = true;
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
  const nflLinesAsOf = state.status === "ready" ? state.data.linesAsOf : null;
  const suppressGameConfidenceBand =
    state.status === "ready"
      ? Boolean(state.data.displayHonesty?.suppressGameConfidenceBand)
      : false;
  const displayHonestyNote =
    state.status === "ready"
      ? (state.data.displayHonesty?.display_suppression_note ?? null)
      : null;
  const headerAsOf = isNfl
    ? state.status === "loading"
      ? "…"
      : marketAsOfHeaderSuffix({ asOf: nflLinesAsOf, kind: "lines" })
    : null;

  return (
    <div data-testid="edge-board-client">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
        <div>
          <div className="text-sm text-gray-400">
            {sportName} ·{" "}
            {marketsOnly
              ? "Markets only"
              : `KEI vs Market · ${getKeiProductLabel(sportKey)}`}
            {isNfl ? <> · {headerAsOf}</> : <> · ET</>}
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
            Week {cfbWeek} · Tag = KEI vs trusted market · Model is
            research-only ·{" "}
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

      {isNfl && state.status === "ready" ? (
        <MarketAsOfStamp
          className="mt-3"
          asOf={nflLinesAsOf}
          kind="lines"
          data-testid="edge-board-asof"
        />
      ) : null}

      {displayHonestyNote && suppressGameConfidenceBand ? (
        <p
          className="mt-3 text-xs text-kos-text/60"
          data-testid="display-honesty-note"
        >
          {displayHonestyNote}
        </p>
      ) : null}

      {state.status === "loading" ? (
        <div
          className="mt-6 rounded-2xl border border-white/12 bg-black/30 p-12 text-center text-gray-400"
          data-testid="edge-board-loading"
        >
          Loading board…
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="mt-6 rounded-2xl border border-white/12 bg-black/30 p-12 text-center text-gray-400">
          Board temporarily unavailable. Refresh to try again.
        </div>
      ) : null}

      {state.status === "ready" ? (
        <>
          <EdgeBoard
            variant="full"
            rows={rows}
            sportKey={sportKey}
            slateWeek={slate === "week1" ? 1 : (nflWeeks[0] ?? null)}
            suppressGameConfidenceBand={suppressGameConfidenceBand}
            emptyHint={
              isNfl && slate === "week1"
                ? "No Week 1 REG schedule games resolved. We do not fall through to later weeks or the full slate. Switch to Full slate for the multi-week board."
                : sportKey === "cfb"
                  ? "KEI rows load from the bundled W0/W1 pack. Open/Best stay empty until The Odds API returns NCAAF — we do not invent book prices."
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
