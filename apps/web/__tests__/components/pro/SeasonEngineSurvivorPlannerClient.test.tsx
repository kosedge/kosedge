import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SeasonEngineSurvivorPlannerClient from "@/components/pro/nfl/SeasonEngineSurvivorPlannerClient";

const planPayload = {
  path_survival: 0.012,
  path_strength: "Fragile",
  path_strength_geo: 0.58,
  locked_pick_count: 1,
  avg_locked_wp: 0.624,
  danger_weeks: 0,
  best_remaining_equity: 0.71,
  slate_grade: "B",
  slate_score: 62,
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
          this_week_wp: 0.624,
          pick_now_score: 0.38,
          opponent: "ARI",
          home_away: "home",
          matchup_label: "SEA vs ARI",
          is_favorite: true,
          favorite_team: "SEA",
          favorite_wp: 0.624,
        },
        {
          team: "MIA",
          win_rate: 0.584,
          this_week_wp: 0.584,
          pick_now_score: 0.37,
          opponent: "NE",
          home_away: "home",
          matchup_label: "MIA vs NE",
          is_favorite: true,
          favorite_team: "MIA",
          favorite_wp: 0.584,
        },
      ],
      available_teams: ["SEA", "MIA", "CHI"],
    },
  ],
};

const suggestPayload = {
  paths: [
    {
      id: "chalk",
      label: "Chalk",
      blurb: "Highest weekly win % among unused teams.",
      picks: { "1": "SEA", "2": "KC" },
      pick_count: 2,
      avg_locked_wp: 0.66,
      danger_weeks: 0,
      slate_grade: "B",
      slate_score: 66,
    },
    {
      id: "balanced",
      label: "Balanced",
      blurb: "Greedy pick_now_score.",
      picks: { "1": "MIA", "2": "BUF" },
      pick_count: 2,
      avg_locked_wp: 0.61,
      danger_weeks: 1,
      slate_grade: "C",
      slate_score: 57,
    },
    {
      id: "contrarian_save",
      label: "Contrarian save",
      blurb: "Bank premium future spots.",
      picks: { "1": "CHI", "2": "DEN" },
      pick_count: 2,
      avg_locked_wp: 0.58,
      danger_weeks: 2,
      slate_grade: "C",
      slate_score: 50,
    },
  ],
};

