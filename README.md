# Kos Edge Analytics

Premium sports handicapping insights built on data. Driven by edge.

[![CI](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/ci.yml)
[![CodeQL](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/codeql.yml/badge.svg)](https://github.com/YOUR_USERNAME/kosedge/actions/workflows/codeql.yml)

## 🚀 Quick Start

### Local Development

```bash
# 1. Install dependencies
pnpm install

# 2. Set up environment variables
cp apps/web/.env.example apps/web/.env.local
# Edit .env.local with your configuration

# 3. Start database (Docker)
pnpm docker:up

# 4. Run database migrations
cd apps/web
pnpm prisma migrate dev

# 5. Start development server (from repo root)
pnpm dev:web:3000
```

Visit [http://localhost:3000](http://localhost:3000) to see the application.

**If you see `Cannot find module '.../next/dist/bin/next'`:** do a clean install from the **repository root**: `rm -rf node_modules apps/web/node_modules && pnpm install`. Then run `pnpm dev:web:3000` again. One-shot: `pnpm bootstrap:web` installs and starts the web app.

**📖 See [QUICK_START.md](./QUICK_START.md) for detailed instructions. See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.**

### Deploy to Vercel

**Option 1: Vercel CLI**
```bash
npm i -g vercel
vercel login
vercel link
vercel --prod
```

**Option 2: GitHub Integration**
1. Push to GitHub
2. Import repository in Vercel Dashboard
3. Set environment variables
4. Deploy!

**📖 See [QUICK_START.md](./QUICK_START.md) for complete deployment guide.**

## 📁 Project Structure

```
kosedge/
├── apps/
│   ├── web/              # Next.js frontend application
│   └── api/              # Backend services (Python/FastAPI)
├── packages/             # Shared packages
├── infra/                # Infrastructure (Docker, etc.)
└── .github/             # GitHub Actions workflows
```

## 🛠️ Development

### Available Scripts

```bash
# Development
pnpm dev                  # Start all services
pnpm dev:web              # Start web app only
pnpm dev:web:3000         # Start web app on port 3000

# Building
pnpm build                # Build all packages
pnpm build:web            # Build web app only

# Quality Checks
pnpm lint                 # Lint all packages
pnpm typecheck            # Type check all packages
pnpm test                 # Run all tests
pnpm format               # Format code
pnpm format:check         # Check formatting

# CI Pipeline
pnpm ci                   # Run full CI checks locally
```

### Docker Services

```bash
pnpm docker:up            # Start all Docker services
pnpm docker:down          # Stop all Docker services
pnpm docker:logs          # View Docker logs
```

## 🧪 Testing

```bash
# Run all tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run tests with coverage
pnpm test:coverage

# Run tests with UI
pnpm test:ui
```

See [TESTING.md](./apps/web/TESTING.md) for detailed testing documentation.

## 🔐 Authentication

The application uses NextAuth.js v5 for authentication with:
- Email/password authentication
- JWT-based sessions
- Role-based access control (USER, PRO, ADMIN)
- Subscription management

See [AUTH_SETUP.md](./apps/web/AUTH_SETUP.md) for authentication setup and configuration.

## 🐛 Error Handling

Comprehensive error handling with:
- Structured logging (Pino)
- React error boundaries
- Custom error pages (404, 500)
- API error handling utilities
- Sentry integration (optional)

See [ERROR_HANDLING.md](./apps/web/ERROR_HANDLING.md) for error handling documentation.

## 🚢 Deployment

### CI/CD Pipeline

The project includes GitHub Actions workflows:
- **CI** - Runs on every push/PR (lint, typecheck, test, build)
- **Deploy** - Deploys to production on main branch
- **PR Checks** - Quality checks for pull requests
- **CodeQL** - Security analysis

### Environment Variables

Required environment variables for production:

```env
DATABASE_URL=postgresql://...
AUTH_SECRET=...
MODEL_SERVICE_URL=...
INTERNAL_API_SECRET=...
```

See `apps/web/.env.example` for complete list.

## 📚 Documentation

- [Authentication Setup](./apps/web/AUTH_SETUP.md)
- [Testing Guide](./apps/web/TESTING.md)
- [Error Handling](./apps/web/ERROR_HANDLING.md)
- [CI/CD Guide](./.github/workflows/README.md)

## 🏗️ Architecture

- **Frontend**: Next.js 16 (App Router), React 19, TypeScript
- **Backend**: FastAPI (Python), PostgreSQL, Redis
- **Authentication**: NextAuth.js v5
- **Database**: Prisma ORM
- **Styling**: Tailwind CSS v4
- **Testing**: Vitest, React Testing Library
- **Logging**: Pino
- **Error Tracking**: Sentry (optional)

## 📝 License

Private - All rights reserved

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run `pnpm ci` to ensure all checks pass
4. Submit a pull request

All PRs must pass CI checks before merging.
