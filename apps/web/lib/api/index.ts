/**
 * API helpers: response shape and error handling.
 * Use these in route handlers for consistent JSON and errors.
 */
export { jsonError, jsonOk, type JsonErrorBody } from "./response";
export { ApiError, handleApiError, withErrorHandler } from "./error-handler";
