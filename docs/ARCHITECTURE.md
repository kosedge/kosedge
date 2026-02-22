# Kos Edge Analytics - Architecture Documentation

## Overview

Kos Edge Analytics is a modern, enterprise-grade sports betting analytics platform built with Next.js, TypeScript, and PostgreSQL. The platform provides data-driven insights, edge calculations, and premium subscription features.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Web App    │  │  Mobile Web  │  │   API Users  │     │
│  │  (Next.js)   │  │   (PWA)      │  │   (Future)   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────┐
│                    Application Layer                       │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Next.js App Router                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │  │
│  │  │  Pages   │  │   API    │  │  Middle  │         │  │
│  │  │  Routes  │  │  Routes  │  │   ware   │         │  │
│  │  └──────────┘  └──────────┘  └──────────┘         │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Business Logic Layer                    │  │
│  │  • Authentication & Authorization                   │  │
│  │  • Edge Calculations                                │  │
│  │  • Subscription Management                          │  │
│  │  • Data Processing                                  │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────┐
│                      Data Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  PostgreSQL  │  │    Redis     │  │   Prisma     │   │
│  │   (Primary)  │  │   (Cache)    │  │    ORM       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└───────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────┐
│                  External Services                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Model Service│  │  Odds APIs   │  │   Sentry     │   │
│  │  (FastAPI)   │  │  (External)  │  │  (Monitoring)│   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└───────────────────────────────────────────────────────────┘
```

## Technology Stack

### Frontend

- **Framework**: Next.js 16.1.3 (App Router)
- **Language**: TypeScript 5
- **UI**: React 19.2.3
- **Styling**: Tailwind CSS v4
- **State Management**: React Server Components + NextAuth
- **Forms**: React Hook Form + Zod validation

### Backend

- **Runtime**: Node.js 20+
- **API**: Next.js API Routes
- **Authentication**: NextAuth.js v5
- **Database**: PostgreSQL 16
- **ORM**: Prisma 7.3.0
- **Cache**: Redis (ioredis)

### Infrastructure

- **Package Manager**: pnpm 10.29.2
- **Monorepo**: pnpm workspaces
- **CI/CD**: GitHub Actions
- **Testing**: Vitest + React Testing Library
- **Logging**: Pino
- **Error Tracking**: Sentry (optional)
- **Deployment**: Vercel / Docker

## Directory Structure

```
kosedge/
├── apps/
│   ├── web/                    # Next.js frontend application
│   │   ├── app/               # App Router pages and routes
│   │   │   ├── (pro)/        # Pro feature routes
│   │   │   ├── api/          # API routes
│   │   │   └── auth/         # Authentication pages
│   │   ├── components/        # React components
│   │   │   ├── auth/         # Auth components
│   │   │   ├── error/        # Error boundaries
│   │   │   ├── layout/       # Layout components
│   │   │   └── pro/          # Pro feature components
│   │   ├── lib/              # Utility libraries
│   │   │   ├── auth/         # Authentication logic
│   │   │   ├── cache/        # Caching utilities
│   │   │   ├── db/           # Database helpers
│   │   │   ├── security/     # Security utilities
│   │   │   └── api/          # API helpers
│   │   ├── prisma/           # Database schema and migrations
│   │   └── __tests__/        # Test files
│   └── api/                  # Backend services (Python/FastAPI)
├── packages/                 # Shared packages
├── infra/                    # Infrastructure configs
│   └── docker-compose.yml   # Local development services
├── .github/                  # GitHub Actions workflows
└── docs/                     # Documentation
```

## Data Flow

### Authentication Flow

1. User submits credentials → `/api/auth/register` or `/api/auth/[...nextauth]`
2. Credentials validated → Zod schema validation
3. Password hashed → bcryptjs
4. User created/authenticated → Prisma ORM
5. Session created → NextAuth JWT
6. Protected routes accessible → Middleware checks

### Data Fetching Flow

1. Page/Component requests data → Server Component or API Route
2. Check cache → Redis (if available)
3. Cache miss → Query database via Prisma
4. Process data → Business logic
5. Store in cache → Redis (TTL based)
6. Return to client → Serialized JSON

### Edge Board Flow

1. Client requests → `/api/edge-board/ncaam/today`
2. Rate limiting check → Rate limiter middleware
3. Proxy to model service → FastAPI backend
4. Validate response → Zod schema
5. Cache result → Redis (short TTL)
6. Return to client → JSON response

## Security Architecture

### Authentication & Authorization

- **NextAuth.js v5**: JWT-based sessions
- **Role-Based Access Control**: USER, PRO, ADMIN
- **Password Security**: bcryptjs (12 rounds)
- **Session Management**: Secure HTTP-only cookies

### Security Headers

- **CSP**: Content Security Policy
- **HSTS**: HTTP Strict Transport Security
- **X-Frame-Options**: Prevent clickjacking
- **X-Content-Type-Options**: Prevent MIME sniffing

### Rate Limiting

- **API Routes**: 100 requests/minute
- **Auth Routes**: 5 requests/minute
- **Edge Board**: 10 requests/minute
- **IP-based**: Fallback to user-based when authenticated

### Input Validation

- **Zod Schemas**: Type-safe validation
- **HTML Sanitization**: DOMPurify
- **SQL Injection Prevention**: Prisma ORM

## Database Schema

### Core Models

- **User**: Authentication and subscription
- **Sport**: Sport namespace (NCAAM, NFL, NBA, MLB)
- **Team**: Teams within sports
- **Game**: Games/matches
- **MarketSnapshot**: Odds data snapshots
- **ModelProjection**: Model predictions
- **Writeup**: Game analysis content

### Relationships

- Sport → Teams (1:many)
- Sport → Games (1:many)
- Team → Games (many:many via home/away)
- Game → MarketSnapshot (1:1)
- Game → ModelProjection (1:1)
- Game → Writeup (1:1)

## Caching Strategy

### Redis Cache

- **TTL-based**: Most data cached with expiration
- **Invalidation**: Pattern-based cache clearing
- **Fallback**: Direct database query if Redis unavailable

### Cache Keys

- `edge-board:ncaam:today` - Today's edge board
- `user:{id}:session` - User session data
- `game:{id}:market` - Game market data

## Performance Optimizations

### Database

- **Connection Pooling**: Prisma connection management
- **Indexes**: Strategic indexes on frequently queried fields
- **Query Optimization**: Batch queries, pagination

### Frontend

- **Server Components**: Reduce client-side JavaScript
- **Image Optimization**: Next.js Image component
- **Code Splitting**: Automatic route-based splitting
- **Static Generation**: ISR for public content

### API

- **Response Caching**: Redis for API responses
- **Request Deduplication**: Automatic in Next.js
- **Compression**: gzip/brotli via Next.js

## Deployment Architecture

### Development

- **Local**: Docker Compose (PostgreSQL, Redis)
- **Hot Reload**: Next.js dev server
- **Database**: Local PostgreSQL instance

### Production

- **Hosting**: Vercel (recommended) or Docker
- **Database**: Managed PostgreSQL (Supabase, Neon, etc.)
- **Cache**: Managed Redis (Upstash, Redis Cloud)
- **CDN**: Vercel Edge Network
- **Monitoring**: Sentry + Vercel Analytics

## Scalability Considerations

### Horizontal Scaling

- **Stateless**: Next.js app is stateless
- **Database**: Read replicas for read-heavy workloads
- **Cache**: Redis cluster for high availability

### Vertical Scaling

- **Database**: Connection pooling limits
- **Memory**: Redis memory management
- **CPU**: Next.js serverless functions auto-scale

## Monitoring & Observability

### Logging

- **Structured Logging**: Pino (JSON in production)
- **Log Levels**: debug, info, warn, error
- **Context**: Request IDs, user IDs, timestamps

### Error Tracking

- **Sentry**: Production error tracking
- **Error Boundaries**: React error boundaries
- **API Error Handling**: Standardized error responses

### Performance Monitoring

- **Performance API**: Browser performance metrics
- **Server Metrics**: Vercel Analytics
- **Database Metrics**: Query performance logging

## Future Enhancements

### Planned Features

- [ ] Read replicas for database
- [ ] GraphQL API layer
- [ ] Real-time updates (WebSockets)
- [ ] Advanced caching strategies
- [ ] Multi-region deployment
- [ ] Edge functions for low latency

### Technical Debt

- [ ] Migrate to database sessions (from JWT)
- [ ] Implement OAuth providers
- [ ] Add E2E tests with Playwright
- [ ] Performance testing suite
- [ ] Load testing infrastructure

## Development Workflow

1. **Feature Development**
   - Create feature branch
   - Write tests
   - Implement feature
   - Run CI checks locally

2. **Code Review**
   - Create PR
   - CI runs automatically
   - Code review
   - Merge to develop

3. **Deployment**
   - Merge develop → main
   - CI builds and deploys
   - Monitor deployment
   - Verify in production

## References

- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [NextAuth.js Documentation](https://next-auth.js.org)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
