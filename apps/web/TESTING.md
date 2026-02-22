# Testing Guide

This document explains the testing infrastructure and how to write tests for Kos Edge Analytics.

## Overview

We use **Vitest** as our testing framework, which provides:

- Fast test execution
- Built-in TypeScript support
- Great Next.js integration
- Coverage reporting
- Watch mode for development

We also use **React Testing Library** for component testing, which encourages testing user behavior rather than implementation details.

## Setup

### Install Dependencies

Dependencies are already added to `package.json`. Install them with:

```bash
cd apps/web
pnpm install
```

### Environment Variables

Tests use a separate test database. Set these in your `.env.test` file:

```env
DATABASE_URL="postgresql://user:password@localhost:5432/kosedge_test"
AUTH_SECRET="test-secret-key-at-least-32-characters-long"
MODEL_SERVICE_URL="http://localhost:8000"
NODE_ENV="test"
```

## Running Tests

### Run all tests

```bash
pnpm test
```

### Run tests in watch mode (for development)

```bash
pnpm test:watch
```

### Run tests with UI (interactive)

```bash
pnpm test:ui
```

### Run tests with coverage report

```bash
pnpm test:coverage
```

Coverage reports are generated in `coverage/` directory. Open `coverage/index.html` in your browser to view the report.

## Writing Tests

### Test File Structure

Tests should be placed in `__tests__` directories or have `.test.ts`/`.test.tsx` extensions:

```
apps/web/
├── __tests__/
│   ├── lib/
│   │   └── auth/
│   │       └── pro.test.ts
│   ├── api/
│   │   └── auth/
│   │       └── register.test.ts
│   └── components/
│       └── auth/
│           └── UserMenu.test.tsx
├── lib/
│   └── auth/
│       └── pro.ts
└── app/
    └── api/
        └── auth/
            └── register/
                └── route.ts
```

### Unit Tests

Test utility functions and business logic:

```typescript
// __tests__/lib/auth/pro.test.ts
import { describe, it, expect, vi } from "vitest";
import { isProUser } from "@/lib/auth/pro";

describe("isProUser", () => {
  it("should return false when user is not authenticated", async () => {
    // Mock dependencies
    vi.mocked(auth).mockResolvedValue(null);

    const result = await isProUser();

    expect(result).toBe(false);
  });
});
```

### API Route Tests

Test Next.js API routes:

```typescript
// __tests__/api/auth/register.test.ts
import { POST } from "@/app/api/auth/register/route";

describe("POST /api/auth/register", () => {
  it("should create a new user", async () => {
    const request = new Request("http://localhost/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "test@example.com",
        password: "password123",
      }),
    });

    const response = await POST(request);
    const data = await response.json();

    expect(response.status).toBe(201);
    expect(data.user.email).toBe("test@example.com");
  });
});
```

### Component Tests

Test React components with React Testing Library:

```typescript
// __tests__/components/auth/UserMenu.test.tsx
import { render, screen } from "@/lib/test-utils";
import UserMenu from "@/components/auth/UserMenu";

describe("UserMenu", () => {
  it("should show sign in button when not authenticated", () => {
    render(<UserMenu />);

    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });
});
```

### Using Test Utilities

We provide a custom `render` function in `lib/test-utils.tsx` that includes all necessary providers:

```typescript
import { render, screen } from "@/lib/test-utils";

// Renders with SessionProvider and other providers
render(<MyComponent />, {
  session: {
    user: { id: "1", email: "test@example.com", role: "PRO" },
  },
});
```

## Mocking

### Mocking Next.js Modules

Common Next.js modules are already mocked in `vitest.setup.ts`:

- `next/navigation` (useRouter, usePathname, etc.)
- `next/image`
- `next/link`

### Mocking Prisma

Mock Prisma client for database operations:

```typescript
import { prisma } from "@/lib/db";

vi.mock("@/lib/db");

vi.mocked(prisma.user.findUnique).mockResolvedValue({
  id: "user-1",
  email: "test@example.com",
  role: "USER",
} as any);
```

### Mocking NextAuth

Mock NextAuth session:

```typescript
import { auth } from "@/lib/auth";

vi.mock("@/lib/auth");

vi.mocked(auth).mockResolvedValue({
  user: { id: "1", email: "test@example.com", role: "PRO" },
} as any);
```

## Test Coverage Goals

Aim for:

- **80%+ coverage** for critical business logic (auth, API routes)
- **70%+ coverage** for utility functions
- **60%+ coverage** for components

Focus on testing:

1. ✅ Authentication and authorization logic
2. ✅ API route handlers
3. ✅ Critical business logic
4. ✅ User-facing component behavior
5. ✅ Error handling paths

## Integration Tests

For integration tests that require a real database:

```typescript
import { setupTestDatabase, teardownTestDatabase } from "@/__tests__/setup/db";

describe("User Registration Integration", () => {
  let prisma: PrismaClient;
  let dbName: string;

  beforeAll(async () => {
    const setup = await setupTestDatabase();
    prisma = setup.prisma;
    dbName = setup.dbName;
  });

  afterAll(async () => {
    await prisma.$disconnect();
    await teardownTestDatabase(dbName);
  });

  it("should create user in database", async () => {
    const user = await prisma.user.create({
      data: {
        email: "test@example.com",
        password: "hashed",
      },
    });

    expect(user.email).toBe("test@example.com");
  });
});
```

## Best Practices

1. **Test behavior, not implementation**: Test what users see and do, not internal implementation details.

2. **Use descriptive test names**:

   ```typescript
   // ❌ Bad
   it("works", () => {});

   // ✅ Good
   it("should return false when user is not authenticated", () => {});
   ```

3. **Arrange-Act-Assert pattern**:

   ```typescript
   it("should create user", () => {
     // Arrange
     const email = "test@example.com";

     // Act
     const result = createUser(email);

     // Assert
     expect(result.email).toBe(email);
   });
   ```

4. **Clean up after tests**: Use `beforeEach` and `afterEach` to reset mocks and state.

5. **Mock external dependencies**: Don't make real API calls or database queries in unit tests.

6. **Test error cases**: Don't just test the happy path.

## Debugging Tests

### Run a specific test file

```bash
pnpm test __tests__/lib/auth/pro.test.ts
```

### Run tests matching a pattern

```bash
pnpm test auth
```

### Debug in VS Code

Add this to `.vscode/launch.json`:

```json
{
  "type": "node",
  "request": "launch",
  "name": "Debug Tests",
  "runtimeExecutable": "pnpm",
  "runtimeArgs": ["test", "--run"],
  "console": "integratedTerminal",
  "internalConsoleOptions": "neverOpen"
}
```

## CI/CD Integration

Tests should run automatically in CI. Add to your GitHub Actions workflow:

```yaml
- name: Run tests
  run: pnpm test:coverage

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./apps/web/coverage/coverage-final.json
```

## Troubleshooting

### "Cannot find module" errors

- Ensure `vitest.config.ts` has correct path aliases
- Check that `tsconfig.json` paths match

### Tests timing out

- Increase timeout: `it("test", () => {}, { timeout: 10000 })`
- Check for unclosed database connections

### Mock not working

- Ensure `vi.mock()` is called before imports
- Check that module path matches exactly

### Coverage not showing

- Run `pnpm test:coverage` (not just `pnpm test`)
- Check that files aren't excluded in `vitest.config.ts`

## Next Steps

1. Add E2E tests with Playwright (Recommendation 3)
2. Add performance tests for critical paths
3. Set up test data factories for easier test setup
4. Add visual regression testing for UI components
