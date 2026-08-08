// apps/web/lib/auth/pro.ts
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/db";
import { UserRole, SubscriptionStatus } from "#prisma";

export type ProAccessState = "authorized" | "unauthenticated" | "forbidden";

function parseBooleanEnv(value: string | undefined): boolean | null {
  if (!value) return null;
  const token = value.trim().toLowerCase();
  if (["1", "true", "yes", "y", "on"].includes(token)) return true;
  if (["0", "false", "no", "n", "off"].includes(token)) return false;
  return null;
}

/**
 * Temporary launch-mode override for paid gating.
 * Set OPEN_ACCESS_PREVIEW=false (and NEXT_PUBLIC_OPEN_ACCESS_PREVIEW=false)
 * when full paywall enforcement is ready.
 */
export function isOpenAccessPreviewEnabled(): boolean {
  const serverValue = parseBooleanEnv(process.env.OPEN_ACCESS_PREVIEW);
  if (serverValue !== null) return serverValue;
  const publicValue = parseBooleanEnv(
    process.env.NEXT_PUBLIC_OPEN_ACCESS_PREVIEW,
  );
  if (publicValue !== null) return publicValue;
  return true;
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
 * When OPEN_ACCESS_PREVIEW is on, returns authorized (launch mode).
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
