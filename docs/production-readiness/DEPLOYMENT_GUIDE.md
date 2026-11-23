# JobRadar AI — Production Deployment Guide

**Document Version:** 1.0.0  
**Milestone:** 16 — End-to-End Validation & Deployment Readiness  
**Target Platform:** Linux / macOS / Windows with Docker & Docker Compose  
**Publish Date:** 2026-11-17  

---

## 1. Overview & Architecture

JobRadar AI is architected as a decoupled micro-service platform comprising:
- **`jobradar_frontend`**: Nginx web server hosting compiled React SPA and acting as reverse proxy for local clients.
- **`jobradar_backend`**: Async FastAPI web application serving the REST API.
- **`jobradar_worker`**: Celery worker executing background discovery, semantic analysis, resume tailoring, and email delivery.
- **`jobradar_beat`**: Celery Beat periodic scheduler driving automated job discovery and pipeline runs.
- **`jobradar_postgres`**: PostgreSQL 16 relational database engine.
- **`jobradar_redis`**: Redis 7 cache, distributed lock coordinator, and Celery message broker.
- **`storage_data`**: Shared Docker volume mounting `/app/storage` across backend, worker, and beat containers.

---

## 2. System Requirements

### Hardware Requirements
| Resource | Minimum (Development) | Recommended (Production) |
| :--- | :--- | :--- |
| **CPU** | 2 Cores | 4+ Cores (x86_64 or ARM64) |
| **RAM** | 4 GB | 8 GB+ (16 GB if running local Ollama LLM) |
| **Disk** | 20 GB SSD | 50 GB+ NVMe SSD |

### Software Prerequisites
- Docker Engine 24.0+ and Docker Compose v2.20+
- Host network connectivity to external job boards and SMTP relay
- (Optional) Local Ollama daemon running on host machine (`http://host.docker.internal:11434`)

---

## 3. Production Deployment with Docker Compose

### Step 1: Clone Repository & Prepare Directory
```bash
git clone https://github.com/organization/jobradar-ai.git
cd jobradar-ai
```

### Step 2: Configure Environment Variables
Copy the production template and populate your secure credentials:
```bash
cp .env.example .env
```

Ensure the following critical variables are customized in `.env`:
```ini
# Application Mode
APP_ENV=production
DEBUG=false

# Database Credentials
POSTGRES_USER=jobradar_prod
POSTGRES_PASSWORD=GENERATE_A_SECURE_RANDOM_PASSWORD_HERE
POSTGRES_DB=jobradar_ai

# URLs inside Docker network
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
DATABASE_SYNC_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Email Configuration
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=YOUR_SENDGRID_API_KEY
SMTP_FROM_EMAIL=alerts@yourdomain.com
SMTP_USE_TLS=true
NOTIFICATION_RECIPIENT_EMAIL=you@yourdomain.com

# LLM Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral:7b

# CORS Configuration
CORS_ORIGINS=https://jobradar.yourdomain.com
```

### Step 3: Build & Start Infrastructure (PostgreSQL & Redis)
Start the stateful database and message broker first:
```bash
docker compose up -d postgres redis
```

Verify service health:
```bash
docker compose ps
# Both jobradar_postgres and jobradar_redis should report (healthy)
```

### Step 4: Apply Database Migrations
Run Alembic schema migrations against the running PostgreSQL container:
```bash
docker compose run --rm backend alembic upgrade head
```

Verify the schema is at head (`20261123_0011`):
```bash
docker compose run --rm backend alembic current
```

For an existing deployment, finish queued discovery and tailoring work and stop the API and worker before applying this migration. It closes legacy pending records so they can be retried. If an older container holds resume files under `/storage`, copy those files out before replacing the container and restore them into the shared volume at `/app/storage`.

### Step 5: Launch All Production Services
Launch the complete application suite with the `--profile full` flag:
```bash
docker compose --profile full up -d --build
```

This starts:
1. `jobradar_postgres`
2. `jobradar_redis`
3. `jobradar_backend`
4. `jobradar_worker`
5. `jobradar_beat`
6. `jobradar_frontend`

### Step 6: Verify Deployment Health
Check container status:
```bash
docker compose ps
```

Probe application endpoints:
```bash
# Backend liveness
curl -I http://localhost:8000/health

# Backend dependency readiness (Postgres + Redis)
curl http://localhost:8000/ready

# Frontend web server
curl -I http://localhost:3000/
```

Access the UI at: `http://localhost:3000` (or configured reverse proxy URL).

---

## 4. Volume Architecture & Data Persistence

JobRadar AI uses three persistent named volumes:
1. **`postgres_data`** (`/var/lib/postgresql/data`): All relational tables, candidate profiles, jobs, matches, and audit logs.
2. **`redis_data`** (`/data`): Append-only file (`appendonly yes`) Redis state, protecting task state and locks.
3. **`storage_data`** (`/app/storage`): Shared filesystem volume storing original uploaded master resumes (`/app/storage/resumes/raw/`) and compiled ATS PDF tailored resumes (`/app/storage/resumes/tailored/`).

> [!IMPORTANT]
> The `storage_data` volume is mounted synchronously in `backend`, `worker`, and `beat`. If `backend` uploads a resume, `worker` reads it directly from disk without network file transfers.

---

## 5. Scheduled Automation (Celery Beat)

The `jobradar_beat` container runs the periodic scheduler configured in `app/workers/celery_app.py`:
- **Periodic Job Discovery**: Dispatches `discover_jobs_task` for all active sources every 4 hours.
- **Automated Pipeline Execution**: Evaluates new matches and dispatches downstream tailoring for qualified candidates.
- **Queue Cleanup**: Purges expired temporary artifacts.

To verify beat scheduler logs:
```bash
docker compose logs -f beat
```

---

## 6. Maintenance & Operational Procedures

### Inspecting Service Logs
```bash
# All services
docker compose logs -f

# Specific worker logs
docker compose logs -f worker

# Web API logs
docker compose logs -f backend
```

### Inspecting Celery Task Queues
```bash
# Count pending tasks in discovery queue
docker compose exec redis redis-cli -n 1 LLEN discovery

# Count pending tasks in tailoring queue
docker compose exec redis redis-cli -n 1 LLEN tailoring

# Count pending tasks in notifications queue
docker compose exec redis redis-cli -n 1 LLEN notifications
```

### Graceful Restart
```bash
# Restart background workers without dropping database
docker compose restart worker beat backend
```

### Upgrading Applications
```bash
git pull origin main
docker compose --profile full build
docker compose run --rm backend alembic upgrade head
docker compose --profile full up -d
```

