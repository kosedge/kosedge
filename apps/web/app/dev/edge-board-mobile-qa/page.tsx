"use client";

import { useState } from "react";
// Unlisted fixture gallery — not linked from nav.
import EdgeBoard from "@/components/EdgeBoard";
import EdgeBoardMobileCard from "@/components/EdgeBoardMobileCard";
import {
  qaCfbEmptyCard,
  qaLongNameCard,
  qaMissingJuiceOpenFair,
  qaNflFlatRows,
  qaNflLeanCard,
  qaNflNeutralCard,
  qaNflPassPickemCard,
  qaNflPlayCard,
} from "@/lib/edge-board-mobile-qa-fixtures";

/**
 * Unlisted QA gallery for the locked mobile hierarchy.
 * Fixture-only — no Odds API.
 */
export default function EdgeBoardMobileQaPage() {
  const [open, setOpen] = useState<Record<string, "overview" | "stats" | null>>(
    {},
  );
  const cards = [
    { key: "lean", sport: "nfl", row: qaNflLeanCard(), title: "NFL LEAN" },
    { key: "play", sport: "nfl", row: qaNflPlayCard(), title: "NFL PLAY" },
    {
      key: "pass",
      sport: "nfl",
      row: qaNflPassPickemCard(),
      title: "NFL PASS / pick’em",
    },
    {
      key: "neutral",
      sport: "nfl",
      row: qaNflNeutralCard(),
      title: "Neutral site",
    },
    {
      key: "missing",
      sport: "nfl",
      row: qaMissingJuiceOpenFair(),
      title: "Missing juice / open / fair",
    },
    { key: "cfb", sport: "cfb", row: qaCfbEmptyCard(), title: "CFB empty" },
    { key: "long", sport: "cfb", row: qaLongNameCard(), title: "Long names" },
  ] as const;

  return (
    <div className="min-h-screen bg-[#070A0F] text-gray-100 px-3 py-6">
      <h1 className="text-2xl font-bebas text-edge-green">
        Edge Board mobile hierarchy QA
      </h1>
      <p className="mt-1 text-xs text-gray-400">
        Fixture-only. No Odds API. Desktop table below lg is hidden — scroll the
        last block at ≥lg for regression.
      </p>
      <div className="mt-4 max-w-[430px] space-y-6" data-qa="mobile-cards">
        {cards.map((c) => (
          <section key={c.key}>
            <h2 className="mb-2 text-[11px] uppercase tracking-wide text-gray-500">
              {c.title}
            </h2>
            <EdgeBoardMobileCard
              row={c.row}
              sportKey={c.sport}
              overviewOpen={open[c.key] === "overview"}
              statsOpen={open[c.key] === "stats"}
              onToggle={(panel) =>
                setOpen((prev) => ({
                  ...prev,
                  [c.key]: prev[c.key] === panel ? null : panel,
                }))
              }
            />
          </section>
        ))}
      </div>
      <section className="mt-10" data-qa="full-board">
        <h2 className="mb-2 text-[11px] uppercase tracking-wide text-gray-500">
          Full EdgeBoard (desktop table ≥lg)
        </h2>
        <EdgeBoard variant="full" sportKey="nfl" rows={qaNflFlatRows()} />
      </section>
    </div>
  );
}
