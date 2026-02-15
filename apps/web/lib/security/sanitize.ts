// apps/web/lib/security/sanitize.ts
import DOMPurify from "isomorphic-dompurify";

/**
 * Sanitize HTML content to prevent XSS attacks
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ["b", "i", "em", "strong", "a", "p", "br", "ul", "ol", "li"],
    ALLOWED_ATTR: ["href"],
  });
}

/**
 * Sanitize user input string (remove HTML tags)
 */
export function sanitizeString(input: string): string {
  return DOMPurify.sanitize(input, { ALLOWED_TAGS: [] });
}

/**
 * Validate and sanitize email
 */
export function sanitizeEmail(email: string): string {
  const sanitized = sanitizeString(email).toLowerCase().trim();
  // Basic email validation
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(sanitized)) {
    throw new Error("Invalid email format");
  }
  return sanitized;
}

/**
 * Sanitize URL
 */
export function sanitizeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    // Only allow http and https
    if (!["http:", "https:"].includes(parsed.protocol)) {
      throw new Error("Invalid URL protocol");
    }
    return parsed.toString();
  } catch {
    throw new Error("Invalid URL");
  }
}
