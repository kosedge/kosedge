// apps/web/__tests__/components/auth/UserMenu.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import UserMenu from "@/components/auth/UserMenu";
import { useSession, signOut } from "next-auth/react";

vi.mock("next-auth/react", () => ({
  useSession: vi.fn(),
  signOut: vi.fn(),
}));

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
    const mockSignOut = signOut as unknown as ReturnType<typeof vi.fn>;
    mockSignOut.mockImplementation(() => Promise.resolve());

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

    const user = userEvent.setup();

    render(<UserMenu />);

    // Open the menu first
    const menuButton = screen.getByText("Test User").closest("button");
    if (menuButton) {
      await user.click(menuButton);
    }

    const signOutButton = screen.getByText("Sign Out");
    await user.click(signOutButton);

    expect(mockSignOut).toHaveBeenCalledWith({ callbackUrl: "/" });
  });
});
