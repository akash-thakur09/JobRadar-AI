# JobRadar AI — Baseline Audit & Codebase State

**Document Version:** 1.0.0  
**Milestone:** 16 — End-to-End Validation & Deployment Readiness  
**Target Environment:** Local Docker Compose / Self-Hosted Production  
**Audit Date:** 2026-11-17  

---

## 1. Executive Overview

JobRadar AI is an AI-powered job discovery, candidate matching, truthful resume tailoring, and notification platform. Prior to Milestone 16, 15 milestones were completed covering backend foundations, candidate profile management, master resume parsing, multi-source job ingestion, 3-layer matching (deterministic eligibility + weighted scoring + LLM semantic analysis), truth-enforcing resume tailoring with PDF rendering, reliable SMTP email notifications, pipeline orchestration, and a complete React/TypeScript frontend intelligence terminal.

This audit establishes the baseline architectural inventory, dependency status, database schema integrity, test execution baseline, and deployment infrastructure readiness.

---

## 2. Architecture & Technology Stack

```
+---------------------------------------------------------------------------------+
|                                Frontend (SPA)                                   |
|   React 18 + TypeScript + Vite + Tailwind CSS + TanStack Query + Zustand        |
|   Visual Identity: Editorial Terminal (#161616, #FF5A36, #D6FF3F, #8DB4FF)      |
+---------------------------------------+-----------------------------------------+
                                        | HTTP / JSON (REST)
                                        v
+---------------------------------------------------------------------------------+
|                             FastAPI Backend                                     |
|   Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 (Asyncpg / Psycopg)     |
|   RFC 7807 Error Handling + Structlog JSON Logging                              |
+-------+--------------------+---------------------+--------------------+---------+
        |                    |                     |                    |
        v                    v                     v                    v
+---------------+    +---------------+     +---------------+    +-----------------+
|  PostgreSQL   |    | Redis 7 &     |     | Ollama LLM    |    | SMTP Provider   |
|  16 (Async)   |    | Celery Queues |     | (Local/Remote)|    | (Email Delivery)|
+---------------+    +---------------+     +---------------+    +-----------------+
        |                    |
        +---------+----------+
                  v
       +--------------------+
       | Local File Storage |
       | (Volume-Mounted)   |
       +--------------------+
```

### Component Details
| Subsystem | Technology | Responsibility |
| :--- | :--- | :--- |
| **API Server** | FastAPI (uvicorn) | Asynchronous HTTP endpoints, dependency injection, validation |
| **Database** | PostgreSQL 16 | Relational persistence, 15 tables, 30 constraints, partial indices |
| **Async ORM** | SQLAlchemy 2.0 (asyncpg) | Non-blocking database access |
| **Sync DB Client**| Psycopg 3 | Sync sessions for Celery tasks and Alembic migrations |
| **Migrations** | Alembic | Version-controlled schema migrations (`20261104_0001` - `20261105_0010`) |
| **Task Queue** | Celery 5.4 + Redis 7 | Distributed job execution across 4 queues (`discovery`, `processing`, `tailoring`, `notifications`) |
| **Distributed Lock**| Redis (redlock-style) | Single-active-pipeline execution concurrency lock (`jobradar:lock:pipeline:{id}`) |
| **AI Evaluation** | Ollama Provider Abstraction | Semantic match scoring, structured tailoring synthesis |
| **PDF Generation**| WeasyPrint | HTML/CSS to ATS-compliant PDF compilation |
| **Email Delivery**| SMTP Provider Abstraction | MIME multipart email dispatch with tailored PDF attachments |
| **Frontend** | React 18 + Vite | Single-page application, TanStack Query cache, Zustand state |

---

## 3. Database Schema & Migration Inventory

The database contains 15 relational tables managed across 10 sequential Alembic migrations:

| Revision ID | Description | Created Tables / Artifacts |
| :--- | :--- | :--- |
| `20261104_0001` | Candidate Profile & Preferences | `users`, `candidate_profiles`, `candidate_preferences`, `candidate_skills` |
| `20261104_0002` | Master Resume Management | `master_resumes`, `resume_versions` |
| `20261104_0003` | Job Ingestion & Sources | `job_sources`, `job_source_records`, `jobs` |
| `20261104_0004` | Job Matching Foundations | `job_matches` |
| `20261104_0005` | Semantic Match Analysis | `semantic_analyses` |
| `20261104_0006` | Truthful Tailored Resumes | `tailored_resumes` |
| `20261104_0007` | Notification Deliveries | `notification_deliveries` |
| `20261105_0008` | Pipeline Orchestration | `pipeline_runs` |
| `20261105_0009` | Check Constraints & Performance | 30 check constraints, foreign key cascades, partial indexes |
| `20261105_0010` | Concurrency & Idempotency Locks | `uq_pipeline_runs_active_candidate` partial unique index |

