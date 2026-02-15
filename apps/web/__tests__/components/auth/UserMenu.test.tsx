// apps/web/__tests__/components/auth/UserMenu.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@/lib/test-utils";
import UserMenu from "@/components/auth/UserMenu";
import { useSession, signOut } from "next-auth/react";

vi.mock("next-auth/react");

describe("UserMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show sign in and sign up buttons when not authenticated", () => {
    vi.mocked(useSession).mockReturnValue({
      data: null,
      status: "unauthenticated",
    } as any);

    render(<UserMenu />);

    expect(screen.getByText("Sign In")).toBeInTheDocument();
    expect(screen.getByText("Sign Up")).toBeInTheDocument();
  });

  it("should show loading state while checking session", () => {
    vi.mocked(useSession).mockReturnValue({
      data: null,
      status: "loading",
    } as any);

    render(<UserMenu />);

    // Should show loading indicator (the rounded div)
    const loadingElement = document.querySelector(".animate-pulse");
    expect(loadingElement).toBeInTheDocument();
  });

  it("should show user menu when authenticated", () => {
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: {
          id: "user-1",
          email: "test@example.com",
          name: "Test User",
          role: "USER",
        },
      },
      status: "authenticated",
    } as any);

    render(<UserMenu />);

    expect(screen.getByText("Test User")).toBeInTheDocument();
  });

  it("should show user email when name is not available", () => {
    vi.mocked(useSession).mockReturnValue({
      data: {
        user: {
          id: "user-1",
          email: "test@example.com",
          name: null,
          role: "USER",
        },
      },
      status: "authenticated",
    } as any);

    render(<UserMenu />);

    expect(screen.getByText("test@example.com")).toBeInTheDocument();
  });

  it("should call signOut when sign out button is clicked", async () => {
    const mockSignOut = vi.fn();
    vi.mocked(signOut).mockImplementation(mockSignOut);

    vi.mocked(useSession).mockReturnValue({
      data: {
        user: {
          id: "user-1",
          email: "test@example.com",
          name: "Test User",
          role: "USER",
        },
      },
      status: "authenticated",
    } as any);

    const { user } = await import("@testing-library/user-event");
    const userEvent = user.setup();

    render(<UserMenu />);

    // Open the menu first
    const menuButton = screen.getByText("Test User").closest("button");
    if (menuButton) {
      await userEvent.click(menuButton);
    }

    const signOutButton = screen.getByText("Sign Out");
    await userEvent.click(signOutButton);

    expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: "/" });
  });
});
