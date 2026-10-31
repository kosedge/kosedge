// apps/web/lib/auth/pro.ts
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/db";
import { UserRole, SubscriptionStatus } from "#prisma";

export type ProAccessState = "authorized" | "unauthenticated" | "forbidden";

/**
 * Opt-in launch override for paid Pro gating. Fail-closed by default.
 *
 * Only the exact server string "true" (after trim, case-insensitive) on
 * OPEN_ACCESS_PREVIEW opens. Unset, invalid, garbage, and aliases
 * (1/yes/y/on/0/false/no/n/off) are closed.
 *
 * NEXT_PUBLIC_OPEN_ACCESS_PREVIEW is UI-only (build-inlined) and must never
 * grant server Pro access. Default is closed.
 */
export function isOpenAccessPreviewEnabled(): boolean {
  const raw = process.env.OPEN_ACCESS_PREVIEW;
  if (typeof raw !== "string") return false;
  return raw.trim().toLowerCase() === "true";
}

/**
 * Check if the current user is a Pro user.
 * Respects OPEN_ACCESS_PREVIEW (launch mode) via getProAccessState().
 *
 * For Insights Pro weekly notes, use isEntitledProUser() instead so
 * production public content is never opened by the preview override.
 */
export async function isProUser(): Promise<boolean> {
  return (await getProAccessState()) === "authorized";
}

/**
 * True Pro entitlement only (role / active subscription).
 * Ignores OPEN_ACCESS_PREVIEW — use for Insights Pro desk notes.
 */
export async function isEntitledProUser(): Promise<boolean> {
  return (await getEntitledProAccessState()) === "authorized";
}

/**
 * Resolve access state for paid Pro surface.
 * - unauthenticated: no signed-in user
 * - forbidden: signed in but not entitled
 * - authorized: PRO/ADMIN role or active subscription
 *
 * When server OPEN_ACCESS_PREVIEW is exactly "true", returns authorized
 * (opt-in launch override). Unset/invalid defaults closed.
 */
export async function getProAccessState(): Promise<ProAccessState> {
  if (isOpenAccessPreviewEnabled()) {
    return "authorized";
  }
  return getEntitledProAccessState();
}

/**
 * Entitlement without open-access preview override.
 * Production Insights gating must call this path.
 */
export async function getEntitledProAccessState(): Promise<ProAccessState> {
  try {
    const session = await auth();
    if (!session?.user?.id) return "unauthenticated";

    const user = await prisma.user.findUnique({
      where: { id: session.user.id },
      select: {
        role: true,
        subscriptionStatus: true,
        subscriptionEnd: true,
      },
    });

    if (!user) return "forbidden";

    if (user.role === UserRole.ADMIN || user.role === UserRole.PRO) {
      return "authorized";
    }

    if (user.subscriptionStatus === SubscriptionStatus.ACTIVE) {
      if (user.subscriptionEnd && user.subscriptionEnd > new Date())
        return "authorized";
    }

    return "forbidden";
  } catch {
    return "forbidden";
  }
}

/**
 * Check if the current user has a specific role.
 * Returns false on DB/auth errors.
 */
export async function hasRole(role: UserRole): Promise<boolean> {
  try {
    const session = await auth();
    if (!session?.user?.id) return false;
    const user = await prisma.user.findUnique({
      where: { id: session.user.id },
      select: { role: true },
    });
    return user?.role === role;
  } catch {
    return false;
  }
}

/**
 * Get the current user's role. Returns null on DB/auth errors.
 */
export async function getUserRole(): Promise<UserRole | null> {
  try {
    const session = await auth();
    if (!session?.user?.id) return null;
    const user = await prisma.user.findUnique({
      where: { id: session.user.id },
      select: { role: true },
    });
    return user?.role ?? null;
  } catch {
    return null;
  }
}
