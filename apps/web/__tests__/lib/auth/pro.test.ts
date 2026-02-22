// apps/web/__tests__/lib/auth/pro.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { isProUser, hasRole, getUserRole } from "@/lib/auth/pro";
import { UserRole, SubscriptionStatus } from "#prisma";
import { prisma } from "@/lib/db";
import { auth } from "@/lib/auth";

// Mock dependencies
vi.mock("@/lib/auth");
vi.mock("@/lib/db");

describe("Auth Pro Utilities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("isProUser", () => {
    it("should return false when user is not authenticated", async () => {
      vi.mocked(auth).mockResolvedValue(null);

      const result = await isProUser();

      expect(result).toBe(false);
    });

    it("should return true when user has PRO role", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.PRO },
      } as any);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: "user-1",
        role: UserRole.PRO,
        subscriptionStatus: null,
        subscriptionEnd: null,
      } as any);

      const result = await isProUser();

      expect(result).toBe(true);
    });

    it("should return true when user has ADMIN role", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.ADMIN },
      } as any);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: "user-1",
        role: UserRole.ADMIN,
        subscriptionStatus: null,
        subscriptionEnd: null,
      } as any);

      const result = await isProUser();

      expect(result).toBe(true);
    });

    it("should return true when user has active subscription", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 30);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
        subscriptionStatus: SubscriptionStatus.ACTIVE,
        subscriptionEnd: futureDate,
      } as any);

      const result = await isProUser();

      expect(result).toBe(true);
    });

    it("should return false when subscription has expired", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 1);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
        subscriptionStatus: SubscriptionStatus.ACTIVE,
        subscriptionEnd: pastDate,
      } as any);

      const result = await isProUser();

      expect(result).toBe(false);
    });

    it("should return false when user does not exist", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      vi.mocked(prisma.user.findUnique).mockResolvedValue(null);

      const result = await isProUser();

      expect(result).toBe(false);
    });
  });

  describe("hasRole", () => {
    it("should return true when user has the specified role", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.PRO },
      } as any);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: "user-1",
        role: UserRole.PRO,
      } as any);

      const result = await hasRole(UserRole.PRO);

      expect(result).toBe(true);
    });

    it("should return false when user does not have the specified role", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
      } as any);

      const result = await hasRole(UserRole.PRO);

      expect(result).toBe(false);
    });

    it("should return false when user is not authenticated", async () => {
      vi.mocked(auth).mockResolvedValue(null);

      const result = await hasRole(UserRole.PRO);

      expect(result).toBe(false);
    });
  });

  describe("getUserRole", () => {
    it("should return user role when authenticated", async () => {
      vi.mocked(auth).mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.PRO },
      } as any);

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: "user-1",
        role: UserRole.PRO,
      } as any);

      const result = await getUserRole();

      expect(result).toBe(UserRole.PRO);
    });

    it("should return null when user is not authenticated", async () => {
      vi.mocked(auth).mockResolvedValue(null);

      const result = await getUserRole();

      expect(result).toBe(null);
    });
  });
});
