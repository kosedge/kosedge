// apps/web/lib/auth/pro.ts
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/db";
import { UserRole, SubscriptionStatus } from "#prisma";

/**
 * Check if the current user is a Pro user.
 * Pro status is determined by:
 * 1. User has PRO or ADMIN role, OR
 * 2. User has an active subscription
 *
 * On DB/auth errors we return false so the Pro page still renders (pricing view).
 */
export async function isProUser(): Promise<boolean> {
  try {
    const session = await auth();
    if (!session?.user?.id) return false;

    const user = await prisma.user.findUnique({
      where: { id: session.user.id },
      select: {
        role: true,
        subscriptionStatus: true,
        subscriptionEnd: true,
      },
    });

    if (!user) return false;

    if (user.role === UserRole.ADMIN || user.role === UserRole.PRO) return true;

    if (user.subscriptionStatus === SubscriptionStatus.ACTIVE) {
      if (user.subscriptionEnd && user.subscriptionEnd > new Date()) return true;
    }

    return false;
  } catch {
    return false;
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
