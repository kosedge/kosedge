// apps/web/__tests__/lib/auth/pro.test.ts
import { describe, it, expect, vi, beforeEach, afterAll } from "vitest";
import { UserRole, SubscriptionStatus } from "#prisma";

// Mock dependencies
const authMock = vi.fn();
const findUniqueMock = vi.fn();

vi.mock("@/lib/auth", () => ({
  auth: authMock,
}));

vi.mock("@/lib/db", () => ({
  prisma: {
    user: {
      findUnique: findUniqueMock,
    },
  },
}));

const { isProUser, hasRole, getUserRole, getProAccessState } =
  await import("@/lib/auth/pro");

describe("Auth Pro Utilities", () => {
  const originalOpenAccessPreview = process.env.OPEN_ACCESS_PREVIEW;
  const originalPublicOpenAccessPreview =
    process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW;

  beforeEach(() => {
    vi.clearAllMocks();
    process.env.OPEN_ACCESS_PREVIEW = "false";
    process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW = "false";
  });

  afterAll(() => {
    if (originalOpenAccessPreview === undefined) {
      delete process.env.OPEN_ACCESS_PREVIEW;
    } else {
      process.env.OPEN_ACCESS_PREVIEW = originalOpenAccessPreview;
    }

    if (originalPublicOpenAccessPreview === undefined) {
      delete process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW;
    } else {
      process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW =
        originalPublicOpenAccessPreview;
    }
  });

  describe("isProUser", () => {
    it("should return false when user is not authenticated", async () => {
      authMock.mockResolvedValue(null);

      const result = await isProUser();

      expect(result).toBe(false);
    });

    it("should return true when user has PRO role", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.PRO },
      } as any);

      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.PRO,
        subscriptionStatus: null,
        subscriptionEnd: null,
      } as any);

      const result = await isProUser();

      expect(result).toBe(true);
    });

    it("should return true when user has ADMIN role", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.ADMIN },
      } as any);

      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.ADMIN,
        subscriptionStatus: null,
        subscriptionEnd: null,
      } as any);

      const result = await isProUser();

      expect(result).toBe(true);
    });

    it("should return true when user has active subscription", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 30);

      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
        subscriptionStatus: SubscriptionStatus.ACTIVE,
        subscriptionEnd: futureDate,
      } as any);

      const result = await isProUser();

      expect(result).toBe(true);
    });

    it("should return false when subscription has expired", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      const pastDate = new Date();
      pastDate.setDate(pastDate.getDate() - 1);

      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
        subscriptionStatus: SubscriptionStatus.ACTIVE,
        subscriptionEnd: pastDate,
      } as any);

      const result = await isProUser();

      expect(result).toBe(false);
    });

    it("should return false when user does not exist", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      findUniqueMock.mockResolvedValue(null);

      const result = await isProUser();

      expect(result).toBe(false);
    });
  });

  describe("hasRole", () => {
    it("should return true when user has the specified role", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.PRO },
      } as any);

      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.PRO,
      } as any);

      const result = await hasRole(UserRole.PRO);

      expect(result).toBe(true);
    });

    it("should return false when user does not have the specified role", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);

      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
      } as any);

      const result = await hasRole(UserRole.PRO);

      expect(result).toBe(false);
    });

    it("should return false when user is not authenticated", async () => {
      authMock.mockResolvedValue(null);

      const result = await hasRole(UserRole.PRO);

      expect(result).toBe(false);
    });
  });

  describe("getUserRole", () => {
    it("should return user role when authenticated", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.PRO },
      } as any);

      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.PRO,
      } as any);

      const result = await getUserRole();

      expect(result).toBe(UserRole.PRO);
    });

    it("should return null when user is not authenticated", async () => {
      authMock.mockResolvedValue(null);

      const result = await getUserRole();

      expect(result).toBe(null);
    });
  });

  describe("getProAccessState", () => {
    it("returns unauthenticated when user is not signed in", async () => {
      authMock.mockResolvedValue(null);
      const result = await getProAccessState();
      expect(result).toBe("unauthenticated");
    });

    it("returns authorized for active subscription user", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 7);
      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
        subscriptionStatus: SubscriptionStatus.ACTIVE,
        subscriptionEnd: futureDate,
      } as any);

      const result = await getProAccessState();
      expect(result).toBe("authorized");
    });

    it("returns forbidden for signed-in non-pro user", async () => {
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "test@example.com", role: UserRole.USER },
      } as any);
      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.USER,
        subscriptionStatus: null,
        subscriptionEnd: null,
      } as any);

      const result = await getProAccessState();
      expect(result).toBe("forbidden");
    });
  });
});
