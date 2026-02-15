// apps/web/lib/security/rate-limit.ts
import { NextRequest, NextResponse } from "next/server";
import { RateLimiterMemory } from "rate-limiter-flexible";

// Create rate limiters for different endpoints
const apiLimiter = new RateLimiterMemory({
  points: 100, // Number of requests
  duration: 60, // Per 60 seconds
});

const authLimiter = new RateLimiterMemory({
  points: 5, // Number of requests
  duration: 60, // Per 60 seconds
});

const strictLimiter = new RateLimiterMemory({
  points: 10, // Number of requests
  duration: 60, // Per 60 seconds
});

function getClientId(req: NextRequest): string {
  // Try to get user ID from auth session
  const authHeader = req.headers.get("authorization");
  if (authHeader) {
    return authHeader;
  }

  // Fall back to IP address
  const forwarded = req.headers.get("x-forwarded-for");
  const ip = forwarded ? forwarded.split(",")[0] : req.headers.get("x-real-ip") || "unknown";
  return ip;
}

export async function rateLimit(req: NextRequest): Promise<NextResponse | null> {
  const { pathname } = req.nextUrl;
  const clientId = getClientId(req);

  let limiter: RateLimiterMemory;

  // Choose limiter based on endpoint
  if (pathname.startsWith("/api/auth")) {
    limiter = authLimiter;
  } else if (pathname.startsWith("/api/edge-board")) {
    limiter = strictLimiter;
  } else if (pathname.startsWith("/api/")) {
    limiter = apiLimiter;
  } else {
    return null; // No rate limiting for non-API routes
  }

  try {
    await limiter.consume(clientId);
    return null; // Allow request
  } catch (rejRes: any) {
    // Rate limit exceeded
    const retryAfter = Math.round(rejRes.msBeforeNext / 1000) || 60;
    
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
          "X-RateLimit-Limit": String(limiter.points),
          "X-RateLimit-Remaining": "0",
          "X-RateLimit-Reset": String(Date.now() + rejRes.msBeforeNext),
        },
      }
    );
  }
}