describe("SeasonEngineSurvivorPlannerClient", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/pro/nfl/survivor?mode=planner");
    window.localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url =
          typeof input === "string"
            ? input
            : input instanceof URL
              ? input.href
              : input instanceof Request
                ? input.url
                : String(input);
        if (url.includes("suggest-paths")) {
          return {
            ok: true,
            status: 200,
            json: async () => suggestPayload,
          };
        }
        return {
          ok: true,
          status: 200,
          json: async () => planPayload,
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it(
    "shows matchup context, locks without pick_now clutter, and clears fully",
    async () => {
      const user = userEvent.setup();
      render(<SeasonEngineSurvivorPlannerClient engineVersion="test-engine" />);

      await waitFor(
        () => {
          expect(screen.getByRole("button", { name: /SEA/ })).toBeInTheDocument();
        },
        { timeout: 10000 },
      );

      const seaChip = screen.getByRole("button", { name: /SEA/ });
      expect(within(seaChip).getByText(/ARI/)).toBeInTheDocument();
      expect(within(seaChip).getByText(/62%/)).toBeInTheDocument();
      expect(seaChip.textContent || "").not.toMatch(/0\.38/);

      await user.click(seaChip);

      await waitFor(() => {
        expect(screen.getByText(/Used: SEA/)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Clear" })).toBeInTheDocument();
      });
      expect(window.location.search).toContain("picks=1%3ASEA");

      await user.click(screen.getByRole("button", { name: "Clear" }));

      await waitFor(() => {
        expect(screen.getByText(/Used: none/)).toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Clear" })).not.toBeInTheDocument();
      });
      expect(window.location.search).not.toContain("picks=");
    },
    15000,
  );

  it("lists used + available at top and can pick any remaining team from the dropdown", async () => {
    const user = userEvent.setup();
    render(<SeasonEngineSurvivorPlannerClient engineVersion="test-engine" />);

    await waitFor(
      () => {
        expect(screen.getByRole("button", { name: /SEA/ })).toBeInTheDocument();
      },
      { timeout: 10000 },
    );
    expect(screen.getByText(/Used: none/)).toBeInTheDocument();
    expect(screen.getByText(/Available:/).textContent || "").toMatch(/CHI/);

    await user.click(screen.getByRole("button", { name: "Week 1 pick" }));
    const list = screen.getByRole("listbox");
    await user.click(within(list).getByRole("button", { name: /CHI/ }));

    await waitFor(() => {
      expect(screen.getByText(/Used: CHI/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Available:/).textContent || "").not.toMatch(/\bCHI\b/);
  }, 15000);

  it("resets plan including localStorage and URL picks", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(
      "kosedge.nfl.survivor.planner.picks",
      JSON.stringify({ "1": "SEA" }),
    );
    window.history.replaceState(
      null,
      "",
      "/pro/nfl/survivor?mode=planner&picks=1:SEA",
    );
    render(<SeasonEngineSurvivorPlannerClient />);
    await waitFor(
      () => {
        expect(screen.getByText(/Used: SEA/)).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    await user.click(screen.getByRole("button", { name: "Reset plan" }));
    await waitFor(() => {
      expect(screen.getByText(/Used: none/)).toBeInTheDocument();
    });
    expect(window.localStorage.getItem("kosedge.nfl.survivor.planner.picks")).toBeNull();
    expect(window.location.search).not.toContain("picks=");
  }, 15000);

  it("loads an AI suggested path into the slate", async () => {
    const user = userEvent.setup();
    render(<SeasonEngineSurvivorPlannerClient />);
    await user.click(
      screen.getByRole("button", { name: /Load suggested paths/i }),
    );
    await waitFor(
      () => {
        expect(screen.getByRole("button", { name: /Chalk/ })).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    await user.click(screen.getByRole("button", { name: /Chalk/ }));
    await waitFor(() => {
      expect(screen.getByText(/Used: KC, SEA/)).toBeInTheDocument();
    });
    expect(window.location.search).toContain("1%3ASEA");
  }, 15000);

  it("exposes hero slate metrics instead of joint survival as primary", async () => {
    render(<SeasonEngineSurvivorPlannerClient />);
    expect(screen.getByText("Week 1")).toBeInTheDocument();
    await waitFor(
      () => {
        expect(screen.getByText("Slate grade")).toBeInTheDocument();
        expect(screen.getByText("Avg weekly WP")).toBeInTheDocument();
        expect(screen.getByText("Danger weeks")).toBeInTheDocument();
        expect(screen.getByText("Best left")).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    expect(screen.queryByText("Path survival")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset plan" }).className).toMatch(
      /min-h-11/,
    );
    expect(
      screen.getByRole("button", { name: /Load suggested paths/i }),
    ).toBeInTheDocument();
    await waitFor(() => {
      const planCalls = vi
        .mocked(fetch)
        .mock.calls.filter((call) => String(call[0]).includes("/plan"));
      expect(planCalls.length).toBeGreaterThan(0);
      const body = JSON.parse(String(planCalls[0]?.[1]?.body ?? "{}")) as {
        nSims?: number;
      };
      expect(body.nSims).toBe(50);
    });
    expect(
      vi.mocked(fetch).mock.calls.some((call) =>
        String(call[0]).includes("suggest-paths"),
      ),
    ).toBe(false);
  }, 15000);

  it("shows engine warming, not Planner error, when plan times out", async () => {
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input instanceof Request
              ? input.url
              : input,
      );
      if (url.includes("suggest-paths")) {
        return { ok: true, status: 200, json: async () => suggestPayload };
      }
      return {
        ok: false,
        status: 504,
        json: async () => ({
          error:
            "Engine warming — survivor rankings timed out. Retry in a few seconds; this is not a blank hang.",
        }),
      };
    });
    render(<SeasonEngineSurvivorPlannerClient engineVersion="test-engine" />);
    await waitFor(
      () => {
        expect(screen.getByText("Engine warming")).toBeInTheDocument();
      },
      { timeout: 8000 },
    );
    expect(screen.queryByText("Planner error")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Retry rankings/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Week 1")).toBeInTheDocument();
  }, 12000);

  it("keeps duplicate-team failures as Planner error", async () => {
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input instanceof Request
              ? input.url
              : input,
      );
      if (url.includes("suggest-paths")) {
        return { ok: true, status: 200, json: async () => suggestPayload };
      }
      return {
        ok: false,
        status: 400,
        json: async () => ({
          error: "Team KC locked in multiple weeks; survivor allows one use",
        }),
      };
    });
    render(<SeasonEngineSurvivorPlannerClient engineVersion="test-engine" />);
    await waitFor(
      () => {
        expect(screen.getByText("Planner error")).toBeInTheDocument();
      },
      { timeout: 8000 },
    );
    expect(screen.queryByText("Engine warming")).not.toBeInTheDocument();
    expect(screen.getByText(/Team KC locked in multiple weeks/)).toBeInTheDocument();
  }, 12000);
});
