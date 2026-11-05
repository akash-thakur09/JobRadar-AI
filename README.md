# JobRadar AI — AI-Powered Job Intelligence Platform

JobRadar AI is an AI-powered job intelligence platform designed to discover jobs from supported sources, evaluate match relevance against a candidate profile, truthfully tailor resumes, compile job-specific PDFs, and deliver immediate email notifications with tailored attachments.

---

## Architecture Overview

- **Architecture:** Modular Monolith + Asynchronous Workers
- **Runtime:** Python 3.12 LTS
- **Framework:** FastAPI (Async REST API with `/api/v1` prefix)
- **Database:** PostgreSQL 16 (ACID durable store, JSONB, Trigram similarity)
- **ORM / Migrations:** SQLAlchemy 2.0 (Async) + Alembic
- **Task Queue & Broker:** Celery 5.4 + Redis 7.2
- **Local LLM Engine:** Ollama (Llama 3.1)
- **Containerization:** Docker Compose (local-first, cloud-ready)

Detailed architecture specifications are located in [`docs/technical-design/`](docs/technical-design/).

---

## Quickstart & Local Development

### 1. Prerequisites

- **Python:** 3.12+
- **Docker & Docker Compose:** Docker Desktop running locally
- **Git**

### 2. Environment Configuration

Copy the example environment template into `.env`:

```bash
cp .env.example .env
```

Review and adjust variables in `.env` if necessary.

### 3. Start Local Infrastructure (PostgreSQL & Redis)

Start the required local backing services using Docker Compose:

```bash
docker compose up -d postgres redis
```

Verify services are healthy:

```bash
docker compose ps
```

### 4. Set Up Python Virtual Environment

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies in editable mode with development tools
pip install -e ".[dev]"
```

### 5. Run Database Migrations

Apply database migrations to PostgreSQL:

```bash
cd backend
alembic upgrade head
```

### 6. Run the FastAPI Application

Start the local development server:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Liveness Endpoint:** [http://localhost:8000/api/v1/health/live](http://localhost:8000/api/v1/health/live)
- **Readiness Endpoint:** [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)

### 7. Run Celery Background Workers & Beat Scheduler

In separate terminals (with virtual environment activated):

```bash
cd backend
# 1. Start Celery worker handling discovery and processing queues
celery -A app.workers.celery_app worker -l INFO -Q discovery,processing,tailoring,notifications

# 2. Start Celery Beat periodic scheduler (polling discovery sources & processing jobs)
celery -A app.workers.celery_app beat -l INFO
```

---

## Candidate Profile & Preferences API Usage

The Candidate module exposes RESTful endpoints under `/api/v1/candidate` to manage candidate identity, job preferences, and verified skills.

### 1. Candidate Profile

- **Get Profile:** `GET /api/v1/candidate/profile`
  ```bash
  curl -s http://localhost:8000/api/v1/candidate/profile
  ```
- **Update Profile:** `PUT /api/v1/candidate/profile`
  ```bash
  curl -X PUT http://localhost:8000/api/v1/candidate/profile \
    -H "Content-Type: application/json" \
    -d '{
      "full_name": "Jane Doe",
      "headline": "Senior Backend Engineer",
      "professional_summary": "Architecting distributed systems and APIs.",
      "total_experience_months": 60,
      "city": "Seattle",
      "country": "USA",
      "work_authorization": "US Citizen"
    }'
  ```

### 2. Candidate Preferences

- **Get Preferences:** `GET /api/v1/candidate/preferences`
  ```bash
  curl -s http://localhost:8000/api/v1/candidate/preferences
  ```
- **Update Preferences:** `PUT /api/v1/candidate/preferences`
  ```bash
  curl -X PUT http://localhost:8000/api/v1/candidate/preferences \
    -H "Content-Type: application/json" \
    -d '{
      "minimum_relevance_score": 75.00,
      "preferred_titles": ["Staff Engineer", "Backend Architect"],
      "preferred_workplace_types": ["REMOTE", "HYBRID"],
      "preferred_locations": ["Seattle", "Remote"],
      "preferred_employment_types": ["FULL_TIME"],
      "max_job_age_days": 14
    }'
  ```

### 3. Candidate Verified Skills

- **List Skills:** `GET /api/v1/candidate/skills`
  ```bash
  curl -s http://localhost:8000/api/v1/candidate/skills
  ```
- **Add Skill (Automatic Normalization & Duplicate Prevention):** `POST /api/v1/candidate/skills`
  ```bash
  curl -X POST http://localhost:8000/api/v1/candidate/skills \
    -H "Content-Type: application/json" \
    -d '{
      "skill_name": "React.js",
      "category": "frontend",
      "experience_months": 36,
      "is_core": true
    }'
  ```
  *(Automatically normalizes `"React.js"` → `"react"` and rejects duplicate registrations with 409 Conflict).*
- **Delete Skill:** `DELETE /api/v1/candidate/skills/{skill_id}`
  ```bash
  curl -X DELETE http://localhost:8000/api/v1/candidate/skills/<UUID>
  ```

---

## Resume Management API Usage

The Resumes module exposes RESTful endpoints under `/api/v1/resumes` for uploading, versioning, activating, and inspecting structured resume content.

### 1. Upload Master Resume
Uploads a PDF or DOCX file (up to 10MB). Enforces file signature (magic bytes) validation, calculates SHA-256 checksum, prevents duplicate uploads, and triggers an asynchronous Celery parsing task.

```bash
curl -X POST http://localhost:8000/api/v1/resumes/upload \
  -F "file=@/path/to/resume.pdf"
