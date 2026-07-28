// apps/web/lib/performance.ts
import { logInfo } from "@/lib/logger";

interface PerformanceMetric {
  name: string;
  duration: number;
  metadata?: Record<string, unknown>;
}

/**
 * Measure execution time of an async function
 */
export async function measurePerformance<T>(
  name: string,
  fn: () => Promise<T>,
  metadata?: Record<string, unknown>,
): Promise<T> {
  const start = performance.now();
  try {
    const result = await fn();
    const duration = performance.now() - start;

    logInfo(`Performance: ${name}`, {
      duration: `${duration.toFixed(2)}ms`,
      ...metadata,
    });

    return result;
  } catch (error) {
    const duration = performance.now() - start;
    logInfo(`Performance: ${name} (failed)`, {
      duration: `${duration.toFixed(2)}ms`,
      error: error instanceof Error ? error.message : String(error),
      ...metadata,
    });
    throw error;
  }
}

/**
 * Measure execution time of a sync function
 */
export function measurePerformanceSync<T>(
  name: string,
  fn: () => T,
  metadata?: Record<string, unknown>,
): T {
  const start = performance.now();
  try {
    const result = fn();
    const duration = performance.now() - start;

    logInfo(`Performance: ${name}`, {
      duration: `${duration.toFixed(2)}ms`,
      ...metadata,
    });

    return result;
  } catch (error) {
    const duration = performance.now() - start;
    logInfo(`Performance: ${name} (failed)`, {
      duration: `${duration.toFixed(2)}ms`,
      error: error instanceof Error ? error.message : String(error),
      ...metadata,
    });
    throw error;
  }
}

/**
 * Create a performance timer
 */
export function createTimer(name: string) {
  const start = performance.now();

  return {
    end: (metadata?: Record<string, unknown>) => {
      const duration = performance.now() - start;
      logInfo(`Performance: ${name}`, {
        duration: `${duration.toFixed(2)}ms`,
        ...metadata,
      });
      return duration;
    },
  };
}
