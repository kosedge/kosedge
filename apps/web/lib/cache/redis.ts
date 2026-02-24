// apps/web/lib/cache/redis.ts
import Redis from "ioredis";
import { env } from "@/lib/config/env";

let redis: Redis | null = null;

export function getRedisClient(): Redis | null {
  if (redis) {
    return redis;
  }

  // Only initialize if REDIS_URL is provided
  const redisUrl = process.env.REDIS_URL;
  if (!redisUrl) {
    return null; // Redis is optional
  }

  try {
    redis = new Redis(redisUrl, {
      maxRetriesPerRequest: 3,
      enableReadyCheck: true,
      lazyConnect: true,
    });

    redis.on("error", (err) => {
      console.error("Redis error:", err);
    });

    return redis;
  } catch (error) {
    console.error("Failed to initialize Redis:", error);
    return null;
  }
}

export async function getCached<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = 300 // 5 minutes default
): Promise<T> {
  const client = getRedisClient();
  
  if (!client) {
    // Fallback to direct fetch if Redis not available
    return fetcher();
  }

  try {
    // Try to get from cache
    const cached = await client.get(key);
    if (cached) {
      return JSON.parse(cached) as T;
    }

    // Fetch fresh data
    const data = await fetcher();

    // Store in cache
    await client.setex(key, ttl, JSON.stringify(data));

    return data;
  } catch (error) {
    console.error("Cache error:", error);
    // Fallback to direct fetch on error
    return fetcher();
  }
}

export async function invalidateCache(pattern: string): Promise<void> {
  const client = getRedisClient();
  if (!client) return;

  try {
    const keys = await client.keys(pattern);
    if (keys.length > 0) {
      await client.del(...keys);
    }
  } catch (error) {
    console.error("Cache invalidation error:", error);
  }
}

export async function setCache(key: string, value: unknown, ttl: number = 300): Promise<void> {
  const client = getRedisClient();
  if (!client) return;

  try {
    await client.setex(key, ttl, JSON.stringify(value));
  } catch (error) {
    console.error("Cache set error:", error);
  }
}

export async function getCache<T>(key: string): Promise<T | null> {
  const client = getRedisClient();
  if (!client) return null;

  try {
    const cached = await client.get(key);
    return cached ? (JSON.parse(cached) as T) : null;
  } catch (error) {
    console.error("Cache get error:", error);
    return null;
  }
}
