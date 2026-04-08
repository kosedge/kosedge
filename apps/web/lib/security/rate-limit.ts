// apps/web/lib/security/rate-limit.ts
import { NextRequest, NextResponse } from "next/server";
import { RateLimiterMemory, RateLimiterRedis } from "rate-limiter-flexible";
import { getRedisClient } from "@/lib/cache/redis";

type Limiter = { consume(key: string): Promise<unknown> };

const POINTS = { api: 100, auth: 5, strict: 10 } as const;

// In-memory limiters (used when REDIS_URL is not set or Redis unavailable)
const apiLimiterMemory = new RateLimiterMemory({
  points: POINTS.api,
  duration: 60,
});
const authLimiterMemory = new RateLimiterMemory({
  points: POINTS.auth,
  duration: 60,
});
const strictLimiterMemory = new RateLimiterMemory({
  points: POINTS.strict,
  duration: 60,
});

// Redis-backed limiters (lazy-init when REDIS_URL is set); shared across instances
let redisLimiters: { api: Limiter; auth: Limiter; strict: Limiter } | null =
  null;

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
      points: POINTS.auth,
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

function getLimiterAndPoints(pathname: string): {
  limiter: Limiter;
  points: number;
} {
  const redis = getRedisLimiters();
  if (pathname.startsWith("/api/auth")) {
    return { limiter: redis?.auth ?? authLimiterMemory, points: POINTS.auth };
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
  const authHeader = req.headers.get("authorization");
  if (authHeader) return authHeader;
  const forwarded = req.headers.get("x-forwarded-for");
  const ip = forwarded
    ? forwarded.split(",")[0]
    : req.headers.get("x-real-ip") || "unknown";
  return ip;
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
