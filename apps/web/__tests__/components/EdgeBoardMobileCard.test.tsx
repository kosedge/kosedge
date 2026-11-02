import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EdgeBoardMobileCard from "@/components/EdgeBoardMobileCard";
import type { LegacyEdgeBoardRow } from "@/lib/flat-rows-to-legacy";
import { UNICODE_MINUS } from "@/lib/edge-board-mobile-presentation";

const EMPTY_PAIR = {
  top: { label: "—", juice: "—" },
  bottom: { label: "—", juice: "—" },
};

function nflLeanRow(
  partial: Partial<LegacyEdgeBoardRow> = {},
): LegacyEdgeBoardRow {
  return {
    id: "ne-sea",
    teamA: { name: "New England Patriots", site: "Away" },
    teamB: { name: "Seattle Seahawks", site: "Home" },
    awayAbbr: "NE",
    homeAbbr: "SEA",
    kickoffDate: "09/13",
    kickoffTime: "8:20 PM",
    linesAsOf: "2026-09-10T16:41:00Z",
    openLine: {
      top: { label: "+3.0", juice: "-110" },
      bottom: { label: "-3.0", juice: "-110" },
    },
    openOU: {
      top: { label: "o45.5", juice: "-110" },
      bottom: { label: "u45.5", juice: "-110" },
    },
    bestLine: {
      top: { label: "+2.5", juice: "-108" },
      bottom: { label: "-2.5", juice: "-108" },
    },
    bestOU: {
      top: { label: "o44.5", juice: "-105" },
      bottom: { label: "u44.5", juice: "-115" },
    },
    bestLineBook: "draftkings",
    bestOUBook: "fanduel",
    keiLine: {
      top: { label: "+3.9", juice: "—" },
      bottom: { label: "-3.9", juice: "—" },
    },
    keiOU: {
      top: { label: "o45.1", juice: "—" },
      bottom: { label: "u45.1", juice: "—" },
    },
    marketLineCurrent: -2.5,
    marketOUCurrent: 44.5,
    fairLineKei: -3.9,
    fairOUKei: 45.1,
    tagLine: "LEAN",
    tagOU: "PASS",
    actionLabelLine: "LEAN",
    actionLabelOU: "PASS",
    edgeMagnitudeLine: 1.4,
    edgeMagnitudeOU: 0.6,
    edgeLineNum: 1.4,
    edgeOUNum: 0.6,
    edgeLineFavor: "Seahawks",
    edgeOUFavor: "Over",
    overview: "House vs street on SEA.",
    ...partial,
  };
}

