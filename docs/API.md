# API contract

All JSON API routes in `apps/web` follow a single response and error contract for consistency and client predictability.

## Success responses

- Use `jsonOk(data, init?)` from `@/lib/api/response` for 2xx responses.
- Response body is the serialized `data` (e.g. `{ rows: [] }`, `{ ok: true, ts: number }`).

## Error responses

All JSON error responses share the same shape:

- **`error`** (string, required) – Human-readable message. In production, 5xx errors use a generic message; in development, the actual error message may be included.
- **`code`** (string, optional) – Machine-readable code for clients (e.g. `VALIDATION_ERROR`, `INVALID_PARAMS`, `INTERNAL_ERROR`).

Additional fields may appear for specific cases:

- **`issues`** – For Zod validation errors (400), the array of Zod issues.
- **`details`** – For `ApiError` when details were provided.
- **`stack`** – Only in development for 5xx.

Implementation:

- **`lib/api/response.ts`** – `jsonError(status, message, { code })` for explicit error responses.
- **`lib/api/error-handler.ts`** – `handleApiError(error)` and `withErrorHandler(handler)` turn thrown `ApiError`, `ZodError`, and generic errors into the same JSON shape. Use in catch blocks or wrap handlers.

## Logging

- Use `logError(error, { route: "..." })` from `@/lib/logger` instead of `console.error` in API routes so all errors go through the same logger and can be correlated.
