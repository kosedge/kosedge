# Kos Edge Analytics - API Documentation

For deployment (Vercel) see [VERCEL.md](./VERCEL.md).

## Base URL

```
Production: https://www.kosedge.com/api
Development: http://localhost:3000/api
```

## Authentication

Some API endpoints require authentication or an internal secret. Public data routes remain accessible without user auth.

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

### Model Service (NFL)

These routes are served by the model-service deployment.

#### GET `/health/nfl-production-readiness`

NFL go/no-go readiness gate with hard thresholds over the latest quality snapshot.

Policy controls:

- `NFL_READINESS_MODE=production|staging` (production is strict default)
- staging-only freshness overrides:
  - `NFL_READINESS_STAGING_MAX_LAST_GAME_AGE_DAYS=<int>`
  - `NFL_READINESS_STAGING_DISABLE_FRESHNESS_GATE=true`

Readiness payload includes `freshness_policy` for auditability (`mode`, `override_active`, `override_reason`, `freshness_gate_enabled`, `max_last_game_age_days_applied`).

#### GET `/health/nfl-production-readiness/prometheus`

Prometheus-friendly readiness gauge:

- `kosedge_nfl_production_readiness_ok{status,model_version}`

#### POST `/api/jobs/run-nfl-walkforward-backtest`

Enqueue NFL leakage-safe walk-forward backtest.

Eligibility rule:

- fold inputs require `projection_created_at < outcome_completed_at` (strict pre-outcome projection timestamp)
- rows that fail this rule are excluded before fold creation and metric computation

Query params:

- `model_version` (default `nfl-v1.5-matchup-sim`)
- `lookback_days` (default `240`)
- `training_days` (default `56`)
- `step_days` (default `7`)
- `apply_calibration` (default `true`)

Backtest totals calibration:

- each fold trains a bounded linear totals calibrator (`slope`, `intercept`) on the training window only
- fold outputs include `base_mae_total_runs`, `calibrated_mae_total_runs`, and per-fold totals calibration coefficients

#### POST `/api/jobs/backfill-nfl-historical-projections`

Enqueue historical NFL projection backfill with explicit pre-outcome projection timestamps.

Query params:

- `start_date` (`YYYY-MM-DD`, required)
- `end_date` (`YYYY-MM-DD`, required)
- `simulations` (default `4000`)
- `model_version` (default `nfl-v1.5-matchup-sim`)
- `kickoff_buffer_minutes` (default `30`)

Behavior:

- runs simulations for completed games in the date range
- writes `nfl_market_projections.created_at` as kickoff minus buffer (`kickoff - kickoff_buffer_minutes`)
- stores matching timestamp metadata under `projection.audit` for traceability

#### POST `/nfl/simulations/{game_id}`

Run deterministic NFL simulation for one game and persist projection row.

Totals payload notes:

- `markets.total_mean` is the calibrated total expectation used by grading/readiness
- diagnostics now include:
  - `diagnostics.totals_adjustments` (bounded tempo/EPA/success/injury contributors + stdev adjustment)
  - `diagnostics.totals_calibration` (base total, calibrated total, slope/intercept, sample size, source)

#### GET `/nfl/ops/backtest-runs`

Return latest persisted NFL walk-forward run summaries.

#### GET `/nfl/ops/backtest-report`

Return latest NFL walk-forward report with fold-level metrics.

#### GET `/nfl/ops/active-model`

Return current NFL champion runtime model state.

#### GET `/nfl/ops/promotion-events`

List recent NFL promotion decisions and whether auto-promotion occurred.

#### POST `/nfl/ops/evaluate-promotion`

Manually trigger NFL champion/challenger evaluation.

Query params:

- `challenger_model_version` (required)
- `lookback_days` (default `45`)
- `auto_promote` (default `true`)

#### GET `/nfl/edges/today`

Return NFL model signals filtered by quality/confidence gating with diagnostics.

