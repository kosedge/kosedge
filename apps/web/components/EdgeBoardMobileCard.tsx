"use client";

import type { ReactNode } from "react";
import EdgeBoardStatDrop from "@/components/EdgeBoardStatDrop";
import SportsbookBadge from "@/components/SportsbookBadge";
import type { LegacyEdgeBoardRow } from "@/lib/flat-rows-to-legacy";
import {
  KOSEDGE_FAIR_GOLD,
  KOSEDGE_FAIR_GOLD_DIM,
  composeEdgeBoardMobileCard,
  hasHeroFair,
  hasHeroMarket,
  hasInterpretation,
  hasMarketContext,
  type MobileCardModel,
  type PublishActionLabel,
} from "@/lib/edge-board-mobile-presentation";

type ExpandPanel = "overview" | "stats";

function statusClassName(label: PublishActionLabel): string {
  const base =
    "inline-flex items-center justify-center min-h-6 px-2 rounded-md text-[11px] font-bold tracking-wide";
  if (label === "PLAY") return `${base} bg-edge-green text-black`;
  if (label === "LEAN") return `${base} bg-amber-500 text-black`;
  return `${base} bg-white/10 text-gray-400`;
}

function Juice({ value }: { value: string | null }) {
  if (!value) return null;
  return (
    <span className="ml-1.5 text-[11px] font-normal text-gray-400 tabular-nums">
      {value}
    </span>
  );
}

