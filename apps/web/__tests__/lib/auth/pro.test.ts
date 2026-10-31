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

const {
  isProUser,
  isEntitledProUser,
  isOpenAccessPreviewEnabled,
  hasRole,
  getUserRole,
  getProAccessState,
  getEntitledProAccessState,
} = await import("@/lib/auth/pro");

type FlagCase = "unset" | "invalid" | "true" | "false";
type RoleCase = "anonymous" | "ordinary-user" | "entitled-user" | "admin";

function applyPreviewFlag(flag: FlagCase) {
  delete process.env.OPEN_ACCESS_PREVIEW;
  delete process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW;
  if (flag === "unset") return;
  if (flag === "invalid") {
    process.env.OPEN_ACCESS_PREVIEW = "maybe";
    return;
  }
  process.env.OPEN_ACCESS_PREVIEW = flag;
}

function mockRole(role: RoleCase) {
  if (role === "anonymous") {
    authMock.mockResolvedValue(null);
    findUniqueMock.mockResolvedValue(null);
    return;
  }

  const dbRole =
    role === "admin"
      ? UserRole.ADMIN
      : role === "entitled-user"
        ? UserRole.PRO
        : UserRole.USER;

  authMock.mockResolvedValue({
    user: { id: "user-1", email: "test@example.com", role: dbRole },
  } as any);

  findUniqueMock.mockResolvedValue({
    id: "user-1",
    role: dbRole,
    subscriptionStatus: null,
    subscriptionEnd: null,
  } as any);
}

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

    it("returns authorized when open-access preview is enabled", async () => {
      process.env.OPEN_ACCESS_PREVIEW = "true";
      authMock.mockResolvedValue(null);
      const result = await getProAccessState();
      expect(result).toBe("authorized");
    });
  });

  describe("isOpenAccessPreviewEnabled (A1/A2 fail-closed)", () => {
    it("unset ⇒ false", () => {
      delete process.env.OPEN_ACCESS_PREVIEW;
      delete process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW;
      expect(isOpenAccessPreviewEnabled()).toBe(false);
    });

    it("invalid ⇒ false", () => {
      process.env.OPEN_ACCESS_PREVIEW = "maybe";
      expect(isOpenAccessPreviewEnabled()).toBe(false);
    });

    it("false and closed aliases ⇒ false", () => {
      for (const value of [
        "false",
        "FALSE",
        "0",
        "no",
        "n",
        "off",
        "  false  ",
      ]) {
        process.env.OPEN_ACCESS_PREVIEW = value;
        expect(isOpenAccessPreviewEnabled()).toBe(false);
      }
    });

    it("open aliases (1/yes/y/on) are invalid ⇒ false", () => {
      for (const value of ["1", "yes", "y", "on", "YES", "On"]) {
        process.env.OPEN_ACCESS_PREVIEW = value;
        expect(isOpenAccessPreviewEnabled()).toBe(false);
      }
    });

    it("only exact server true (trim, case-insensitive) ⇒ true", () => {
      for (const value of ["true", "TRUE", "True", " true ", "\ttrue\n"]) {
        process.env.OPEN_ACCESS_PREVIEW = value;
        expect(isOpenAccessPreviewEnabled()).toBe(true);
      }
    });

    it("NEXT_PUBLIC_OPEN_ACCESS_PREVIEW does not grant server Pro access", () => {
      delete process.env.OPEN_ACCESS_PREVIEW;
      process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW = "true";
      expect(isOpenAccessPreviewEnabled()).toBe(false);
    });

    it("NEXT_PUBLIC true does not override a closed server flag", () => {
      process.env.OPEN_ACCESS_PREVIEW = "false";
      process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW = "true";
      expect(isOpenAccessPreviewEnabled()).toBe(false);
    });
  });

  describe("ACCESS_MATRIX_G1 §4b 4×4 (getProAccessState + isEntitledProUser)", () => {
    const flags: FlagCase[] = ["unset", "invalid", "true", "false"];
    const roles: RoleCase[] = [
      "anonymous",
      "ordinary-user",
      "entitled-user",
      "admin",
    ];
    const expectedPro: Record<RoleCase, Record<FlagCase, string>> = {
      anonymous: {
        unset: "unauthenticated",
        invalid: "unauthenticated",
        true: "authorized",
        false: "unauthenticated",
      },
      "ordinary-user": {
        unset: "forbidden",
        invalid: "forbidden",
        true: "authorized",
        false: "forbidden",
      },
      "entitled-user": {
        unset: "authorized",
        invalid: "authorized",
        true: "authorized",
        false: "authorized",
      },
      admin: {
        unset: "authorized",
        invalid: "authorized",
        true: "authorized",
        false: "authorized",
      },
    };
    const expectedEntitled: Record<RoleCase, boolean> = {
      anonymous: false,
      "ordinary-user": false,
      "entitled-user": true,
      admin: true,
    };

    for (const role of roles) {
      for (const flag of flags) {
        it(`${role} × ${flag}`, async () => {
          applyPreviewFlag(flag);
          mockRole(role);
          expect(await getProAccessState()).toBe(expectedPro[role][flag]);
          expect(await isEntitledProUser()).toBe(expectedEntitled[role]);
          expect(await getEntitledProAccessState()).toBe(
            role === "anonymous"
              ? "unauthenticated"
              : expectedEntitled[role]
                ? "authorized"
                : "forbidden",
          );
        });
      }
    }

    it("NEXT_PUBLIC=true with server unset does not authorize anonymous", async () => {
      delete process.env.OPEN_ACCESS_PREVIEW;
      process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW = "true";
      mockRole("anonymous");
      expect(await getProAccessState()).toBe("unauthenticated");
      expect(await isEntitledProUser()).toBe(false);
    });
  });

  describe("isEntitledProUser / getEntitledProAccessState", () => {
    it("ignores OPEN_ACCESS_PREVIEW for anonymous users", async () => {
      process.env.OPEN_ACCESS_PREVIEW = "true";
      process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW = "true";
      authMock.mockResolvedValue(null);

      expect(await getEntitledProAccessState()).toBe("unauthenticated");
      expect(await isEntitledProUser()).toBe(false);
      // Preview override still opens general Pro surfaces.
      expect(await isProUser()).toBe(true);
    });

    it("returns true for entitled PRO role even when preview is off", async () => {
      process.env.OPEN_ACCESS_PREVIEW = "false";
      authMock.mockResolvedValue({
        user: { id: "user-1", email: "pro@example.com", role: UserRole.PRO },
      } as any);
      findUniqueMock.mockResolvedValue({
        id: "user-1",
        role: UserRole.PRO,
        subscriptionStatus: null,
        subscriptionEnd: null,
      } as any);

      expect(await isEntitledProUser()).toBe(true);
    });
  });
});
