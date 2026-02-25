// apps/web/lib/logger.ts
import pino from "pino";

const isDevelopment = process.env.NODE_ENV === "development";

export const logger = pino({
  level: process.env.LOG_LEVEL || (isDevelopment ? "debug" : "info"),
  transport: isDevelopment
    ? {
        target: "pino-pretty",
        options: {
          colorize: true,
          translateTime: "HH:MM:ss Z",
          ignore: "pid,hostname",
        },
      }
    : undefined,
  formatters: {
    level: (label) => {
      return { level: label.toUpperCase() };
    },
  },
  base: {
    env: process.env.NODE_ENV,
  },
});

// Helper functions for structured logging
export const logError = (error: Error, context?: Record<string, unknown>) => {
  logger.error(
    {
      err: {
        message: error.message,
        stack: error.stack,
        name: error.name,
      },
      ...context,
    },
    error.message
  );
};

export const logInfo = (message: string, context?: Record<string, unknown>) => {
  logger.info(context, message);
};

export const logWarn = (message: string, context?: Record<string, unknown>) => {
  logger.warn(context, message);
};

export const logDebug = (message: string, context?: Record<string, unknown>) => {
  logger.debug(context, message);
};
