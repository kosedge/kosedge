// apps/web/lib/api/error-handler.ts
import { NextResponse } from "next/server";
import { logError } from "@/lib/logger";
import { ZodError } from "zod";

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public code?: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function handleApiError(error: unknown): NextResponse {
  // Log the error
  if (error instanceof Error) {
    logError(error, {
      apiError: true,
    });
  }

  // Handle known error types
  if (error instanceof ApiError) {
    return NextResponse.json(
      {
        error: error.message,
        code: error.code,
        ...(error.details != null ? { details: error.details } : {}),
      },
      { status: error.statusCode }
    );
  }

  // Handle Zod validation errors
  if (error instanceof ZodError) {
    return NextResponse.json(
      {
        error: "Validation failed",
        code: "VALIDATION_ERROR",
        issues: error.issues,
      },
      { status: 400 }
    );
  }

  // Handle generic errors
  if (error instanceof Error) {
    // Don't expose internal error messages in production
    const isDevelopment = process.env.NODE_ENV === "development";
    return NextResponse.json(
      {
        error: isDevelopment ? error.message : "An internal error occurred",
        code: "INTERNAL_ERROR",
        ...(isDevelopment ? { stack: error.stack } : {}),
      },
      { status: 500 }
    );
  }

  // Handle unknown errors
  return NextResponse.json(
    {
      error: "An unknown error occurred",
      code: "UNKNOWN_ERROR",
    },
    { status: 500 }
  );
}

export function withErrorHandler<T extends (...args: any[]) => Promise<NextResponse>>(
  handler: T
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await handler(...args);
    } catch (error) {
      return handleApiError(error);
    }
  }) as T;
}
