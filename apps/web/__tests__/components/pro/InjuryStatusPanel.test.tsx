import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import InjuryStatusPanel from "@/components/pro/InjuryStatusPanel";

describe("InjuryStatusPanel", () => {
  it("renders polished fallback when injuries are missing", () => {
    render(<InjuryStatusPanel rows={[]} />);
    expect(
      screen.getByText(
        "Injury report is currently unavailable for the selected team/week.",
      ),
    ).toBeInTheDocument();
  });
});
