import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: ReactNode;
    href: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/nfl-intel", () => ({
  formatIntelValueWithRank: (value: unknown, rank?: number) =>
    `${String(value ?? "—")}${typeof rank === "number" ? ` (${rank})` : ""}`,
  formatTeamRecordWithRank: (
    row: Record<string, unknown> | undefined,
    rank?: number,
  ) => {
    if (!row) return "—";
    const wins = Number(row.wins ?? Number.NaN);
    const losses = Number(row.losses ?? Number.NaN);
    const ties = Number(row.ties ?? 0);
    if (!Number.isFinite(wins) || !Number.isFinite(losses)) return "—";
    const base = ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
    return typeof rank === "number" ? `${base} (${rank})` : base;
  },
  fetchNflIntel: vi.fn(),
  groupStandingsRows: (rows: unknown[]) => {
    const typedRows = rows as Array<Record<string, unknown>>;
    return [
      {
        conference: "AFC",
        division: "East",
        rows: typedRows.filter(
          (row) => row.conference === "AFC" && row.division === "East",
        ),
      },
      {
        conference: "NFC",
        division: "West",
        rows: typedRows.filter(
          (row) => row.conference === "NFC" && row.division === "West",
        ),
      },
    ];
  },
}));

import NflIntelTablePage from "@/components/pro/NflIntelTablePage";
import { fetchNflIntel } from "@/lib/nfl-intel";

afterEach(() => {
  vi.useRealTimers();
});

describe("NflIntelTablePage", () => {
  it("renders fallback guidance when latest period is used", async () => {
    vi.mocked(fetchNflIntel).mockResolvedValue({
      season: 2025,
      week: 22,
      team: null,
      count: 3,
      rows: [
        {
          team: "SEA",
          wins: 10,
          losses: 7,
          ties: 0,
          win_pct: 0.625,
          point_diff: 35,
          conference: "NFC",
          division: "West",
        },
        {
          team: "MIA",
          wins: 11,
          losses: 6,
          ties: 0,
          win_pct: 0.688,
          point_diff: 40,
          conference: "AFC",
          division: "East",
        },
        {
          team: "BUF",
          wins: 13,
          losses: 4,
          ties: 0,
          win_pct: 0.812,
          point_diff: 70,
          conference: "AFC",
          division: "East",
        },
      ],
      selection: {
        fallback_applied: true,
        latest_available: {
          season: 2025,
          week: 22,
          row_count: 320,
          team_count: 32,
        },
      },
    });

    const page = await NflIntelTablePage({
      endpoint: "standings",
      title: "NFL Team Intel · Standings",
      description: "Derived weekly standings",
      emptyHint: "No data",
      columns: [
        { key: "team", label: "Team" },
        { key: "record", label: "Record" },
      ],
    });

    render(page);

    expect(
      screen.getByText("ARCHIVE · showing 2025 finals (as-of) — not 2026 current"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Season 2025 · finals/)).toBeInTheDocument();
    expect(screen.queryByText(/W22/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Week 18/)).not.toBeInTheDocument();
    expect(screen.getByTestId("nfl-truth-state")).toHaveTextContent("ARCHIVE");
    expect(screen.getByText("AFC · East")).toBeInTheDocument();
    expect(screen.getByText("NFC · West")).toBeInTheDocument();
    expect(screen.getByText("BUF")).toBeInTheDocument();
    expect(screen.getByText("13-4 (1)")).toBeInTheDocument();
  });

  it("does not present 2026 Week 18 as current in August", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-12T16:00:00Z"));
    vi.mocked(fetchNflIntel).mockResolvedValue({
      season: 2026,
      week: 18,
      team: null,
      count: 1,
      rows: [{ team: "LAR", position: "QB", player_name: "Stafford" }],
      selection: {
        fallback_applied: true,
        latest_available: { season: 2026, week: 18, row_count: 1 },
      },
    });

    const page = await NflIntelTablePage({
      endpoint: "depth-charts",
      title: "NFL Depth Charts",
      description: "Depth",
      emptyHint: "No data",
      columns: [
        { key: "team", label: "Team" },
        { key: "player_name", label: "Player" },
      ],
    });

    render(page);

    expect(screen.getByText(/Season 2026 · Preseason/)).toBeInTheDocument();
    expect(screen.getByTestId("nfl-truth-state")).toHaveTextContent("PRESEASON");
    expect(screen.queryByText(/Week 18/)).not.toBeInTheDocument();
    expect(screen.queryByText(/2026 W18/)).not.toBeInTheDocument();
    vi.useRealTimers();
  });
});