```

### 2. List Resumes
Lists all master resumes uploaded by the candidate with pagination envelopes.

```bash
curl -s "http://localhost:8000/api/v1/resumes?page=1&page_size=20"
```

### 3. Get Resume Details
Retrieves master resume metadata, including active version and full version history.

```bash
curl -s http://localhost:8000/api/v1/resumes/<RESUME_UUID>
```

### 4. Activate Resume
Sets the target resume as the active master resume for job matching and tailoring, automatically deactivating any previously active resume.

```bash
curl -X POST http://localhost:8000/api/v1/resumes/<RESUME_UUID>/activate
```

### 5. List Resume Versions
Fetches all parsed versions associated with a master resume.

```bash
curl -s http://localhost:8000/api/v1/resumes/<RESUME_UUID>/versions
```

### 6. Download Original File
Streams the original uploaded PDF or DOCX file directly from local storage with `Content-Disposition` attachment headers.

```bash
curl -OJ http://localhost:8000/api/v1/resumes/<RESUME_UUID>/download
```

### 7. Inspect Structured Resume Content
Retrieves parsed sections (contact info, summary, experience, education, skills, projects, certifications) and layout metadata without LLM inference.

```bash
curl -s http://localhost:8000/api/v1/resumes/<RESUME_UUID>/content
```

---

## Job Discovery Engine API Usage

The Discovery module exposes RESTful endpoints under `/api/v1/discovery` to manage configured ATS job boards, company career portals, and execute background discovery runs.

### 1. Register a Job Source
Registers an external job source (Greenhouse, Lever, or Career Page). Enforces source-specific configuration validation.

```bash
curl -X POST http://localhost:8000/api/v1/discovery/sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Stripe Greenhouse",
    "source_type": "GREENHOUSE",
    "base_url": "https://boards-api.greenhouse.io",
    "is_enabled": true,
    "polling_interval_minutes": 360,
    "configuration": {
      "board_token": "stripe"
    }
  }'