function BookUnit({
  bookKey,
  children,
}: {
  bookKey: string | null;
  children: ReactNode;
}) {
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      {bookKey ? <SportsbookBadge book={bookKey} compact /> : null}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

function InterpRow({
  label,
  interp,
}: {
  label: string;
  interp: NonNullable<MobileCardModel["spreadInterp"]>;
}) {
  return (
    <div
      className={`flex items-center gap-2 min-h-7 ${
        interp.subdued ? "text-gray-500" : "text-gray-100"
      }`}
      data-interp={label}
      data-fail-closed={interp.failClosed ? "1" : "0"}
    >
      {interp.status ? (
        <span className={statusClassName(interp.status)}>{interp.status}</span>
      ) : null}
      {interp.sideLabel ? (
        <span className="text-[13px] font-semibold truncate">
          {interp.sideLabel}
        </span>
      ) : null}
      {interp.magnitude ? (
        <span className="text-[13px] font-semibold tabular-nums">
          {interp.magnitude}
        </span>
      ) : null}
    </div>
  );
}

export default function EdgeBoardMobileCard({
  row,
  sportKey,
  overviewOpen,
  statsOpen,
  onToggle,
}: {
  row: LegacyEdgeBoardRow;
  sportKey: string;
  overviewOpen: boolean;
  statsOpen: boolean;
  onToggle: (panel: ExpandPanel) => void;
}) {
  const model = composeEdgeBoardMobileCard({ row, sportKey });
  const showMarket = hasHeroMarket(model);
  const showFair = hasHeroFair(model);
  const showHero = showMarket || showFair;
  const showInterp = hasInterpretation(model);
  const showContext = hasMarketContext(model);

  return (
    <article
      className="rounded-2xl border border-white/14 bg-black/45 px-3.5 py-3 sm:px-4 backdrop-blur-xl"
      data-testid="edge-board-mobile-card"
      data-game-id={row.id}
    >
      {/* L1 — GAME */}
      <header className="min-w-0">
        <h3 className="text-[15px] font-semibold text-gray-100 leading-snug break-words">
          {model.matchup}
        </h3>
        {model.marketHorizonLabel ? (
          <div
            className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-kos-gold/90"
            data-testid="odds-horizon-label"
          >
            {model.marketHorizonLabel}
          </div>
        ) : null}
        {model.oddsWithoutKei ? (
          <div className="mt-0.5 text-[10px] text-gray-500">no house print</div>
        ) : null}
        {model.kickoffDate || model.kickoffTime ? (
          <div className="mt-1 leading-snug tabular-nums">
            {model.kickoffDate ? (
              <span className="text-sm font-semibold text-gray-200">
                {model.kickoffDate}
              </span>
            ) : null}
            {model.kickoffTime ? (
              <span className="ml-2 text-xs text-gray-400">
                {model.kickoffTime}
                {model.kickoffTz ? (
                  <span className="ml-1 text-[10px] uppercase tracking-wide text-gray-500">
                    {model.kickoffTz}
                  </span>
                ) : null}
              </span>
            ) : null}
          </div>
        ) : null}
        {model.venue ? (
          <p
            className={
              model.venue.kind === "neutral"
                ? "mt-1 text-[12px] font-semibold text-amber-200/90"
                : "mt-1 text-[11px] text-gray-500"
            }
            data-venue={model.venue.kind}
          >
            {model.venue.text}
          </p>
        ) : null}
      </header>

      {/* L2 — MARKET | KOSEDGE FAIR (hero) */}
      {showHero ? (
        <div
          className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1"
          data-testid="edge-board-mobile-hero"
        >
          <div className="min-w-0" data-col="market">
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white">
              Market
            </div>
            {model.isMoneyline ? (
              <div className="mt-1.5 space-y-0.5">
                {model.marketMlAway ? (
                  <BookUnit
                    bookKey={
                      model.marketSpread?.bookKey ?? row.bestLineBook ?? null
                    }
                  >
                    <div className="text-[17px] font-semibold text-white tabular-nums leading-tight">
                      {model.marketMlAway}
                    </div>
                  </BookUnit>
                ) : null}
                {model.marketMlHome ? (
                  <div className="text-[17px] font-semibold text-white tabular-nums leading-tight">
                    {model.marketMlHome}
                  </div>
                ) : null}
              </div>
            ) : model.marketSpread ? (
              <div className="mt-1.5">
                <BookUnit bookKey={model.marketSpread.bookKey}>
                  <div className="text-[17px] font-semibold text-white tabular-nums leading-tight">
                    {model.marketSpread.teamLabeled}
                    <Juice value={model.marketSpread.juice} />
                  </div>
                </BookUnit>
                {model.marketSpread.trustFootnote ? (
                  <div className="mt-0.5 text-[10px] text-gray-400">
                    {model.marketSpread.trustFootnote}
                  </div>
                ) : null}
              </div>
            ) : null}
            {model.marketTotal ? (
              <div className="mt-1.5 text-[13px] font-medium text-gray-100 tabular-nums leading-snug">
                {model.marketTotal.over}
                <Juice value={model.marketTotal.overJuice} />
                <span className="mx-1 text-gray-500">/</span>
                {model.marketTotal.under}
                <Juice value={model.marketTotal.underJuice} />
                {model.marketTotal.bookKey &&
                model.marketTotal.bookKey !== model.marketSpread?.bookKey ? (
                  <span className="ml-1.5 align-middle">
                    <SportsbookBadge book={model.marketTotal.bookKey} compact />
                  </span>
                ) : null}
                {model.marketTotal.trustFootnote ? (
                  <div className="mt-0.5 text-[10px] text-gray-400">
                    O/U {model.marketTotal.trustFootnote}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="min-w-0" data-col="kosedge-fair">
            <div
              className="text-[10px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: KOSEDGE_FAIR_GOLD }}
            >
              Kosedge Fair
            </div>
            {showFair ? (
              <>
                {model.isMoneyline ? (
                  <div className="mt-1.5 space-y-0.5">
                    {model.fairMlAway ? (
                      <div
                        className="text-[17px] font-semibold tabular-nums leading-tight"
                        style={{ color: KOSEDGE_FAIR_GOLD }}
                      >
                        {model.fairMlAway}
                      </div>
                    ) : null}
                    {model.fairMlHome ? (
                      <div
                        className="text-[17px] font-semibold tabular-nums leading-tight"
                        style={{ color: KOSEDGE_FAIR_GOLD }}
                      >
                        {model.fairMlHome}
                      </div>
                    ) : null}
                  </div>
                ) : model.fairSpread ? (
                  <div
                    className="mt-1.5 text-[17px] font-semibold tabular-nums leading-tight"
                    style={{ color: KOSEDGE_FAIR_GOLD }}
                  >
                    {model.fairSpread.teamLabeled}
                  </div>
                ) : null}
                {model.fairTotal ? (
                  <div
                    className="mt-1.5 text-[13px] font-medium tabular-nums leading-snug"
                    style={{ color: KOSEDGE_FAIR_GOLD_DIM }}
                  >
                    {model.fairTotal.over}
                    <span className="mx-1 opacity-70">/</span>
                    {model.fairTotal.under}
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* L3 — INTERPRETATION (one place) */}
      {showInterp ? (
        <div className="mt-3 space-y-1" data-testid="edge-board-mobile-interp">
          {model.spreadInterp ? (
            <InterpRow
              label={model.isMoneyline ? "ml" : "spread"}
              interp={model.spreadInterp}
            />
          ) : null}
          {model.totalInterp ? (
            <InterpRow label="total" interp={model.totalInterp} />
          ) : null}
          {model.confidence ? (
            <div className="text-[11px] text-gray-400">{model.confidence}</div>
          ) : null}
          {model.sizeDown ? (
            <div className="text-[10px] font-semibold uppercase tracking-wide text-amber-300/80">
              Size down
            </div>
          ) : null}
        </div>
      ) : model.confidence ? (
        <div className="mt-3 text-[11px] text-gray-400">{model.confidence}</div>
      ) : null}

      {/* L4 — MARKET CONTEXT */}
      {showContext ? (
        <div
          className="mt-2.5 text-[12px] text-gray-400 leading-snug"
          data-testid="edge-board-mobile-context"
        >
          {model.openSpread || model.openTotal ? (
            <div className="tabular-nums">
              Open
              {model.openSpread ? ` ${model.openSpread}` : ""}
              {model.openSpread && model.openTotal ? " · " : " "}
              {model.openTotal ?? ""}
            </div>
          ) : null}
          {model.linesAsOfLabel ? (
            <div className={model.linesStale ? "text-amber-300/80" : ""}>
              Updated {model.linesAsOfLabel}
              {model.linesStale ? " · stale" : ""}
            </div>
          ) : model.asOfUnavailable ? (
            <div className="text-amber-200/80">Market as-of unavailable</div>
          ) : null}
        </div>
      ) : null}

      {/* L5 — DETAILS */}
      <div className="mt-2.5 flex items-center gap-2">
        <button
          type="button"
          onClick={() => onToggle("overview")}
          aria-expanded={overviewOpen}
          className="inline-flex min-h-11 flex-1 items-center justify-center rounded-lg px-2 text-[13px] font-medium text-kos-gold hover:bg-white/5"
        >
          {overviewOpen ? "Overview ▴" : "Overview ▾"}
        </button>
        <button
          type="button"
          onClick={() => onToggle("stats")}
          aria-expanded={statsOpen}
          className="inline-flex min-h-11 flex-1 items-center justify-center rounded-lg px-2 text-[13px] font-medium text-kos-gold hover:bg-white/5"
        >
          {statsOpen ? "Stats ▴" : "Stats ▾"}
        </button>
      </div>

      {overviewOpen ? (
        <div className="mt-2 rounded-lg border border-white/10 bg-black/60 p-3 text-[11px] leading-relaxed whitespace-pre-wrap text-gray-300">
          {row.siteLabel ? (
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-amber-200/90">
              {row.siteLabel}
            </div>
          ) : null}
          {model.overview ?? "No overview available."}
          {model.modelNote ? (
            <div className="mt-2 text-[10px] text-gray-400">
              {model.modelNote}
            </div>
          ) : null}
        </div>
      ) : null}
      {statsOpen ? (
        <div className="mt-2 rounded-lg border border-white/10 bg-black/70 p-3">
          {row.statDrop ? (
            <EdgeBoardStatDrop drop={row.statDrop} />
          ) : (
            <div className="text-xs text-gray-500">Stat Drop unavailable.</div>
          )}
        </div>
      ) : null}
    </article>
  );
}
