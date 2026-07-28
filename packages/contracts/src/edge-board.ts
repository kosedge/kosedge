import { z } from "zod";

/**
 * Row contract used by the Edge Board UI.
 * Keep this aligned with model-service output.
 */
export const EdgeBoardRowSchema = z
  .object({
    game: z.string().optional(),
    time: z.string().optional(),
    commenceTime: z.string().optional(),

    // These may vary by sport/market; keep permissive but typed
    open: z.string().optional(),
    best: z.string().optional(),
    market: z.string().optional(),
    book: z.string().optional(),

    // Allow additional fields without breaking (enterprise-friendly evolution)
  })
  .passthrough();

export type EdgeBoardRow = z.infer<typeof EdgeBoardRowSchema>;

/**
 * Preferred API response shape (stable + extensible).
 */
export const EdgeBoardResponseSchema = z
  .object({
    rows: z.array(EdgeBoardRowSchema),
    cached: z.boolean().optional(),
    ttl: z.number().optional(),
  })
  .passthrough();

export type EdgeBoardResponse = z.infer<typeof EdgeBoardResponseSchema>;
