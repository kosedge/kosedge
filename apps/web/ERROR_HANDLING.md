# Error Handling & Monitoring Guide

This document explains the error handling infrastructure and monitoring setup for Kos Edge Analytics.

## Overview

We've implemented a comprehensive error handling system with:

- **Structured Logging** (Pino) - Fast, structured JSON logging
- **React Error Boundaries** - Catch and handle React component errors gracefully
- **Global Error Handlers** - Next.js error.tsx and global-error.tsx
- **API Error Handling** - Standardized error responses
- **Error Tracking** (Sentry) - Production error monitoring (optional)
- **Custom Error Pages** - 404 and 500 pages matching your design system

## Error Pages

All error pages match your exact design system:

- Dark background (`bg-[#070A0F]`)
- Gold/green accent colors
- Backdrop blur cards
- Same background FX patterns
- Bebas Neue font for headings

### Available Error Pages

1. **404 (Not Found)** - `app/not-found.tsx`
   - Shown when a route doesn't exist
   - Styled to match your design system

2. **500 (Server Error)** - `app/error.tsx`
   - Shown when a page-level error occurs
   - Includes "Try Again" button

3. **Global Error** - `app/global-error.tsx`
   - Catches errors in the root layout
   - Last resort error handler

## Error Boundaries

### Component Error Boundary

Wrap components that might error:

```typescript
import { ErrorBoundary } from "@/components/error/ErrorBoundary";

<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>
```

### Custom Fallback

Provide a custom fallback UI:

```typescript
<ErrorBoundary
  fallback={
    <div>Custom error UI matching your style</div>
  }
>
  <YourComponent />
</ErrorBoundary>
```

## Logging

### Structured Logging with Pino

All logs are structured JSON in production, pretty-printed in development:

```typescript
import { logger, logError, logInfo, logWarn } from "@/lib/logger";

// Log an error
logError(new Error("Something went wrong"), {
  userId: "user-123",
  action: "purchase",
});

// Log info
logInfo("User logged in", { userId: "user-123" });

// Log warning
logWarn("Rate limit approaching", { userId: "user-123" });

// Direct logger access
logger.debug({ data }, "Debug message");
```

### Log Levels

Set log level via `LOG_LEVEL` environment variable:

- `debug` - All logs (development)
- `info` - Info, warnings, errors (default production)
- `warn` - Warnings and errors only
- `error` - Errors only

## API Error Handling

### Standardized Error Responses

Use the error handler utilities:

```typescript
import {
  ApiError,
  handleApiError,
  withErrorHandler,
} from "@/lib/api/error-handler";

// Throw a custom API error
throw new ApiError(404, "User not found", "USER_NOT_FOUND");

// Wrap route handlers
export const GET = withErrorHandler(async (req: Request) => {
  // Your handler code
  // Errors are automatically caught and formatted
});
```

### Error Response Format

All API errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {} // Optional
}
```

### Error Codes

- `VALIDATION_ERROR` - Input validation failed
- `INTERNAL_ERROR` - Server error
- `UNKNOWN_ERROR` - Unknown error type
- Custom codes - Define your own

## Sentry Integration (Optional)

Sentry provides production error tracking and monitoring.

### Setup

1. **Get Sentry DSN** from [sentry.io](https://sentry.io)

2. **Add to environment variables:**

   ```env
   NEXT_PUBLIC_SENTRY_DSN="https://your-dsn@sentry.io/project-id"
   SENTRY_AUTH_TOKEN="your-auth-token" # For source maps
   ```

3. **Configure Sentry** (already set up):
   - `sentry.client.config.ts` - Client-side
   - `sentry.server.config.ts` - Server-side
   - `sentry.edge.config.ts` - Edge runtime

### Manual Error Reporting

```typescript
import * as Sentry from "@sentry/nextjs";

try {
  // Your code
} catch (error) {
  Sentry.captureException(error);
  throw error;
}
```

### User Context

Add user context to Sentry:

```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.setUser({
  id: user.id,
  email: user.email,
});
```

## Best Practices

### 1. Always Log Errors

```typescript
try {
  await riskyOperation();
} catch (error) {
  logError(error as Error, { context: "riskyOperation" });
  // Handle or rethrow
}
```

### 2. Use Appropriate Error Types

- `ApiError` for API route errors
- `ZodError` for validation errors (handled automatically)
- Standard `Error` for unexpected errors

### 3. Don't Expose Internal Details

Error messages in production should be user-friendly:

```typescript
// ❌ Bad
throw new Error("Database connection failed: postgres://...");

// ✅ Good
throw new ApiError(500, "Unable to process request", "DATABASE_ERROR");
```

### 4. Include Context

Always include context when logging:

```typescript
logError(error, {
  userId: user.id,
  endpoint: "/api/edge-board",
  requestId: requestId,
});
```

### 5. Use Error Boundaries Strategically

Wrap:

- ✅ Page-level components
- ✅ Complex feature components
- ❌ Don't wrap every small component

## Monitoring in Production

### Log Aggregation

In production, logs are JSON-structured. Use a log aggregation service:

- **Vercel** - Built-in log viewing
- **Datadog** - Advanced log management
- **CloudWatch** - AWS logging
- **Logtail** - Simple log aggregation

### Error Tracking

Sentry provides:

- Real-time error alerts
- Error grouping and deduplication
- Performance monitoring
- User impact analysis
- Source map support

### Health Checks

Monitor these endpoints:

- `/api/ping` - Basic health check
- Database connection status
- External API availability

## Troubleshooting

### Errors Not Logging

1. Check `LOG_LEVEL` environment variable
2. Verify logger is imported correctly
3. Check console for Pino output

### Sentry Not Capturing Errors

1. Verify `NEXT_PUBLIC_SENTRY_DSN` is set
2. Check Sentry dashboard for project status
3. Verify Sentry config files are in place
4. Check browser console for Sentry initialization

### Error Pages Not Showing

1. Ensure error.tsx files are in correct locations
2. Check that ErrorBoundary is wrapping components
3. Verify error is being thrown (not caught elsewhere)

## Next Steps

1. **Set up Sentry** (optional but recommended for production)
2. **Configure log aggregation** for production
3. **Add custom error codes** for your domain
4. **Set up alerting** for critical errors
5. **Add performance monitoring** for slow requests
