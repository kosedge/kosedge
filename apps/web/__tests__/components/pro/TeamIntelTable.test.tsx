import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import TeamIntelTable from "@/components/pro/TeamIntelTable";
import type { NflIntelResponseRow } from "@/lib/nfl-intel";

describe("TeamIntelTable Roster Pulse", () => {
  it("renders open_competition as Open competition — never snake_case", () => {
    const rows: NflIntelResponseRow[] = [
      {
        position: "QB",
        player_name: "Tua Tagovailoa",
        depth_slot: "open_competition",
        depth_order: 1,
        report_status: "active",
      },
      {
        position: "QB",
        player_name: "Michael Penix Jr.",
        depth_slot: "open_competition",
        depth_order: 2,
        report_status: "active",
      },
      {
        position: "QB",
        player_name: "Deshaun Watson",
        depth_slot: "open_competition",
        depth_order: 1,
        report_status: "active",
      },
      {
        position: "QB",
        player_name: "Shedeur Sanders",
        depth_slot: "open_competition",
        depth_order: 2,
        report_status: "active",
      },
    ];

    render(
      <TeamIntelTable
        title="Roster Pulse"
        rows={rows}
        empty="Roster hierarchy unavailable"
        columns={[
          { key: "position", label: "Pos" },
          { key: "player_name", label: "Player" },
          { key: "depth_slot", label: "Slot" },
          { key: "depth_order", label: "Order" },
          { key: "report_status", label: "Report" },
        ]}
      />,
    );

    expect(screen.getByText("Roster Pulse")).toBeInTheDocument();
    expect(screen.getAllByText("Open competition")).toHaveLength(4);
    expect(screen.queryByText(/open_competition/)).not.toBeInTheDocument();
    expect(screen.getAllByTestId("roster-pulse-depth-slot")).toHaveLength(4);
    for (const cell of screen.getAllByTestId("roster-pulse-depth-slot")) {
      expect(cell.textContent).toBe("Open competition");
    }
  });

  it("keeps ordinary depth_slot labels unchanged", () => {
    render(
      <TeamIntelTable
        title="Roster Pulse"
        rows={[
          {
            position: "RB",
            player_name: "Starter RB",
            depth_slot: "starter",
            depth_order: 1,
          },
        ]}
        empty="empty"
        columns={[
          { key: "player_name", label: "Player" },
          { key: "depth_slot", label: "Slot" },
        ]}
      />,
    );

    expect(screen.getByText("starter")).toBeInTheDocument();
  });
});
