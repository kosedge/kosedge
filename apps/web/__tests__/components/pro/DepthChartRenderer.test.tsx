import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import DepthChartRenderer from "@/components/pro/DepthChartRenderer";
import type { NflIntelResponseRow } from "@/lib/nfl-intel";

describe("DepthChartRenderer", () => {
  it("orders skill positions first in QB/RB/WR/TE sequence", () => {
    const rows: NflIntelResponseRow[] = [
      { position: "CB", player_name: "Corner One", depth_slot: "starter", depth_order: 1 },
      { position: "WR", player_name: "Wideout One", depth_slot: "starter", depth_order: 1 },
      { position: "QB", player_name: "Quarterback One", depth_slot: "starter", depth_order: 1 },
      { position: "TE", player_name: "Tight End One", depth_slot: "starter", depth_order: 1 },
      { position: "RB", player_name: "Running Back One", depth_slot: "starter", depth_order: 1 },
    ];

    const { container } = render(<DepthChartRenderer rows={rows} />);
    const headings = Array.from(container.querySelectorAll("h3")).map((el) => el.textContent);
    expect(headings.slice(0, 5)).toEqual(["QB", "RB", "WR", "TE", "CB"]);
  });

  it("renders fantasy-relevant stat strings for known player rows", () => {
    const rows: NflIntelResponseRow[] = [
      {
        position: "QB",
        player_name: "Starter QB",
        depth_slot: "starter",
        depth_order: 1,
        pass_yards: 287,
        pass_touchdowns: 2,
        rush_yards: 31,
        touchdowns_scored: 3,
      },
      {
        position: "WR",
        player_name: "WR1",
        depth_slot: "starter",
        depth_order: 1,
        receiving_yards: 108,
        receptions: 8,
        touchdowns_scored: 1,
      },
    ];

    render(<DepthChartRenderer rows={rows} />);
    expect(screen.getByText(/Pass 287 \(1\)y \/ 2 \(1\) TD/)).toBeInTheDocument();
    expect(screen.getByText(/Rush 31 \(1\)y \/ 3 \(1\) TD/)).toBeInTheDocument();
    expect(screen.getByText("Rec 108 (1)y / 8 (1) rec / 1 (1) TD")).toBeInTheDocument();
  });

  it("renders premium placeholder when projections are unavailable", () => {
    const rows: NflIntelResponseRow[] = [
      {
        position: "RB",
        player_name: "Depth RB",
        depth_slot: "backup",
        depth_order: 2,
        rush_yards: 54,
        touchdowns_scored: 0,
      },
    ];

    render(<DepthChartRenderer rows={rows} />);
    expect(screen.getByText("Premium rest-of-year projection pending")).toBeInTheDocument();
    expect(screen.getByText("Premium Pending")).toBeInTheDocument();
    expect(screen.getByText(/Rush 54 \(1\)y \/ 0 \(1\) TD/)).toBeInTheDocument();
  });

  it("renders decimal metrics with 3-digit precision", () => {
    const rows: NflIntelResponseRow[] = [
      {
        position: "QB",
        player_name: "Precision QB",
        depth_slot: "starter",
        depth_order: 1,
        role_confidence: 0.92349,
        pass_yards_mean: 267.4567,
        pass_tds_mean: 2.1129,
        fantasy_points_roy: 21.9876,
      },
    ];

    render(<DepthChartRenderer rows={rows} />);
    expect(screen.getByText(/267.457 \(1\)y \/ 2.113 \(1\) TD/)).toBeInTheDocument();
    expect(screen.getByText(/92.349 \(1\)% role confidence/)).toBeInTheDocument();
    expect(screen.getByText(/FPTS 21.988 \(1\)/)).toBeInTheDocument();
  });
});