```

### 2. List Registered Sources
```bash
curl -s "http://localhost:8000/api/v1/discovery/sources"
```

### 3. Trigger Discovery Run (Single Source)
Queues an asynchronous Celery task on the `discovery` queue:

```bash
curl -X POST http://localhost:8000/api/v1/discovery/sources/<SOURCE_UUID>/discover
```

### 4. Trigger Discovery Run (All Enabled Sources)
```bash
curl -X POST http://localhost:8000/api/v1/discovery/trigger -H "Content-Type: application/json" -d '{}'
```

### 5. Inspect Discovery Execution Runs
```bash
curl -s "http://localhost:8000/api/v1/discovery/runs?page=1&page_size=20"
```

### 6. Inspect Raw Discovered Job Records
Inspect raw, unadulterated source payloads, URLs, and SHA-256 payload checksums before downstream normalization:

```bash
curl -s "http://localhost:8000/api/v1/discovery/records?page=1&page_size=20"
```

---

## Canonical Jobs & Normalization API Usage

The Jobs module transforms disparate, unformatted job postings discovered by upstream adapters into sanitized, canonical, and deduplicated job opportunities ready for matching.

### Deduplication Architecture (Two-Tier)
1. **Tier 1 (Fast Path):** Compound unique constraint `(job_source_id, external_job_id)` on `job_source_records` prevents redundant ingestion from the same ATS.
2. **Tier 2 (Cross-Source & Cross-Time):** Deterministic SHA-256 identity fingerprint:
   $$\text{canonical\_slug} = \text{normalize\_slug}(\text{company}) : \text{normalize\_slug}(\text{title}) : \text{normalize\_slug}(\text{location}) : \text{workplace\_type}$$
   $$\text{dedup\_fingerprint\_sha256} = \text{SHA-256}(\text{canonical\_slug})$$
   - Corporate suffixes (`Inc`, `Corp`, `LLC`, `Ltd`, `Technologies`, etc.) are stripped.
   - Title abbreviations (`Sr.` $\to$ `senior`, `Jr.` $\to$ `junior`, `SWE` $\to$ `software engineer`, `QA` $\to$ `quality assurance`) are expanded deterministically.
   - Application URLs are sanitized: tracking parameters (`utm_*`, `gh_jid`, `lever-*`, `ref`, `source`, `fbclid`, `token`) are stripped, enforcing `https://` and lowercase domains.
   - HTML descriptions are safely parsed and stripped into clean text without LLMs.

### 1. List Canonical Jobs
Query canonical jobs with fuzzy search across company name and title, workplace type filtering, status filtering, and pagination:

```bash
curl -s "http://localhost:8000/api/v1/jobs?search=Stripe&workplace_type=REMOTE&page=1&page_size=20"
```

### 2. Get Canonical Job Details
Retrieve detailed canonical job opportunity including sanitized description and all linked discovery source records:

```bash
curl -s "http://localhost:8000/api/v1/jobs/<JOB_UUID>"
```

### 3. Get Linked Source Provenance
Inspect all raw postings and discovery timestamps linked to a canonical job:

```bash
curl -s "http://localhost:8000/api/v1/jobs/<JOB_UUID>/sources"
```

### 4. Trigger Batch Processing of Pending Jobs
Manually trigger immediate normalization and canonicalization of all pending raw source records:

```bash
curl -X POST "http://localhost:8000/api/v1/jobs/process-pending?batch_size=100"
```

---

## Candidate Eligibility & Deterministic Job Matching API Usage

The Matching module provides candidate-specific, deterministic intelligence (Layer 1 boolean eligibility gates and Layer 2 weighted relevance scoring) without LLM latency or cost.

### Matching Engine Architecture

```text
Candidate Profile + Preferences + Skills + Experience + Canonical Job
                               ↓
                 Layer 1 — Deterministic Eligibility
        (Freshness, Workplace, Location, Experience + 12mo Buffer,
                Work Authorization, Mandatory Skills)
                               ↓
                       Passes Hard Gates?
                      /                 \
                    NO                  YES
                   /                     \
       Status: ELIGIBILITY_FAILED         Layer 2 — Deterministic Scoring
       Deterministic Score: 0.00          - Skill Coverage: 40 pts
       (Qualification halts)              - Experience Alignment: 20 pts
                                          - Role Title Relevance: 15 pts
                                          - Workplace / Location Match: 15 pts
                                          - Bonus Factors: 10 pts
                                                   ↓
                                        Relevance Score (0 - 100)
                                        ├── Score >= 50.00: is_qualified = True
                                        └── Score < 50.00: is_qualified = False
                                        (Canonical Job.status remains candidate-independent)
```

### 1. List Evaluated Job Matches
Query matches for a candidate sorted by relevance score descending with optional score and eligibility filters:

```bash
curl -s "http://localhost:8000/api/v1/matches?min_score=70.0&eligibility=ELIGIBLE&page=1&page_size=20"
```