describe("EdgeBoardMobileCard composition", () => {
  it("renders L1–L5: team-labeled hero, one interp, book=DK, no Lean-to", () => {
    render(
      <EdgeBoardMobileCard
        row={nflLeanRow()}
        sportKey="nfl"
        overviewOpen={false}
        statsOpen={false}
        onToggle={() => undefined}
      />,
    );
    expect(
      screen.getByText("New England Patriots @ Seattle Seahawks"),
    ).toBeInTheDocument();
    expect(screen.getByText("Market")).toBeInTheDocument();
    expect(screen.getByText("Kosedge Fair")).toBeInTheDocument();
    expect(screen.getByText(`SEA ${UNICODE_MINUS}2.5`)).toBeInTheDocument();
    expect(screen.getByText(`SEA ${UNICODE_MINUS}3.9`)).toBeInTheDocument();
    expect(screen.getByText(/O 44\.5/)).toBeInTheDocument();
    expect(screen.getByText("LEAN")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
    expect(screen.getByText("+1.4 pts")).toBeInTheDocument();
    expect(screen.queryByText(/Lean to/)).not.toBeInTheDocument();
    expect(screen.queryByText(/KEINFL/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Spread edge/i)).not.toBeInTheDocument();
    const overview = screen.getByRole("button", { name: /Overview/ });
    const stats = screen.getByRole("button", { name: /Stats/ });
    expect(overview).toBeInTheDocument();
    expect(stats).toBeInTheDocument();
    expect(overview).toHaveAttribute("aria-expanded", "false");
    expect(overview.className).toMatch(/min-h-11/);
    expect(overview.className).toMatch(/text-kos-gold\/65/);
    expect(overview.className).not.toMatch(/flex-1/);
    expect(overview.className).not.toMatch(/justify-center/);
    expect(overview.className).not.toMatch(/rounded-lg/);
    expect(overview.className).not.toMatch(/bg-kos-gold/);
    expect(stats.className).toMatch(/text-kos-gold\/65/);
    expect(stats.className).not.toMatch(/flex-1/);
    const card = screen.getByTestId("edge-board-mobile-card");
    expect(card.textContent).toContain("DK");
    expect(card.textContent).toMatch(/Open/);
  });

  it("collapses CFB empty/null — no giant em-dash panels", () => {
    render(
      <EdgeBoardMobileCard
        row={{
          id: "cfb-null",
          teamA: { name: "North Carolina Tar Heels", site: "Away" },
          teamB: { name: "TCU Horned Frogs", site: "Home" },
          awayAbbr: "UNC",
          homeAbbr: "TCU",
          openOU: EMPTY_PAIR,
          openLine: EMPTY_PAIR,
          bestLine: EMPTY_PAIR,
          bestOU: EMPTY_PAIR,
          kickoffDate: "08/29",
          kickoffTime: "12:00 PM",
        }}
        sportKey="cfb"
        overviewOpen={false}
        statsOpen={false}
        onToggle={() => undefined}
      />,
    );
    expect(
      screen.getByText("North Carolina Tar Heels @ TCU Horned Frogs"),
    ).toBeInTheDocument();
    expect(screen.queryByText("— —")).not.toBeInTheDocument();
    expect(screen.queryByText("undefined")).not.toBeInTheDocument();
    expect(screen.queryByText("NaN")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("edge-board-mobile-interp"),
    ).not.toBeInTheDocument();
  });

  it("emphasizes Neutral · City and opens Overview without raw-model on collapse", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const { rerender } = render(
      <EdgeBoardMobileCard
        row={nflLeanRow({
          isNeutral: true,
          siteLabel: "Neutral · São Paulo",
          modelLine: {
            top: { label: "+4.0", juice: "—" },
            bottom: { label: "-4.0", juice: "—" },
          },
        })}
        sportKey="nfl"
        overviewOpen={false}
        statsOpen={false}
        onToggle={onToggle}
      />,
    );
    const venue = screen.getByText("Neutral · São Paulo");
    expect(venue).toHaveAttribute("data-venue", "neutral");
    expect(screen.queryByText(/Model /)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Overview/ }));
    expect(onToggle).toHaveBeenCalledWith("overview");

    rerender(
      <EdgeBoardMobileCard
        row={nflLeanRow({
          isNeutral: true,
          siteLabel: "Neutral · São Paulo",
          modelLine: {
            top: { label: "+4.0", juice: "—" },
            bottom: { label: "-4.0", juice: "—" },
          },
        })}
        sportKey="nfl"
        overviewOpen
        statsOpen={false}
        onToggle={onToggle}
      />,
    );
    expect(screen.getByText(/Model /)).toBeInTheDocument();
    const overviewOpenBtn = screen.getByRole("button", { name: /Overview/ });
    const statsQuiet = screen.getByRole("button", { name: /Stats/ });
    expect(overviewOpenBtn).toHaveAttribute("aria-expanded", "true");
    expect(overviewOpenBtn.className).toMatch(/min-h-11/);
    expect(overviewOpenBtn.className).toMatch(/text-kos-gold/);
    expect(overviewOpenBtn.className).not.toMatch(/text-kos-gold\/65/);
    expect(overviewOpenBtn.className).not.toMatch(/flex-1/);
    expect(overviewOpenBtn.className).not.toMatch(/justify-center/);
    expect(overviewOpenBtn.className).not.toMatch(/rounded-lg/);
    expect(overviewOpenBtn.className).not.toMatch(/bg-kos-gold/);
    expect(overviewOpenBtn.className).not.toMatch(/hover:bg-white/);
    expect(statsQuiet.className).toMatch(/text-kos-gold\/65/);
    expect(statsQuiet.className).not.toMatch(/flex-1/);
  });

  it("does not paint a mismatched book when decision line ≠ best display", () => {
    render(
      <EdgeBoardMobileCard
        row={nflLeanRow({
          marketLineCurrent: -2.5,
          bestLine: {
            top: { label: "+3.5", juice: "-110" },
            bottom: { label: "-3.5", juice: "-110" },
          },
          bestLineBook: "fanduel",
          bestOUBook: undefined,
          bestOU: {
            top: { label: "—", juice: "—" },
            bottom: { label: "—", juice: "—" },
          },
          marketOUCurrent: undefined,
          fairOUKei: undefined,
          keiOU: undefined,
        })}
        sportKey="nfl"
        overviewOpen={false}
        statsOpen={false}
        onToggle={() => undefined}
      />,
    );
    expect(screen.getByText(`SEA ${UNICODE_MINUS}2.5`)).toBeInTheDocument();
    const hero = screen.getByTestId("edge-board-mobile-hero");
    expect(hero.textContent).not.toContain("FD");
    expect(hero.textContent).not.toContain("FanDuel");
  });
});

describe("mobile source lock", () => {
  it("EdgeBoard wires the dedicated card below lg only", () => {
    const src = readFileSync(
      path.join(__dirname, "../../components/EdgeBoard.tsx"),
      "utf8",
    );
    expect(src).toContain("EdgeBoardMobileCard");
    expect(src).toContain("lg:hidden");
    expect(src).toContain("hidden lg:block");
    expect(src).not.toMatch(/KEI · \{keiCode\}/);
  });
});
