import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import TeamIntelStatCards from "@/components/pro/TeamIntelStatCards";

describe("TeamIntelStatCards", () => {
  it("shows combined record with win_pct rank", () => {
    render(
      <TeamIntelStatCards
        row={{
          team: "BUF",
          wins: 15,
          losses: 2,
          ties: 0,
          win_pct: 0.882,
          point_diff: 140,
          pass_rate: 0.58,
          red_zone_td_rate: 0.65,
          epa_per_play_offense: 0.19,
          epa_per_play_defense_allowed: -0.08,
        }}
        comparisonRows={[
          {
            team: "MIA",
            wins: 11,
            losses: 6,
            ties: 0,
            win_pct: 0.647,
            point_diff: 40,
          },
          {
            team: "BUF",
            wins: 15,
            losses: 2,
            ties: 0,
            win_pct: 0.882,
            point_diff: 140,
          },
          {
            team: "NYJ",
            wins: 5,
            losses: 12,
            ties: 0,
            win_pct: 0.294,
            point_diff: -120,
          },
        ]}
      />,
    );

    expect(screen.getByText("Record")).toBeInTheDocument();
    expect(screen.getByText("15-2 (1)")).toBeInTheDocument();
    expect(screen.queryByText("Wins")).not.toBeInTheDocument();
    expect(screen.queryByText("Losses")).not.toBeInTheDocument();
  });
});