### 2. Get Match Details & Line-Item Mathematical Breakdown
Inspect the complete mathematical audit trail, including Layer 1 boolean checks and Layer 2 component point breakdowns:

```bash
curl -s "http://localhost:8000/api/v1/matches/<MATCH_UUID>"
```

### 3. Re-evaluate Match for a Job
Re-run Layer 1 eligibility and Layer 2 scoring on-demand against updated candidate skills or preferences:

```bash
curl -X POST "http://localhost:8000/api/v1/matches/<JOB_UUID>/re-evaluate"
```

---

## Background Processing & Task Architecture

- **Source Adapter Contract:** Abstract `JobSourceAdapter` interface (`GreenhouseAdapter`, `LeverAdapter`, `CareerPageAdapter`) with decoupled HTTP client lifecycle.
- **Idempotent Ingestion:** Compound unique constraint `(job_source_id, external_job_id)` on `job_source_records` prevents redundant row creation. Repeat discoveries update `last_seen_at`; material payload changes compute a new SHA-256 hash and mark records for downstream re-normalization.
- **Asynchronous Task Queue:** `discover_source_jobs_task` executes on Celery queue `discovery` with exponential backoff (30s, 60s, 120s) for retryable network/rate-limit errors, and immediate failure isolation for permanent configuration errors.
- **Deterministic Structural Extraction:** PDF extraction using `pdfplumber`/`pypdf` with scanned/image-only PDF detection; DOCX extraction using `python-docx` for paragraphs, tables, and document metadata.
- **File Storage Security:** Isolated storage abstraction under `backend/storage/resumes/raw/{candidate_profile_id}/{uuid}.{ext}` with strict path traversal prevention.

---

## Quality & Testing Commands

From the `backend` directory:

### Run Tests
```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires docker compose up postgres redis)
pytest tests/integration/

# Run complete test suite with coverage
pytest --cov=app tests/
```

### Code Formatting & Linting
```bash
# Run linter
ruff check .

# Check formatting
ruff format --check .

# Auto-format
ruff format .
```

### Static Type Checking
```bash
# Strict Mypy type validation
mypy app
```

---

## Directory Layout

```text
JobRadar-AI/
├── .env.example                # Global environment template
├── docker-compose.yml          # PostgreSQL 16 & Redis 7 services
├── docs/                       # Product requirements & technical design
│   └── technical-design/       # Implementation-ready technical specifications
└── backend/
    ├── app/
    │   ├── main.py             # FastAPI entry point & lifespan
    │   ├── api/                # API routes, middleware, RFC 7807 error handlers
    │   ├── core/               # Pydantic settings, structured logging, exceptions
    │   ├── database/           # SQLAlchemy async session, base, health checks
    │   ├── infrastructure/     # Redis client, file storage abstraction, reusable HTTP client
    │   ├── workers/            # Celery app, queues, background tasks
    │   └── modules/            # Domain modules
    │       ├── candidate/      # Candidate profile, preferences, skills models & service
    │       ├── resumes/        # Master resumes, versioning, PDF/DOCX deterministic parsers
    │       ├── discovery/      # Job source registry, Greenhouse & Lever adapters, discovery tasks
    │       └── jobs/           # Canonical jobs, normalizers, deduplication, and processing tasks
    │           ├── deduplicator.py   # Deterministic slugs, URL sanitization, HTML cleaning
    │           ├── normalizers/      # Platform-specific normalizers (Greenhouse, Lever)
    │           ├── repository.py     # Canonical job & source record persistence
    │           ├── service.py        # Canonicalization & deduplication orchestrator
    │           └── tasks.py          # Celery processing & periodic scheduler tasks
    ├── storage/                # Local raw resume file storage root (gitignored)
    ├── tests/                  # Pytest unit & integration test suites
    │   ├── unit/               # Unit tests (schemas, service, routes, config, errors)
    │   └── integration/        # Integration tests (PostgreSQL constraints, Redis)
    ├── alembic/                # Async database migrations & version history
    ├── alembic.ini             # Alembic migration configuration
    └── pyproject.toml          # PEP 621 dependencies & tool configurations
```