#### GET `/nfl/edges/optimize`

Build deterministic bankroll-aware NFL stake recommendations with correlation/exposure controls.

Supports player-level controls:

- `max_per_player_exposure`
- `same_game_player_penalty`
- `qb_wr_correlation_penalty`

#### GET `/nfl/projections/players`

Return weekly player baseline projections with uncertainty payloads.

Key query params:

- `season` (required)
- `week` (required)
- `model_version` (default `nfl-player-v1`)
- optional filters: `team`, `position`, `limit`

#### GET `/nfl/props/board`

Return player props board with model probabilities, fair prices, and market edges.

Key query params:

- `season` (required)
- `week` (required)
- `model_version` (default `nfl-player-v1`)
- optional filters: `market_key`, `team`, `min_confidence`, `min_abs_edge`, `limit`

#### GET `/nfl/fantasy/rankings`

Return weekly fantasy projections/rankings by scoring profile.

Key query params:

- `season` (required)
- `week` (required)
- `scoring_profile` (`standard|half_ppr|ppr`)
- `model_version` (default `nfl-player-v1`)
- optional filters: `position`, `tier_max`, `limit`

#### GET `/nfl/ops/projections-readiness`

Return latest layer-level audit state for player baseline, props, and fantasy pipelines.

#### POST `/nfl/ops/materialize-player-baselines`

Enqueue player baseline materialization.

#### POST `/nfl/ops/materialize-player-props`

Enqueue player props edge materialization.

#### POST `/nfl/ops/materialize-fantasy`

Enqueue fantasy projection/ranking materialization.

#### POST `/nfl/ops/run-player-cycle`

Enqueue full player pipeline cycle (market pull + baselines + props + fantasy).

#### POST `/api/jobs/evaluate-nfl-promotion`

Enqueue asynchronous NFL promotion evaluation task.

#### POST `/api/jobs/pull-nfl-player-prop-markets`

Enqueue ingestion of player prop market snapshots from Odds API.

#### POST `/api/jobs/run-nfl-player-baselines`

Enqueue baseline player projection materialization.

#### POST `/api/jobs/run-nfl-player-props`

Enqueue player props edge materialization.

#### POST `/api/jobs/run-nfl-fantasy-projections`

Enqueue fantasy ranking/projection materialization.

#### POST `/api/jobs/run-nfl-player-cycle`

Enqueue full player-layer weekly cycle.

#### POST `/api/jobs/run-nfl-identity-refresh`

Enqueue full weekly NFL player identity refresh and reconciliation cycle.

#### POST `/api/jobs/run-nfl-identity-manual-resolutions`

Apply pending manual identity resolution actions (approve/reject workflow execution task).

#### POST `/api/jobs/run-nfl-identity-quality-snapshot`

Compute and persist latest identity SLA snapshot (`coverage`, `unresolved`, `conflict`, `remap`, `freshness`).

#### GET `/nfl/identity/queue`

List unresolved/conflict/manual-review identity queue records with filters (`queue_status`, `reason`, `season`, `week`).

#### POST `/nfl/identity/queue/{queue_id}/action`

Approve or reject one manual mapping action. `approve` requires canonical `player_uid`.

#### POST `/nfl/identity/refresh`

Trigger asynchronous identity refresh for a target season/week/model version.

#### POST `/nfl/identity/manual-reconciliations`

Trigger asynchronous application of pending manual identity resolutions.

#### POST `/nfl/identity/quality-snapshot`

Trigger asynchronous identity quality snapshot computation.

#### GET `/nfl/identity/quality/latest`

Fetch latest persisted identity quality SLA snapshot and readiness classification.

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
const response = await fetch("/api/auth/register", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "user@example.com",
    password: "password123",
  }),
});

// Get edge board (with auth)
const edgeBoard = await fetch("/api/edge-board/ncaam/today", {
  headers: {
    Cookie: `next-auth.session-token=${sessionToken}`,
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
