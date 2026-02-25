# Kos Edge Analytics - API Documentation

## Base URL

```
Production: https://kosedge.com/api
Development: http://localhost:3000/api
```

## Authentication

Most API endpoints require authentication via NextAuth.js session cookies. Include session cookie in requests.

### Headers

```
Cookie: next-auth.session-token=<token>
```

## Rate Limiting

- **General API**: 100 requests per minute per IP
- **Authentication**: 5 requests per minute per IP
- **Edge Board**: 10 requests per minute per IP

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
Retry-After: 60
```

## Error Responses

All errors follow this format:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

### Error Codes

- `VALIDATION_ERROR` - Input validation failed
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `UNAUTHORIZED` - Authentication required
- `FORBIDDEN` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `INTERNAL_ERROR` - Server error

## Endpoints

### Authentication

#### POST `/api/auth/register`

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "message": "User created successfully",
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "USER"
  }
}
```

**Errors:**
- `400` - Validation error
- `409` - User already exists

---

#### GET/POST `/api/auth/[...nextauth]`

NextAuth.js authentication endpoints. See [NextAuth.js docs](https://next-auth.js.org/getting-started/rest-api).

---

### Edge Board

#### GET `/api/edge-board/ncaam/today`

Get today's NCAAM edge board data.

**Headers:**
```
x-kosedge-secret: <internal-api-secret> (optional)
x-request-id: <uuid> (optional)
```

**Response:** `200 OK`
```json
[
  {
    "id": "game-id",
    "game": "Duke @ UNC",
    "time": "7:00 PM",
    "market": "Spread",
    "open": "-3.5",
    "best": "-4",
    "book": "DK"
  }
]
```

**Errors:**
- `401` - Unauthorized (if secret required)
- `502` - Upstream service error
- `429` - Rate limit exceeded

---

### Health Check

#### GET `/api/ping`

Health check endpoint.

**Response:** `200 OK`
```json
{
  "status": "ok",
  "timestamp": "2025-02-13T12:00:00Z"
}
```

---

## Data Models

### User

```typescript
{
  id: string;
  email: string;
  name: string | null;
  role: "USER" | "PRO" | "ADMIN";
  subscriptionStatus: "ACTIVE" | "CANCELLED" | "EXPIRED" | "TRIAL" | null;
  subscriptionPlan: string | null;
  subscriptionStart: Date | null;
  subscriptionEnd: Date | null;
  createdAt: Date;
  updatedAt: Date;
}
```

### Edge Board Row

```typescript
{
  id?: string;
  game?: string;      // "Duke @ UNC"
  time?: string;      // "7:00 PM"
  market?: string;    // "Spread" | "Total" | "ML"
  open?: string;      // "-3.5" | "145.5"
  best?: string;      // "-4" | "146"
  book?: string;      // "DK" | "FD"
  note?: string;      // Optional tag/status
}
```

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**
- `page` - Page number (default: 1)
- `limit` - Items per page (default: 20, max: 100)

**Response Format:**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5,
    "hasMore": true
  }
}
```

## Webhooks

### Stripe Webhook (Future)

`POST /api/webhooks/stripe`

Handle Stripe subscription events.

**Headers:**
```
stripe-signature: <signature>
```

## SDK Examples

### JavaScript/TypeScript

```typescript
// Register user
const response = await fetch('/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
  }),
});

// Get edge board (with auth)
const edgeBoard = await fetch('/api/edge-board/ncaam/today', {
  headers: {
    'Cookie': `next-auth.session-token=${sessionToken}`,
  },
});
```

### cURL

```bash
# Register
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Get edge board
curl http://localhost:3000/api/edge-board/ncaam/today \
  -H "Cookie: next-auth.session-token=TOKEN"
```

## Versioning

Current API version: `v1` (implicit)

Future versions will use URL versioning: `/api/v2/...`

## Changelog

### v1.0.0 (2025-02-13)
- Initial API release
- Authentication endpoints
- Edge board endpoint
- Health check endpoint