### Schema Verification
- **Total Tables:** 15
- **Foreign Key Cascades:** Verified on candidate profiles, master resumes, jobs, matches, tailored resumes, and notifications.
- **Migration Downgrade Reversibility:** Verified via automated test (`test_alembic_clean_migration_and_reversibility`). Downgrade to `base` cleanly drops all tables to 0.

---

## 4. Backend Module & API Inventory

The FastAPI application registers routes under `/api/v1`:

| Route Prefix | Module | Primary Capabilities |
| :--- | :--- | :--- |
| `/candidate` | `app.modules.candidate` | Profile CRUD, skill management, preference configuration |
| `/resumes` | `app.modules.resumes` | Master resume upload, active version toggling, PDF/DOCX parsing |
| `/jobs` | `app.modules.jobs` | Canonical job listings, source tracking, detail retrieval |
| `/matches` | `app.modules.matching` | Evaluated job matches, score breakdowns, eligibility inspection |
| `/tailoring` | `app.modules.tailoring` | Tailored resume generation, diff inspection, PDF download |
| `/notifications` | `app.modules.notifications` | Notification delivery logs, failure inspection, retry dispatch |
| `/pipeline` | `app.modules.pipeline` | Pipeline run triggers, live telemetry, operational run summaries |
| `/health`, `/ready`| `app.main` | System liveness probe and dependency readiness check (DB + Redis) |

---

## 5. Frontend Architecture & Design Compliance

The frontend terminal is built with Vite, TypeScript, and Tailwind CSS following the approved **Career Intelligence Terminal** visual identity:

### Design Tokens & Typography
- **Primary Dark Canvas:** `#161616`
- **Secondary Dark Card:** `#20201F`
- **Elevated Dark Panel:** `#292927`
- **Warm Background:** `#F3EFE7`
- **Primary Action Orange:** `#FF5A36`
- **Opportunity Lime:** `#D6FF3F`
- **AI Intelligence Blue:** `#8DB4FF`
- **Success Green:** `#5BCB8A`
- **Warning Amber:** `#E6B84D`
- **Error Red:** `#E05A47`
- **Typography:** Space Grotesk (headers), Inter (body/data), JetBrains Mono (metrics/code)

### Page & Feature Inventory
1. **Dashboard** (`/`): Aggregate metric cards, quick pipeline trigger, high-match alerts, recent activity stream.
2. **Candidate Profile** (`/candidate`): Personal summary, skills inventory with proficiency tags, granular preference controls.
3. **Job Discovery** (`/jobs`): Searchable job catalog with source badges, workplace filters, and apply links.
4. **Matches** (`/matches`): 3-tier scoring visualization (Skill, Experience, Title, Preference), eligibility flags, semantic breakdown.
5. **Resume Vault** (`/resumes`): Master resume upload, parsing inspection, version timeline, activation toggle.
6. **Tailored Resumes** (`/tailored-resumes`): Target job mapping, side-by-side diff view, truthful audit checks, PDF preview/download.
7. **Notifications** (`/notifications`): Delivery audit history, attempt counts, error inspection, one-click manual retry.
8. **Pipeline Monitoring** (`/pipeline`): Live stage metrics, run lifecycle tracker, error summaries, trigger configuration.

---

## 6. Test Baseline Summary

| Test Domain | Test Framework | Test Files | Total Tests | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Backend Integration** | Pytest + AnyIO | 15 files | 35 tests | **34 Passed, 1 Skipped** |
| **Backend Unit / Suite**| Pytest | 42 files | 350+ tests | **Passed** |
| **Frontend Suites** | Vitest + RTL | 24 files | 120 tests | **120 Passed** |
| **Frontend Build** | TypeScript (`tsc -b`) + Vite | 1 build | Static assets | **0 Errors** |

---

## 7. Known Baseline Gaps & Operational Debt

1. **Authentication Absence:** The backend currently operates without token-based authentication (Bearer JWT or API key). Designed for single-tenant local MVP, but requires an authenticating reverse proxy or VPN boundary for non-local deployment.
2. **SSRF Risk in Discovery:** External job board adapters accept arbitrary `base_url` values without a domain allowlist.
3. **Container Storage Volume:** Initial compose configuration lacked a shared volume between `backend` and `worker` for PDF/resume persistence (addressed in M16).
4. **Scheduler Service:** Celery Beat container was missing in Compose, requiring manual CLI execution for scheduled runs (addressed in M16).

