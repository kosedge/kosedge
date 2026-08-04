import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SeasonEngineSurvivorShell from "@/components/pro/nfl/SeasonEngineSurvivorShell";

vi.mock("@/components/pro/nfl/SeasonEngineSurvivorPlannerClient", () => ({
  default: () => <div data-testid="planner">Planner mounted</div>,
}));

vi.mock("@/components/pro/nfl/SeasonEngineSurvivorClient", () => ({
  default: () => <div data-testid="helper">Helper mounted</div>,
}));

describe("SeasonEngineSurvivorShell", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/pro/nfl/survivor?mode=planner");
  });

  it("switches modes with real buttons on click", async () => {
    const user = userEvent.setup();
    render(<SeasonEngineSurvivorShell defaultMode="planner" />);

    expect(screen.getByTestId("planner")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "17-week planner" })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    await user.click(screen.getByRole("tab", { name: "Single-week helper" }));

    expect(screen.getByTestId("helper")).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "Single-week helper" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(window.location.search).toContain("mode=helper");
  });
});
