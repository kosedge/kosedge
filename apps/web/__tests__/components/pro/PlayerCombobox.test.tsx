import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlayerCombobox } from "@/components/pro/nfl/fantasy/PlayerCombobox";
import type { FantasyDeskRow } from "@/lib/fantasy/types";

function row(
  partial: Pick<FantasyDeskRow, "playerId" | "playerName" | "position" | "team">,
): FantasyDeskRow {
  return {
    season: 2026,
    scoringProfile: "half_ppr",
    modelVersion: "test",
    playerUid: null,
    gamesProjected: 17,
    passYardsTotal: 0,
    rushYardsTotal: 0,
    receivingYardsTotal: 800,
    receptionsTotal: 60,
    passTdsTotal: 0,
    rushTdsTotal: 0,
    recTdsTotal: 4,
    totalPoints: 180,
    floorPoints: 140,
    medianPoints: 180,
    ceilingPoints: 220,
    replacementPoints: 100,
    valueOverReplacement: 80,
    rankOverall: 12,
    rankPosition: 4,
    tier: "WR1",
    adp: 14,
    valueDelta: 2,
    isRookie: false,
    rookieYear: null,
    draftNumber: null,
    schedule: {
      early: "neutral",
      playoff: "neutral",
      label: "Neutral",
      detail: "",
    },
    riskFlags: [],
    expertBlurb: "",
    drivers: [],
    updatedAt: null,
    source: "preseason-fallback",
    ...partial,
  };
}

describe("PlayerCombobox", () => {
  it("searches by name and adds to builder", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const players = [
      row({
        playerId: "jj",
        playerName: "Justin Jefferson",
        position: "WR",
        team: "MIN",
      }),
      row({
        playerId: "cd",
        playerName: "CeeDee Lamb",
        position: "WR",
        team: "DAL",
      }),
    ];

    render(
      <PlayerCombobox
        players={players}
        rosterSet={new Set()}
        onToggle={onToggle}
      />,
    );

    const input = screen.getByRole("combobox");
    await user.click(input);
    await user.type(input, "Jefferson");
    expect(screen.getByText("Justin Jefferson")).toBeInTheDocument();
    expect(screen.queryByText("CeeDee Lamb")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Add to builder" }));
    expect(onToggle).toHaveBeenCalledWith("jj");
  });

  it("does not add a player already on the roster", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <PlayerCombobox
        players={[
          row({
            playerId: "jj",
            playerName: "Justin Jefferson",
            position: "WR",
            team: "MIN",
          }),
        ]}
        rosterSet={new Set(["jj"])}
        onToggle={onToggle}
      />,
    );
    await user.click(screen.getByRole("combobox"));
    expect(screen.getByRole("button", { name: "Add to builder" })).toBeDisabled();
    await user.click(screen.getByText("Justin Jefferson"));
    expect(onToggle).not.toHaveBeenCalled();
  });
});
