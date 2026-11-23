# JobRadar AI — Environment Variables & Configuration Reference

**Document Version:** 1.0.0  
**Milestone:** 16 — End-to-End Validation & Deployment Readiness  
**Target:** Backend Configuration (`app.core.config.Settings`) & Docker Compose  
**Date:** 2026-11-17  

---

## 1. Overview

All configuration parameters in JobRadar AI are managed using Pydantic v2 `BaseSettings` (`app/core/config.py`). Variables are read from the execution environment or from a local `.env` file. Type conversion, default fallbacks, and validation occur at application startup.

---

## 2. Configuration Parameters

### 2.1. Core Application
| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `APP_ENV` | String | `development` | Deployment environment (`development`, `staging`, `production`, `test`). |
| `DEBUG` | Boolean | `false` | Enables verbose debug logging and stack traces. Must be `false` in production. |
| `PROJECT_NAME` | String | `JobRadar AI` | Display name of the application. |
| `API_V1_STR` | String | `/api/v1` | URL routing prefix for all API endpoints. |
| `LOG_LEVEL` | String | `INFO` | Structlog logging threshold (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

### 2.2. Database & Connection Pools
| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | String | `postgresql+asyncpg://postgres:postgres@localhost:5432/jobradar_ai` | Async SQLAlchemy database connection string used by FastAPI web app. |
| `DATABASE_SYNC_URL` | String | `postgresql+psycopg://postgres:postgres@localhost:5432/jobradar_ai` | Synchronous database connection string used by Alembic and sync workers. |
| `POSTGRES_USER` | String | `postgres` | PostgreSQL username (used by Docker Compose). |
| `POSTGRES_PASSWORD` | String | `postgres` | PostgreSQL password (used by Docker Compose). |
| `POSTGRES_DB` | String | `jobradar_ai` | Primary database name. |
| `POSTGRES_PORT` | Integer | `5432` | Exposed PostgreSQL port on host. |
| `DB_POOL_SIZE` | Integer | `20` | Maximum persistent connections per process connection pool. |
| `DB_MAX_OVERFLOW` | Integer | `10` | Maximum temporary overflow connections above `DB_POOL_SIZE`. |
| `DB_POOL_TIMEOUT` | Integer | `30` | Seconds to wait before raising connection pool timeout error. |

### 2.3. Redis & Celery Task Queue
| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `REDIS_URL` | String | `redis://localhost:6379/0` | Primary Redis connection string for caching and distributed locks. |
| `REDIS_PORT` | Integer | `6379` | Exposed Redis port on host. |
| `CELERY_BROKER_URL` | String | `redis://localhost:6379/1` | Celery message broker queue database (DB 1). |
| `CELERY_RESULT_BACKEND` | String | `redis://localhost:6379/2` | Celery task result backend database (DB 2). |

### 2.4. File Storage Subsystem
| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `STORAGE_BACKEND` | String | `local` | Storage driver (`local` or `s3`). |
| `STORAGE_DIR` | String | `storage` | Root directory for uploads, generated files, and saved operator settings. Compose mounts the shared volume at `/app/storage`. |
| `MAX_UPLOAD_SIZE_BYTES` | Integer | `10485760` (10 MB) | Maximum permitted size for uploaded resume files. |

### 2.5. AI & Large Language Model (LLM)
| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `LLM_PROVIDER` | String | `ollama` | Provider backend (`ollama` or `mock`). |
| `OLLAMA_BASE_URL` | String | `http://localhost:11434` | Network address of the running Ollama API daemon. |
| `OLLAMA_MODEL` | String | `llama3.1:8b` | Installed model used for semantic matching and tailoring. |
| `LLM_TIMEOUT_SECONDS` | Number | `30` | HTTP request timeout for LLM inference generation. |
| `LLM_MAX_RETRIES` | Integer | `2` | Maximum retry attempts for transient inference errors. |

### 2.6. Email Delivery & SMTP
| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `EMAIL_PROVIDER` | String | `smtp` | Email delivery adapter (`smtp` or `mock`). |
| `SMTP_HOST` | String | `smtp.gmail.com` | Hostname of SMTP mail relay server. |
| `SMTP_PORT` | Integer | `587` | SMTP relay port. Use the relay's STARTTLS port where required. |
| `SMTP_USERNAME` | String | `""` | SMTP authentication username / account. |
| `SMTP_PASSWORD` | String | `""` | SMTP authentication password / application token. |
| `SMTP_FROM_EMAIL` | String | `noreply@jobradar.ai` | From-address in outbound notification headers. |
| `SMTP_USE_TLS` | Boolean | `true` in Compose | Enable certificate-validated STARTTLS. |
| `NOTIFICATION_RECIPIENT_EMAIL` | String | Empty | Delivery address for the default candidate. Also configurable in Settings. |
| `EMAIL_MAX_RETRIES` | Integer | `3` | Maximum automatic delivery attempts for failed notifications. |
| `EMAIL_BASE_RETRY_DELAY_SECONDS` | Integer | `60` | Base exponential backoff delay for delivery retries. |

### 2.7. Security, Networking & Frontend
| Variable | Type | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `CORS_ORIGINS` | Comma-separated | `http://localhost,http://localhost:3000,http://localhost:5173` | Allowed origins for cross-origin browser requests. |
| `CAREER_PAGE_ALLOWED_HOSTS` | Comma-separated | Empty | Exact public hostnames approved for company career-page discovery. |
| `BACKEND_PORT` | Integer | `8000` | Host port exposed for FastAPI REST API. |
| `FRONTEND_PORT` | Integer | `3000` | Host port exposed for Nginx frontend web server. |
| `VITE_API_BASE_URL` | String | `""` | Optional client-side API base URL override (defaults to relative `/api/v1` via proxy). |

---

## 3. Production `.env` Template Example

```ini
# Core Configuration
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# PostgreSQL Configuration
POSTGRES_USER=jobradar_user
POSTGRES_PASSWORD=UseAStrongRandomPassword123!
POSTGRES_DB=jobradar_ai
DATABASE_URL=postgresql+asyncpg://jobradar_user:UseAStrongRandomPassword123!@postgres:5432/jobradar_ai
DATABASE_SYNC_URL=postgresql+psycopg://jobradar_user:UseAStrongRandomPassword123!@postgres:5432/jobradar_ai

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# File Storage
STORAGE_BACKEND=local
STORAGE_DIR=/app/storage

# Email Service
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=postmaster@mg.jobradar.ai
SMTP_PASSWORD=mailgun_api_secret_token
SMTP_FROM_EMAIL=alerts@jobradar.ai
SMTP_USE_TLS=true
NOTIFICATION_RECIPIENT_EMAIL=you@example.com

# AI Service
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral:7b

# Networking
CORS_ORIGINS=https://jobradar.company.internal
FRONTEND_PORT=3000
BACKEND_PORT=8000
```

