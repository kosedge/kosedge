FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# pg_dump must match Railway Postgres major (currently 18.x).
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  bash \
  ca-certificates \
  gnupg \
  && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg \
  && . /etc/os-release \
  && echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
    > /etc/apt/sources.list.d/pgdg.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends postgresql-client-18 \
  && ln -sf /usr/lib/postgresql/18/bin/pg_dump /usr/local/bin/pg_dump \
  && ln -sf /usr/lib/postgresql/18/bin/pg_restore /usr/local/bin/pg_restore \
  && rm -rf /var/lib/apt/lists/*

# Build context = services/model-service via: railway up services/model-service --path-as-root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/scripts/nfl/*.sh 2>/dev/null || true \
  && mkdir -p /app/data/backups/nfl

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# API default PORT 8080 matches Railway public domain. Worker must listen on
# default+odds+models or season 5–10min odds/board jobs never run.
CMD ["sh", "-c", "case \"${PROCESS_TYPE:-api}\" in worker) exec celery -A src.celery_app worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-4} -Q ${CELERY_WORKER_QUEUES:-default,odds,models};; beat) exec celery -A src.celery_app beat --loglevel=info;; *) exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080};; esac"]
