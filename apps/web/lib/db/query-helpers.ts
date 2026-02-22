// apps/web/lib/db/query-helpers.ts
import { Prisma } from "#prisma";
import { prisma } from "@/lib/db";
import { getCached } from "@/lib/cache/redis";

/**
 * Pagination helper
 */
export interface PaginationParams {
  page?: number;
  limit?: number;
}

export interface PaginatedResult<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasMore: boolean;
  };
}

export async function paginate<T>(
  model: any,
  args: Prisma.Args<any, "findMany">,
  params: PaginationParams = {}
): Promise<PaginatedResult<T>> {
  const page = Math.max(1, params.page || 1);
  const limit = Math.min(100, Math.max(1, params.limit || 20));
  const skip = (page - 1) * limit;

  const [data, total] = await Promise.all([
    model.findMany({
      ...args,
      skip,
      take: limit,
    }),
    model.count({ where: args.where }),
  ]);

  return {
    data: data as T[],
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
      hasMore: page * limit < total,
    },
  };
}

/**
 * Cached query helper
 */
export async function cachedQuery<T>(
  cacheKey: string,
  query: () => Promise<T>,
  ttl: number = 300
): Promise<T> {
  return getCached(cacheKey, query, ttl);
}

/**
 * Batch query helper for N+1 prevention
 */
export async function batchQuery<T, K>(
  ids: K[],
  fetcher: (ids: K[]) => Promise<T[]>,
  idExtractor: (item: T) => K
): Promise<Map<K, T>> {
  const items = await fetcher(ids);
  const map = new Map<K, T>();
  items.forEach((item) => {
    map.set(idExtractor(item), item);
  });
  return map;
}
