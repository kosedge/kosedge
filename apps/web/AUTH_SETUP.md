# Authentication Setup Guide

This document explains the authentication system implemented for Kos Edge Analytics.

## Overview

We've implemented a complete authentication system using **NextAuth.js v5 (Auth.js)** with:

- Email/password authentication (Credentials provider)
- JWT-based sessions
- Role-based access control (USER, PRO, ADMIN)
- Subscription management integration
- Secure password hashing with bcryptjs

## Prerequisites

1. **Install dependencies:**

   ```bash
   cd apps/web
   pnpm install
   ```

2. **Set up environment variables:**
   Add these to your `.env.local` file:

   ```env
   # Required
   DATABASE_URL="postgresql://user:password@localhost:5432/kosedge"
   AUTH_SECRET="your-secret-key-at-least-32-characters-long"
   AUTH_URL="http://localhost:3000"  # Your app URL

   # Optional - for OAuth providers (add as needed)
   # GOOGLE_CLIENT_ID=""
   # GOOGLE_CLIENT_SECRET=""
   # GITHUB_CLIENT_ID=""
   # GITHUB_CLIENT_SECRET=""
   ```

   **Generate AUTH_SECRET:**

   ```bash
   openssl rand -base64 32
   ```

3. **Run database migrations:**
   ```bash
   cd apps/web
   pnpm prisma migrate dev --name add_auth_models
   ```

## Database Schema

The authentication system adds these models to your Prisma schema:

- **User**: Core user model with email, password (hashed), role, and subscription info
- **Account**: OAuth account linking (for future OAuth providers)
- **Session**: Session management (currently using JWT, but schema ready for database sessions)
- **VerificationToken**: Email verification tokens

### User Roles

- `USER`: Standard user (default)
- `PRO`: Pro subscriber with access to premium features
- `ADMIN`: Administrative access

### Subscription Status

- `ACTIVE`: Active subscription
- `CANCELLED`: Subscription cancelled but still valid until end date
- `EXPIRED`: Subscription has expired
- `TRIAL`: Trial period

## Usage

### Sign Up

Users can sign up at `/auth/signup`. The registration process:

1. Validates email format and password (min 8 characters)
2. Checks for existing users
3. Hashes password with bcryptjs
4. Creates user with `USER` role
5. Automatically signs them in

### Sign In

Users sign in at `/auth/signin` with email and password.

### Pro Access

Pro access is determined by:

1. User has `PRO` or `ADMIN` role, OR
2. User has `ACTIVE` subscription status with valid `subscriptionEnd` date

Use the `isProUser()` function to check:

```typescript
import { isProUser } from "@/lib/auth/pro";

if (await isProUser()) {
  // User has Pro access
}
```

### Protected Routes

Routes under `/pro/*` are automatically protected by middleware. Unauthenticated users are redirected to `/auth/signin`.

### Client-Side Session

Use the `useSession` hook in client components:

```typescript
"use client";
import { useSession } from "next-auth/react";

export function MyComponent() {
  const { data: session, status } = useSession();

  if (status === "loading") return <div>Loading...</div>;
  if (!session) return <div>Not signed in</div>;

  return <div>Signed in as {session.user.email}</div>;
}
```

### Server-Side Session

Use the `auth()` function in server components/API routes:

```typescript
import { auth } from "@/lib/auth";

export default async function Page() {
  const session = await auth();

  if (!session) {
    redirect("/auth/signin");
  }

  return <div>Hello {session.user.email}</div>;
}
```

## API Routes

### POST `/api/auth/register`

Register a new user.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe" // optional
}
```

**Response:**

```json
{
  "message": "User created successfully",
  "user": {
    "id": "...",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "USER"
  }
}
```

### GET/POST `/api/auth/[...nextauth]`

NextAuth.js API route handler. Handles all authentication flows.

## Components

### UserMenu

A dropdown menu component showing user info and sign out option:

```typescript
import UserMenu from "@/components/auth/UserMenu";

<UserMenu />
```

## Upgrading Users to Pro

To upgrade a user to Pro status, update their subscription:

```typescript
import { prisma } from "@/lib/db";
import { SubscriptionStatus } from "@prisma/client";

// Option 1: Set role to PRO
await prisma.user.update({
  where: { id: userId },
  data: { role: "PRO" },
});

// Option 2: Set active subscription
await prisma.user.update({
  where: { id: userId },
  data: {
    subscriptionStatus: SubscriptionStatus.ACTIVE,
    subscriptionPlan: "monthly",
    subscriptionStart: new Date(),
    subscriptionEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
  },
});
```

## Security Features

1. **Password Hashing**: All passwords are hashed with bcryptjs (12 rounds)
2. **JWT Sessions**: Secure, stateless sessions
3. **Middleware Protection**: Automatic route protection
4. **Input Validation**: Zod schemas validate all inputs
5. **SQL Injection Protection**: Prisma ORM prevents SQL injection
6. **CSRF Protection**: Built into NextAuth.js

## Next Steps

1. **Add OAuth Providers**: Uncomment and configure Google/GitHub providers in `lib/auth/config.ts`
2. **Email Verification**: Implement email verification flow
3. **Password Reset**: Add password reset functionality
4. **Stripe Integration**: Connect subscription management to Stripe webhooks
5. **Rate Limiting**: Add rate limiting to auth endpoints

## Troubleshooting

### "AUTH_SECRET is not set"

Add `AUTH_SECRET` to your `.env.local` file. Generate one with:

```bash
openssl rand -base64 32
```

### "User already exists"

The email is already registered. Use sign in instead.

### "Invalid email or password"

Check that:

- Email is correct
- Password is correct
- User exists in database

### Database connection errors

Ensure:

- `DATABASE_URL` is set correctly
- Database is running
- Prisma migrations are up to date

## Migration from Cookie-Based Auth

The old cookie-based auth (`kosedge_pro` cookie) has been replaced. All existing code using `isProUser()` now uses the new authentication system.

To migrate existing users:

1. They'll need to sign up with their email
2. You can manually upgrade them to Pro via database or admin panel
3. Or implement a migration script to convert cookie-based users
