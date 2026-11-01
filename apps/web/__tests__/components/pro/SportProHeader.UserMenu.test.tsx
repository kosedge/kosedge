import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useSession, signOut } from "next-auth/react";
import SportProHeader from "@/components/pro/SportProHeader";
import { SPORTS } from "@/lib/sports";

const HEADER_SRC = readFileSync(
  resolve(__dirname, "../../../components/pro/SportProHeader.tsx"),
  "utf8",
);

const AUTHED_SESSION = {
  data: {
    user: {
      id: "user-1",
      email: "test@example.com",
      name: "Test User",
      role: "USER",
    },
  },
  status: "authenticated" as const,
};

describe("SportProHeader UserMenu mount", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useSession).mockReturnValue({
      data: null,
      status: "unauthenticated",
    } as ReturnType<typeof useSession>);
  });

  it("renders signed-out chrome next to usable sport hubs", () => {
    render(<SportProHeader activeSport="nba" />);

    expect(screen.getByRole("link", { name: "Sign In" })).toHaveAttribute(
      "href",
      "/auth/signin",
    );
    expect(screen.getByRole("link", { name: "Sign Up" })).toHaveAttribute(
      "href",
      "/auth/signup",
    );

    const hubs = screen.getByRole("navigation", { name: "Sport hubs" });
    for (const sport of SPORTS) {
      expect(
        within(hubs).getByRole("link", { name: sport.label }),
      ).toHaveAttribute("href", `/pro/${sport.key}/overview`);
    }
  });

  it("renders the loading pulse while the session is unresolved", () => {
    vi.mocked(useSession).mockReturnValue({
      data: null,
      status: "loading",
    } as ReturnType<typeof useSession>);

    render(<SportProHeader activeSport="nba" />);

    const mount = screen.getByTestId("sport-pro-header-user-menu");
    expect(mount.querySelector(".animate-pulse")).toBeInTheDocument();
    expect(screen.queryByText("Sign In")).not.toBeInTheDocument();
    expect(screen.queryByText("Sign Out")).not.toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Sport hubs" }),
    ).toBeInTheDocument();
  });

  it("exposes working sign-out from the authenticated menu", async () => {
    vi.mocked(useSession).mockReturnValue(
      AUTHED_SESSION as ReturnType<typeof useSession>,
    );
    const user = userEvent.setup();

    render(<SportProHeader activeSport="nba" />);

    await user.click(screen.getByRole("button", { name: /Test User/i }));
    await user.click(screen.getByRole("button", { name: "Sign Out" }));

    expect(signOut).toHaveBeenCalledTimes(1);
    expect(signOut).toHaveBeenCalledWith({ callbackUrl: "/" });
  });

  it("keeps the research desk nav usable after the mount", () => {
    render(<SportProHeader activeSport="nba" />);

    const desk = screen.getByRole("navigation", { name: "NBA research desk" });
    expect(
      within(desk).getByRole("link", { name: "Overview" }),
    ).toHaveAttribute("href", "/pro/nba/overview");
    expect(
      within(desk).getByRole("link", { name: "Edge Board" }),
    ).toHaveAttribute("href", "/edge-board/nba");
    expect(
      within(desk).getByRole("link", { name: "More tools" }),
    ).toHaveAttribute("href", "/pro/nba/overview#tools");
  });

  it("avoids mobile overflow and sticky/menu obstruction", () => {
    render(<SportProHeader activeSport="nba" />);

    const header = screen.getByRole("banner");
    expect(header.className).toContain("sticky");
    expect(header.className).toContain("top-0");
    expect(header.className).toContain("z-40");
    expect(header.className).toContain("[--kos-pro-header-h:6.75rem]");
    expect(header.className).toContain("sm:[--kos-pro-header-h:7.5rem]");
    expect(header.className).not.toMatch(/overflow-x-(hidden|clip|auto)/);

    const hubs = screen.getByRole("navigation", { name: "Sport hubs" });
    expect(hubs.className).toContain("min-w-0");
    expect(hubs.className).toContain("flex-1");
    expect(hubs.className).toContain("overflow-x-auto");
    expect(hubs.className).not.toContain("flex-wrap");

    const mount = screen.getByTestId("sport-pro-header-user-menu");
    expect(mount.className).toContain("shrink-0");
    expect(mount.parentElement?.className).toContain("min-w-0");
    expect(mount.parentElement?.className).not.toContain("flex-wrap");
  });

  it("keeps UserMenu when sport hubs are hidden", () => {
    render(<SportProHeader activeSport="nba" showSportsNav={false} />);

    expect(
      screen.queryByRole("navigation", { name: "Sport hubs" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign In" })).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "NBA research desk" }),
    ).toBeInTheDocument();
  });

  it("opens the authenticated menu above the sticky header without rewriting signOut", async () => {
    vi.mocked(useSession).mockReturnValue(
      AUTHED_SESSION as ReturnType<typeof useSession>,
    );
    const user = userEvent.setup();

    render(<SportProHeader activeSport="nba" />);
    await user.click(screen.getByRole("button", { name: /Test User/i }));

    const overlay = document.querySelector(".fixed.inset-0.z-50");
    expect(overlay).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign Out" }),
    ).toBeInTheDocument();
    expect(signOut).not.toHaveBeenCalled();
  });

  it("does not import auth, entitlement, or forecast-eligibility gates", () => {
    expect(HEADER_SRC).toMatch(/from ["']@\/components\/auth\/UserMenu["']/);
    expect(HEADER_SRC).not.toMatch(
      /getProAccessState|getEntitledProAccessState|OPEN_ACCESS|isFootballPublicNumbersDisabled|forecast/i,
    );
    expect(HEADER_SRC).not.toMatch(/lib\/auth\/pro|signOut\(|csrf/i);
  });
});
