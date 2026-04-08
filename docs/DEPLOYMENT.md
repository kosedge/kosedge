# Deployment Guide

## Prerequisites

- Node.js 20+
- pnpm 10.29.2+
- PostgreSQL 16+ (managed or self-hosted)
- Redis (optional, for caching)
- GitHub repository
- Deployment platform account (Vercel recommended)

## Environment Setup

### 1. Environment Variables

Create `.env.production` or set in your hosting platform:

```env
# Required
DATABASE_URL=postgresql://user:password@host:5432/kosedge
AUTH_SECRET=<generate-with-openssl-rand-base64-32>
AUTH_URL=https://yourdomain.com
MODEL_SERVICE_URL=https://api.yourdomain.com
INTERNAL_API_SECRET=<min-16-characters>

# Optional
NODE_ENV=production
LOG_LEVEL=info
REDIS_URL=redis://host:6379
NEXT_PUBLIC_SENTRY_DSN=https://...
SENTRY_AUTH_TOKEN=...
```

### 2. Generate Secrets

```bash
# Generate AUTH_SECRET
openssl rand -base64 32

# Generate INTERNAL_API_SECRET
openssl rand -hex 16
```

## Deployment Options

### Option 1: Vercel (Recommended)

**Advantages:**

- Zero-config Next.js deployment
- Automatic HTTPS
- Edge network CDN
- Serverless functions
- Built-in analytics

**Steps:**

1. **Deploy (no global install needed):**

   ```bash
   cd /path/to/kosedge
   npx vercel
   ```

2. **Or install Vercel CLI:**

   ```bash
   pnpm add -g vercel   # or: npm i -g vercel
   vercel login
   npx vercel --prod
   ```

3. **Vercel Project Settings:**
   - **Root Directory:** `apps/web` (required for monorepo)
   - `vercel.json` lives in `apps/web/`

4. **Set Environment Variables:**
   - Go to Vercel Dashboard → Project → Settings → Environment Variables
   - Add all required variables
   - Redeploy

5. **Configure Custom Domain:**
   - Settings → Domains
   - Add your domain
   - Update DNS records

**Vercel Configuration:** `apps/web/vercel.json` (already in repo):

```json
{
  "buildCommand": "cd ../.. && pnpm build:web",
  "installCommand": "pnpm install --frozen-lockfile",
  "framework": "nextjs",
  "regions": ["iad1"]
}
```

Set **Root Directory** to `apps/web` in Vercel Dashboard → Project Settings → General.

### Option 2: Docker

**Dockerfile:**

```dockerfile
FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@10.29.2 --activate

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build:web

FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public

EXPOSE 3000
ENV PORT 3000
CMD ["node", "apps/web/server.js"]
```

**Build and Run:**

```bash
docker build -t kosedge-web .
docker run -p 3000:3000 --env-file .env.production kosedge-web
```

### Option 3: Self-Hosted (Node.js)

**Steps:**

1. **Build:**

   ```bash
   pnpm build:web
   ```

2. **Start:**

   ```bash
   cd apps/web
   pnpm start
   ```

3. **Use PM2 for process management:**
   ```bash
   pm2 start apps/web/server.js --name kosedge-web
   pm2 save
   pm2 startup
   ```

## Database Setup

### 1. Run Migrations

```bash
cd apps/web
pnpm prisma migrate deploy
```

### 2. Generate Prisma Client

```bash
pnpm prisma generate
```

### 3. Seed Database (Optional)

```bash
pnpm prisma db seed
```

## Post-Deployment Checklist

- [ ] Environment variables set
- [ ] Database migrations run
- [ ] Prisma client generated
- [ ] SSL certificate configured
- [ ] Domain DNS configured
- [ ] Health check endpoint working (`/api/ping`)
- [ ] Authentication working (`/auth/signin`)
- [ ] Error tracking configured (Sentry)
- [ ] Monitoring set up
- [ ] Backup strategy in place

## Monitoring

### Health Checks

Monitor these endpoints:

- `/api/ping` - Basic health check
- Database connection status
- Redis connection (if used)

### Logs

- **Vercel**: Dashboard → Logs
- **Docker**: `docker logs <container>`
- **PM2**: `pm2 logs kosedge-web`

### Error Tracking

Sentry automatically tracks errors. Check Sentry dashboard for:

- Error rates
- Performance issues
- User impact

## Scaling

### Horizontal Scaling

1. **Add More Instances:**
   - Vercel: Automatic
   - Docker: Load balancer + multiple containers
   - Self-hosted: Multiple PM2 instances

2. **Database Read Replicas:**

   ```env
   DATABASE_URL_REPLICA=postgresql://...
   ```

3. **Redis Cluster:**
   ```env
   REDIS_URL=redis://cluster-host:6379
   ```

### Vertical Scaling

- Increase database resources
- Increase Redis memory
- Increase server resources (if self-hosted)

## Backup Strategy

### Database Backups

**Automated (Recommended):**

- Use managed PostgreSQL (Supabase, Neon, etc.)
- They provide automatic backups

**Manual:**

```bash
pg_dump $DATABASE_URL > backup.sql
```

### Application Backups

- Code: Git repository
- Environment variables: Secure storage (1Password, etc.)
- Uploads: S3 or similar

## Rollback Procedure

### Vercel

1. Go to Deployments
2. Find previous working deployment
3. Click "Promote to Production"

### Docker

```bash
docker pull kosedge-web:previous-tag
docker stop kosedge-web
docker run -p 3000:3000 kosedge-web:previous-tag
```

### Self-Hosted

```bash
git checkout previous-commit
pnpm build:web
pm2 restart kosedge-web
```

## Troubleshooting

### Build Failures

1. Check Node.js version (20+)
2. Verify all dependencies installed
3. Check environment variables
4. Review build logs

### Runtime Errors

1. Check application logs
2. Verify database connection
3. Check Redis connection (if used)
4. Review Sentry for errors

### Performance Issues

1. Check database query performance
2. Verify caching is working
3. Review server resources
4. Check CDN configuration

## Security Checklist

- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (Prisma)
- [ ] XSS prevention (DOMPurify)
- [ ] CSRF protection
- [ ] Secrets not in code
- [ ] Database credentials secure
- [ ] Regular security updates

## Support

For deployment issues:

1. Check logs
2. Review documentation
3. Check GitHub Issues
4. Contact support
