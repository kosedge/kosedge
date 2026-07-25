// apps/web/lib/security/rate-limit.ts
import { NextRequest, NextResponse } from "next/server";
import { RateLimiterMemory, RateLimiterRedis } from "rate-limiter-flexible";
import { getRedisClient } from "@/lib/cache/redis";

type Limiter = { consume(key: string): Promise<unknown> };

const POINTS = { api: 100, authRead: 60, authWrite: 5, strict: 10 } as const;

// In-memory limiters (used when REDIS_URL is not set or Redis unavailable)
const apiLimiterMemory = new RateLimiterMemory({
  points: POINTS.api,
  duration: 60,
});
const authLimiterMemory = new RateLimiterMemory({
  points: POINTS.authRead,
  duration: 60,
});
const authWriteLimiterMemory = new RateLimiterMemory({
  points: POINTS.authWrite,
  duration: 60,
});
const strictLimiterMemory = new RateLimiterMemory({
  points: POINTS.strict,
  duration: 60,
});

// Redis-backed limiters (lazy-init when REDIS_URL is set); shared across instances
let redisLimiters: {
  api: Limiter;
  auth: Limiter;
  authWrite: Limiter;
  strict: Limiter;
} | null = null;

function getRedisLimiters(): typeof redisLimiters {
  if (redisLimiters) return redisLimiters;
  const client = getRedisClient();
  if (!client) return null;

  redisLimiters = {
    api: new RateLimiterRedis({
      storeClient: client,
      keyPrefix: "rl:api",
      points: POINTS.api,
      duration: 60,
    }),
    auth: new RateLimiterRedis({
      storeClient: client,
      keyPrefix: "rl:auth",
      points: POINTS.authRead,
      duration: 60,
    }),
    authWrite: new RateLimiterRedis({
      storeClient: client,
      keyPrefix: "rl:auth-write",
      points: POINTS.authWrite,
      duration: 60,
    }),
    strict: new RateLimiterRedis({
      storeClient: client,
      keyPrefix: "rl:strict",
      points: POINTS.strict,
      duration: 60,
    }),
  };
  return redisLimiters;
}

function isAuthWritePath(pathname: string): boolean {
  return (
    pathname === "/api/auth/register" ||
    pathname.startsWith("/api/auth/callback") ||
    pathname.startsWith("/api/auth/signin") ||
    pathname.startsWith("/api/auth/signout")
  );
}

function getLimiterAndPoints(pathname: string): {
  limiter: Limiter;
  points: number;
} {
  const redis = getRedisLimiters();
  if (pathname.startsWith("/api/auth")) {
    if (isAuthWritePath(pathname)) {
      return {
        limiter: redis?.authWrite ?? authWriteLimiterMemory,
        points: POINTS.authWrite,
      };
    }
    return {
      limiter: redis?.auth ?? authLimiterMemory,
      points: POINTS.authRead,
    };
  }
  if (pathname.startsWith("/api/edge-board")) {
    return {
      limiter: redis?.strict ?? strictLimiterMemory,
      points: POINTS.strict,
    };
  }
  return { limiter: redis?.api ?? apiLimiterMemory, points: POINTS.api };
}

function getClientId(req: NextRequest): string {
  // Do NOT key by Authorization header: it's user-controlled and easy to rotate/spoof.
  // Prefer proxy-provided client IP, then add user-agent for better cardinality behind NAT.
  const cfIp = req.headers.get("cf-connecting-ip");
  const realIp = req.headers.get("x-real-ip");
  const forwarded = req.headers.get("x-forwarded-for");
  const forwardedIp = forwarded
    ? forwarded
        .split(",")
        .map((x) => x.trim())
        .find(Boolean)
    : undefined;
  const ip = cfIp || realIp || forwardedIp || "unknown";
  const userAgent = req.headers.get("user-agent") || "unknown";
  return `${ip}|${userAgent.slice(0, 120)}`;
}

export async function rateLimit(
  req: NextRequest,
): Promise<NextResponse | null> {
  const { pathname } = req.nextUrl;
  if (!pathname.startsWith("/api/")) return null;

  const clientId = getClientId(req);
  const { limiter, points } = getLimiterAndPoints(pathname);

  try {
    await limiter.consume(clientId);
    return null;
  } catch (rejRes: unknown) {
    const msBeforeNext =
      (rejRes as { msBeforeNext?: number })?.msBeforeNext ?? 60_000;
    const retryAfter = Math.round(msBeforeNext / 1000) || 60;
    return NextResponse.json(
      {
        error: "Too many requests",
        code: "RATE_LIMIT_EXCEEDED",
        retryAfter,
      },
      {
        status: 429,
        headers: {
          "Retry-After": String(retryAfter),
          "X-RateLimit-Limit": String(points),
          "X-RateLimit-Remaining": "0",
          "X-RateLimit-Reset": String(Date.now() + msBeforeNext),
        },
      },
    );
  }
}
