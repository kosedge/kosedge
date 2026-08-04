import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SeasonEngineSurvivorPlannerClient from "@/components/pro/nfl/SeasonEngineSurvivorPlannerClient";

const planPayload = {
  path_survival: 0.624,
  path_strength: "OK",
  path_strength_geo: 0.62,
  locked_pick_count: 1,
  n_sims: 250,
  engine_version: "test-engine",
  weeks: [
    {
      week: 1,
      status: "open",
      ranked_picks: [
        {
          team: "SEA",
          win_rate: 0.624,
          pick_now_score: 0.38,
          opponent: "SF",
          home_away: "home",
        },
        { team: "MIA", win_rate: 0.584, pick_now_score: 0.37 },
      ],
      available_teams: ["SEA", "MIA", "CHI"],
    },
  ],
};

describe("SeasonEngineSurvivorPlannerClient", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/pro/nfl/survivor?mode=planner");
    window.localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => planPayload,
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it(
    "locks a recommendation chip and clears the week with real buttons",
    async () => {
      const user = userEvent.setup();
      render(<SeasonEngineSurvivorPlannerClient engineVersion="test-engine" />);

      await waitFor(
        () => {
          expect(screen.getByRole("button", { name: /SEA/ })).toBeInTheDocument();
        },
        { timeout: 4000 },
      );

      await user.click(screen.getByRole("button", { name: /SEA/ }));

      await waitFor(() => {
        expect(screen.getByText(/Used: SEA/)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument();
      });
      expect(window.location.search).toContain("picks=1%3ASEA");

      await user.click(screen.getByRole("button", { name: "Clear" }));

      await waitFor(() => {
        expect(screen.getByText(/Used: none/)).toBeInTheDocument();
      });
    },
    15000,
  );

  it("exposes Reset plan as a real button", async () => {
    const user = userEvent.setup();
    render(<SeasonEngineSurvivorPlannerClient />);
    await waitFor(
      () => {
        expect(screen.getByRole("button", { name: /SEA/ })).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    await user.click(screen.getByRole("button", { name: /SEA/ }));
    await waitFor(() => expect(screen.getByText(/Used: SEA/)).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Reset plan" }));
    await waitFor(() => {
      expect(screen.getByText(/Used: none/)).toBeInTheDocument();
    });
  }, 15000);
});
