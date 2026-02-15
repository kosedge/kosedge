# Quick Start Guide

## 🚀 Local Development

### Step 1: Install Dependencies

```bash
# From project root
pnpm install
```

### Step 2: Set Up Environment Variables

```bash
# Copy example file
cp apps/web/.env.example apps/web/.env.local
```

Edit `apps/web/.env.local` with your values:

```env
# Database (use Docker or local PostgreSQL)
DATABASE_URL="postgresql://user:password@localhost:5432/kosedge"

# Generate AUTH_SECRET
# Run: openssl rand -base64 32
AUTH_SECRET="your-generated-secret-here"
AUTH_URL="http://localhost:3000"

# Model Service (if running locally)
MODEL_SERVICE_URL="http://localhost:8000"
INTERNAL_API_SECRET="your-internal-secret-min-16-chars"

# Optional
NODE_ENV="development"
LOG_LEVEL="debug"
```

### Step 3: Start Database (Docker)

```bash
# Start PostgreSQL and Redis
pnpm docker:up

# Or manually:
cd infra
docker compose up -d postgres redis
```

### Step 4: Run Database Migrations

```bash
cd apps/web
pnpm prisma migrate dev
```

### Step 5: Start Development Server

```bash
# From project root
pnpm dev:web:3000

# Or from apps/web directory
cd apps/web
pnpm dev
```

### Step 6: Open Browser

Visit [http://localhost:3000](http://localhost:3000)

🎉 **You're running locally!**

---

## 📤 Deploy to Vercel

### Option 1: Vercel CLI (Recommended)

#### Step 1: Install Vercel CLI

```bash
npm i -g vercel
```

#### Step 2: Login to Vercel

```bash
vercel login
```

#### Step 3: Link Your Project

```bash
# From project root
vercel link
```

This will:
- Ask for your project name
- Link to existing Vercel project OR create new one

#### Step 4: Set Environment Variables

```bash
# Set all required variables
vercel env add DATABASE_URL
vercel env add AUTH_SECRET
vercel env add AUTH_URL
vercel env add MODEL_SERVICE_URL
vercel env add INTERNAL_API_SECRET

# Optional
vercel env add REDIS_URL
vercel env add NEXT_PUBLIC_SENTRY_DSN
```

Or set them in Vercel Dashboard:
1. Go to your project → Settings → Environment Variables
2. Add each variable
3. Select environments (Production, Preview, Development)

#### Step 5: Deploy

```bash
# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

### Option 2: GitHub Integration (Automatic)

#### Step 1: Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

#### Step 2: Import to Vercel

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New Project"
3. Import your GitHub repository
4. Configure project:
   - **Framework Preset**: Next.js
   - **Root Directory**: `apps/web`
   - **Build Command**: `cd ../.. && pnpm build:web`
   - **Install Command**: `pnpm install --frozen-lockfile`
   - **Output Directory**: `.next` (default)

#### Step 3: Set Environment Variables

In Vercel Dashboard → Settings → Environment Variables, add:

```env
DATABASE_URL=postgresql://...
AUTH_SECRET=...
AUTH_URL=https://your-domain.vercel.app
MODEL_SERVICE_URL=https://...
INTERNAL_API_SECRET=...
```

#### Step 4: Deploy

Click "Deploy" - Vercel will automatically:
- Install dependencies
- Build your app
- Deploy to production

**Future pushes to `main` branch will auto-deploy!**

---

## 🔧 Vercel Configuration

Create `vercel.json` in project root (optional):

```json
{
  "buildCommand": "cd ../.. && pnpm build:web",
  "installCommand": "pnpm install --frozen-lockfile",
  "framework": "nextjs",
  "rootDirectory": "apps/web"
}
```

Or configure in Vercel Dashboard → Settings → General.

---

## 🗄️ Database Setup for Production

### Option 1: Vercel Postgres (Easiest)

1. Go to Vercel Dashboard → Storage → Create Database
2. Select "Postgres"
3. Copy connection string
4. Add as `DATABASE_URL` environment variable

### Option 2: External Database (Supabase, Neon, etc.)

1. Create database on your provider
2. Get connection string
3. Add as `DATABASE_URL` in Vercel

### Run Migrations on Production

```bash
# Using Vercel CLI
vercel env pull .env.production
cd apps/web
DATABASE_URL=$(grep DATABASE_URL ../.env.production | cut -d '=' -f2) pnpm prisma migrate deploy

# Or use Vercel's database dashboard to run SQL
```

---

## ✅ Post-Deployment Checklist

- [ ] Environment variables set in Vercel
- [ ] Database migrations run
- [ ] Custom domain configured (optional)
- [ ] SSL certificate active (automatic with Vercel)
- [ ] Health check working: `https://your-domain.vercel.app/api/ping`
- [ ] Authentication working: `https://your-domain.vercel.app/auth/signin`

---

## 🐛 Troubleshooting

### Local Issues

**Port already in use:**
```bash
pnpm kill:ports
```

**Database connection error:**
```bash
# Check if Docker is running
pnpm docker:ps

# Restart database
pnpm docker:down
pnpm docker:up
```

**Prisma errors:**
```bash
cd apps/web
pnpm prisma generate
pnpm prisma migrate dev
```

### Vercel Issues

**Build fails:**
- Check build logs in Vercel Dashboard
- Verify `rootDirectory` is set to `apps/web`
- Check `buildCommand` includes `cd ../.. &&`

**Environment variables not working:**
- Verify variables are set for correct environment (Production/Preview)
- Redeploy after adding variables
- Check variable names match exactly

**Database connection:**
- Verify `DATABASE_URL` is correct
- Check database allows Vercel IPs (if using external DB)
- Run migrations: `vercel env pull` then run migrations locally with production URL

---

## 📚 Next Steps

1. **Set up monitoring**: Add Sentry DSN to environment variables
2. **Configure domain**: Add custom domain in Vercel Dashboard
3. **Set up backups**: Configure database backups
4. **Monitor performance**: Check Vercel Analytics

---

## 🆘 Need Help?

- Check [DEPLOYMENT.md](./docs/DEPLOYMENT.md) for detailed deployment guide
- Check [ARCHITECTURE.md](./docs/docs/ARCHITECTURE.md) for system overview
- Vercel Docs: https://vercel.com/docs
- Next.js Docs: https://nextjs.org/docs
