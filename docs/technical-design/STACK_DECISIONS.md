# AI Job Intelligence Platform — Technology Stack Decisions

**Document ID:** TD-001  
**Status:** Approved Technical Design  
**Date:** 2026-11-04  
**Scope:** Core Technology Stack & Architectural Dependencies  

---

# 1. Executive Summary

This document establishes the technology stack for the JobRadar AI platform. JobRadar AI is an AI-powered job intelligence platform designed to discover jobs from supported platforms, normalize and deduplicate them, evaluate match suitability using a hybrid deterministic and LLM-driven engine, generate truthful tailored resumes preserving original formatting or falling back to ATS-friendly templates, and deliver immediate email notifications with tailored PDF attachments.

The platform follows a **modular monolith** backend architecture with **asynchronous background workers**, built on a **local-first, cloud-ready** paradigm. This document details each stack component, evaluating alternatives, trade-offs, MVP suitability, and long-term cloud scalability.

---

# 2. Technology Stack Matrix

| Component | Selected Technology | Version | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.12 LTS | High-performance async runtime, modern typing |
| **API Framework** | FastAPI | 0.115+ | High-throughput asynchronous REST API & OpenAPI docs |
| **Data Validation** | Pydantic | 2.9+ | High-speed Rust-based serialization & schema validation |
| **ORM / Data Access** | SQLAlchemy (Async) | 2.0+ | Typed async relational mapping and query execution |
| **Database Driver** | asyncpg / psycopg3 | 0.29+ / 3.2+ | High-performance async PostgreSQL driver |
| **Database Migrations** | Alembic | 1.13+ | Versioned relational database schema migrations |
| **Primary Database** | PostgreSQL | 16.x | ACID-compliant durable source of truth with JSONB |
| **Task Queue / Broker** | Celery + Redis | 5.4+ / 7.2+ | Distributed task processing, scheduling, retries |
| **Coordination / Cache**| Redis | 7.2+ | Task broker, concurrency locks, transient caching |
| **Local LLM Engine** | Ollama | 0.3+ | Local-first inference for JD analysis and tailoring |
| **PDF Rendering** | WeasyPrint + pdfplumber | 62+ / 0.11+ | HTML/CSS-to-PDF compilation & PDF parsing |
| **Code Formatting / Lint**| Ruff | 0.6+ | Ultra-fast linter, code formatter, import sorter |
| **Type Checking** | Mypy (Strict) | 1.11+ | Static type enforcement across all domain layers |
| **Testing Framework** | Pytest + pytest-asyncio | 8.3+ | Unit, integration, contract, and workflow tests |

---

# 3. Backend Stack Decisions

## 3.1 Language Runtime: Python 3.12

### Decision
Adopt **Python 3.12** as the unified platform runtime for the backend API and worker processes.

### Why
- **Performance:** Python 3.12 introduces major performance improvements in runtime execution (PEP 659 specializing adaptive interpreter optimizations) and lower memory overhead compared to 3.10/3.11.
- **Enhanced Typing:** Native support for PEP 695 (Type Parameter Syntax) and improved typing generics makes domain modeling significantly cleaner and more maintainable.
- **AsyncIO Refinements:** Lower latency event loop task management, superior exception groups handling (PEP 654), and improved traceback formatting for asynchronous workers.
- **Ecosystem Compatibility:** Broad, native support across FastAPI, SQLAlchemy 2.0, Pydantic v2, Celery, and scientific/document-processing packages.

### Alternatives Considered
- **Python 3.11:** Highly stable, but lacks PEP 695 clean type syntax and runtime speed gains present in 3.12.
- **Python 3.13:** Released recently; ecosystem support for certain binary C-extensions (such as WeasyPrint dependencies or specific DB drivers) is still stabilizing. 3.12 is the sweet spot of modern features and rock-solid ecosystem stability.
- **Go / Node.js:** High raw concurrency, but lacks Python's dominant ecosystem for AI/LLM integration, document parsing (`pdfplumber`, `pypdf`, `python-docx`), and templating engines.

### Trade-offs
- Interpreted language performance is lower than compiled languages like Go or Rust; mitigated by delegating I/O-heavy operations to `asyncio` and computation-heavy tasks (parsing, LLM, PDF rendering) to isolated background workers.

### MVP Suitability & Future Scalability
- **MVP:** Fast local iteration, rapid prototyping, rich library ecosystem.
- **Scalability:** Scales horizontally across containerized workers in Kubernetes or AWS ECS without changing code boundaries.

---

## 3.2 Web API Framework: FastAPI

### Decision
Adopt **FastAPI (>= 0.115)** as the core REST API framework.

### Why
- **Asynchronous Native:** Built directly on Starlette and `asyncio`, providing high I/O concurrency for handling concurrent client requests and database queries.
- **Deep Pydantic v2 Integration:** Native serialization and validation of HTTP requests and responses with zero-boilerplate schema generation.
- **Automatic OpenAPI Documentation:** Generates interactive Swagger/OpenAPI documentation (`/docs`) out of the box, facilitating rapid frontend integration and contract validation.
- **Dependency Injection System:** Elegant and testable DI architecture (`Depends`) allowing seamless swapping of database sessions, authenticated users, and external provider clients during testing.

### Alternatives Considered
- **Django / Django REST Framework:** Heavy batteries-included MVC framework. Introduces excessive ORM overhead, synchronous defaults, and rigidity unnecessary for a clean modular API backend.
- **Flask:** Lightweight, but lacks native async handling, requires multiple third-party plugins for validation/OpenAPI, and lacks modern typing integration.
- **Litestar:** Modern and fast, but smaller community and fewer production battle-tested integration examples compared to FastAPI.

### Trade-offs
- Requires discipline to prevent developers from writing business logic directly in route handlers ("fat controllers"). Mitigated by enforcing layered domain boundaries.

### MVP Suitability & Future Scalability
- **MVP:** Extremely fast setup, built-in validation reduces boilerplate bugs, self-documenting endpoints.
- **Scalability:** Stateless architecture enables infinite horizontal scaling behind any modern reverse proxy (Nginx, Traefik, AWS ALB).

---

## 3.3 Data Validation & Serialization: Pydantic v2

### Decision
Standardize on **Pydantic v2 (>= 2.9)** for all domain schemas, DTOs, environment configurations, and LLM structured output parsing.

### Why
- **Performance:** Core validation logic rewritten in Rust (`pydantic-core`), delivering a 5x to 20x speedup over Pydantic v1.
- **Strict Typing:** Strong separation between strict and lax coercion modes, preventing silent data corruption.
- **JSON Schema Output:** High-fidelity JSON schema generation used directly for structured LLM function calling and response formatting.
- **Settings Management:** Robust `pydantic-settings` package provides strictly typed, environment-driven configuration with file fallback (`.env`).

### Alternatives Considered
- **Marshmallow:** Python-based, significantly slower, lacks modern type annotation syntax.
- **Attrs / dataclasses:** Lacks built-in JSON schema generation, type coercion, and robust nested validation capabilities required for external API and LLM payload parsing.

### Trade-offs
- Slight learning curve around v2 model validators (`@field_validator`, `@model_validator`) compared to v1 syntax.

### MVP Suitability & Future Scalability
- **MVP:** Eliminates data validation bugs at API and worker boundaries.
- **Scalability:** Low CPU consumption even under heavy schema validation loads.

---

## 3.4 Object-Relational Mapping (ORM): SQLAlchemy 2.0 (Async)

### Decision
Adopt **SQLAlchemy 2.0+** using the modern `AsyncSession` paradigm with `Mapped` and `mapped_column` type annotations.

### Why
- **Modern 2.0 Syntax:** Complete departure from legacy 1.x query syntax; enforces explicit `select()` statements and full PEP 484 static typing compliance.
- **Native AsyncIO:** First-class asynchronous database session management via `create_async_engine()` and `async_sessionmaker()`.
- **Ecosystem Dominance:** The gold standard in Python database modeling, compatible with all advanced PostgreSQL features (JSONB operators, CTEs, window functions, advisory locks).
- **Clean Unit of Work:** Clear separation between domain entity definitions, persistence logic, and session lifecycles.

### Alternatives Considered
- **Tortoise ORM:** Async native, but smaller ecosystem, limited migration tooling, and less mature support for complex PostgreSQL features.
- **Prisma Python:** Foreign engine wrapper (Node.js engine binary), slow startup, unidiomatic Python experience.
- **Raw SQL / asyncpg directly:** Highest raw performance, but lacks schema abstraction, relationship loading, automated migration tracking, and increases boilerplate.

### Trade-offs
- Requires careful handling of lazy loading in async contexts (lazy loading is disabled in async SQLAlchemy; explicit `selectinload` or `joinedload` must be specified).

### MVP Suitability & Future Scalability
- **MVP:** Fast domain modeling with strict schema enforcement; prevents raw SQL injection vulnerabilities.
- **Scalability:** Easily configured for read/write replicas, connection pooling, and enterprise migration strategies.

---

## 3.5 Database Driver: asyncpg & psycopg

### Decision
- **Runtime App/Worker Driver:** **`asyncpg`** via `postgresql+asyncpg://`
- **Migration & Admin Driver:** **`psycopg` (v3)** or `psycopg2-binary` for synchronous Alembic operations.

### Why
- **`asyncpg`:** The fastest PostgreSQL client library available for Python. Built specifically for `asyncio`, utilizing PostgreSQL's native binary protocol directly rather than wrapping libpq. Provides unmatched throughput for async queries.
- **Alembic Compatibility:** Alembic's core runner is synchronous by design; pairing asyncpg with a standard synchronous driver (or using SQLAlchemy's `run_sync` wrapper over asyncpg) ensures rock-solid, deadlock-free database migrations.

### Alternatives Considered
- **`psycopg` (v3) in async mode:** Very capable and modern, but asyncpg benchmark numbers consistently show 2x to 3x lower latency on bulk fetches and JSONB queries.

### Trade-offs
- Managing two driver references in dependencies; mitigated by encapsulating the connection string generation in `app/core/config/database.py`.

### MVP Suitability & Future Scalability
- **MVP:** Excellent local throughput.
- **Scalability:** Supports connection pooling tuning (min/max size, max overflow, recycle time) suitable for high-concurrency cloud environments.

---

## 3.6 Database Migrations: Alembic

### Decision
Use **Alembic (>= 1.13)** for all schema migrations.

### Why
- **Native SQLAlchemy Integration:** Reads models directly from metadata, enabling automated diff generation (`alembic revision --autogenerate`).
- **Linear & Branching Versioning:** Full programmatic control over migration ordering, rollbacks, and data seeding scripts.
- **Strict Determinism:** Guarantees database schemas are reproducible across local dev, CI pipelines, and production environments.

### Alternatives Considered
- **Raw SQL Migration Scripts (e.g. Flyway, Sqitch):** Introduces external toolchain dependencies; lacks Python model reflection.

### Trade-offs
- Autogenerated migrations must always be reviewed by developers before merging to verify index naming and destructive column operations.

---

# 4. Database Architecture Decisions

## 4.1 Engine Version: PostgreSQL 16.x

### Decision
Deploy **PostgreSQL 16.x** as the single primary relational database.

### Why
- **JSONB Enhancements:** PostgreSQL 16 brings further optimizations to JSONB subscripting, JSON path functions, and GIN index performance.
- **Query Optimization:** Improved parallel execution of queries and enhanced index lookups.
- **Logical Replication & Observability:** Enhanced monitoring views (`pg_stat_io`) for tracking I/O bottlenecks.
- **Universal Cloud Availability:** Fully supported on AWS RDS, GCP Cloud SQL, Azure Database, and Supabase/Neon for cloud readiness.

---

## 4.2 Primary Key Strategy: UUIDv4 vs UUIDv7

### Decision
Adopt **UUIDv4** (`gen_random_uuid()`) for the initial MVP, with architecture structured to allow seamless migration to **UUIDv7** when native PostgreSQL 17 or standardized library extensions are adopted.

### Why
- **Local & Cloud Standard:** `gen_random_uuid()` is natively built into PostgreSQL 13+ core without requiring external C-extensions like `pgcrypto` or `pg_uuidv7`.
- **Security & Privacy:** Prevents sequential enumeration attacks on candidate profiles, resume versions, and job IDs.
- **Distributed Idempotency:** IDs can be generated on client, API, or worker nodes before database insertion.

### Trade-offs
- Random UUIDv4 inserts cause B-tree index page fragmentation at very high write scales (> 10M records).
- **Mitigation for Scale:** UUIDv7 offers time-ordered sorting. For the MVP scope (< 100k jobs/resumes), UUIDv4 B-tree fragmentation overhead is negligible. If table sizes grow significantly, sequential ID generation can be activated via Python's `uuid6` library without changing column types.

---

## 4.3 JSON vs JSONB Usage

### Decision
Exclusively use **`JSONB`** for semi-structured data; **`JSON`** (plain text) is prohibited.

### Fields Using JSONB:
1. `candidate_preferences.raw_filters`: Dynamic preference filters.
2. `resume_versions.structured_content`: Full hierarchical parsed resume data (skills, experiences, educations, achievements).
3. `resume_versions.template_metadata`: Layout, styling, fonts, margins, and section coordinates.
4. `job_source_records.raw_payload`: Unmodified upstream API or HTML extraction payload for auditability.
5. `job_analysis.structured_requirements`: Extracted skill matrices, responsibility lists, seniority markers.
6. `job_matches.match_explanation_details`: Granular scoring breakdown and LLM evidence quotes.

### Indexing on JSONB:
- Use **GIN (Generalized Inverted Index)** with `jsonb_path_ops` on searchable JSONB arrays (e.g., extracted skills).
- Scalar queries (e.g., specific flags inside JSONB) must be hoisted to dedicated relational columns rather than queried through JSONB traversal.

---

## 4.4 Full-Text Search (FTS) vs Trigram Search

### Decision
Use PostgreSQL native **Trigram Similarity (`pg_trgm`)** combined with **`tsvector` / `tsquery`** full-text search. No external search engine (Elasticsearch, OpenSearch, Meilisearch) will be deployed for the MVP.

### Why
- **Zero Additional Infrastructure:** Operates entirely within PostgreSQL, eliminating data synchronization pipelines and secondary cluster maintenance.
- **Job Title & Company Matching:** `pg_trgm` provides fuzzy matching on job titles and company names (e.g., handling "Frontend Engineer" vs "Front-End Developer" or slight typos).
- **Description Search:** `tsvector` with English dictionary stemming enables keyword searches across job descriptions and resume text.

---

# 5. Background Task & Queue Architecture

## 5.1 Framework Selection: Celery + Redis

### Decision
Adopt **Celery (>= 5.4)** backed by **Redis (>= 7.2)** for task brokering, scheduling, and concurrency management.

### Why
- **Approved Architectural Baseline:** Defined in `MVP_SCOPE.md` and `SYSTEM_ARCHITECTURE.md`.
- **Maturity & Reliability:** Over a decade of battle-tested production history handling millions of tasks.
- **Rich Feature Set:**
  - Native periodic scheduling via `Celery Beat`.
  - Granular task routing across dedicated queues (`discovery`, `matching`, `tailoring`, `notifications`).
  - Native exponential backoff retries with jitter.
  - Task execution timeouts (hard and soft limits).
  - Rate-limiting per worker or per task type.
- **Separation of Concerns:** Allows the FastAPI web process to remain 100% responsive while long-running tasks (LLM extraction, PDF compilation, web crawling) execute in isolated worker processes.

### Alternatives Evaluated
- **ARQ:** Lightweight async Redis task queue. Very fast, but lacks complex task routing, mature periodic task scheduling UI, canvas workflows (chords, chains), and enterprise monitoring tools like Flower.
- **Dramatiq:** Excellent modern alternative to Celery, but smaller community, fewer plugins, and less widespread familiarity in the Python ecosystem.
- **Temporal / Cadence:** Outstanding for enterprise durable workflow orchestration, but introduces massive operational complexity (Cassandra/Postgres, UI server, Go/Java services) that directly violates the "do not over-engineer the MVP" principle.

### Trade-offs
- Celery configuration can be verbose and has historical quirks with async event loops.
- **Mitigation:** Run Celery workers in standard synchronous or prefork mode, using `async_to_sync` or dedicated async runners only where needed, while keeping task entry points clean and modular.

---

## 5.2 Task Routing & Queue Topology

Tasks are partitioned across four distinct queues to prevent long-running tasks from starving urgent operations:

```text
┌────────────────────────────────────────────────────────┐
│                      Redis Broker                      │
│                                                        │
│  ├── queue: discovery      (Crawling, Source Polling)  │
│  ├── queue: processing     (Normalization, Matching)   │
│  ├── queue: tailoring      (LLM Inference, PDF Render) │
│  └── queue: notifications  (SMTP Email Delivery)       │
└────────────────────────────────────────────────────────┘
```

1. **`discovery` queue:** Low concurrency, strict rate limits (respecting source restrictions).
2. **`processing` queue:** High concurrency, CPU-light, database I/O-bound (normalization, deduplication, deterministic rules).
3. **`tailoring` queue:** Low concurrency (limited by Ollama/GPU capacity), CPU and LLM-bound.
4. **`notifications` queue:** High priority, network I/O-bound (fast delivery of job alerts).

---

## 5.3 Retry Strategy & Idempotency

### Retry Policy:
- **Network / Third-party Failures (Ollama timeout, SMTP error, external source 5xx):**
  - Max retries: 5 attempts.
  - Exponential backoff with jitter: `initial_delay = 5s`, `backoff_factor = 2`, `max_delay = 300s`, plus random jitter `[0, 15s]`.
- **Permanent Failures (404 Not Found, Schema Validation Failure, Resume Evidence Mismatch):**
  - Zero retries. Task fails immediately and marks the database record as `FAILED` with an explicit `error_summary`.

### Idempotency Mechanism:
- Every background task checks the target record's database state prior to execution.
- If a task is retried after a worker crash:
  - If `tailored_resumes` already has a valid checksum and file on disk, resume tailoring is skipped.
  - If `notification_deliveries` already has `status = 'DELIVERED'`, email sending is skipped.

---

# 6. Caching & Coordination: Redis Role

## 6.1 MVP Requirements
In the MVP, Redis is strictly utilized as:
1. **Celery Message Broker:** Transporting task payloads between FastAPI and workers.
2. **Celery Result Backend:** Transient storage for task completion states (TTL = 1 hour).
3. **Distributed Locks (Redlock Pattern):** Preventing concurrent duplicate processing of the same canonical job during discovery runs.
4. **Source Adapter Rate Limiting:** Enforcing sliding-window request limits against Greenhouse, Lever, and career portals.

## 6.2 Scalability & Anti-Patterns
- **Durable Data Prohibition:** Redis is treated as ephemeral infrastructure. Under no circumstances is business-critical history (job details, candidate information, notification history) stored solely in Redis.
- **Future Cloud Evolution:** Can transition from a single local Redis Docker container to AWS ElastiCache / Redis Cloud with zero application code modifications.

---

# 7. LLM Integration Architecture

## 7.1 Provider Abstraction Layer

The platform isolates all LLM interactions behind an abstract protocol (`LLMProvider`) to prevent vendor lock-in and enable seamless switching between local models and cloud providers.

```text
┌──────────────────────────────────────────────────────────────┐
│                      LLMProvider (Protocol)                  │
│                                                              │
│  + complete(prompt: str, options: LLMOptions) -> str         │
│  + complete_structured(prompt: str, schema: Type[T]) -> T    │
└──────────────────────────────┬───────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│        OllamaProvider        │    │    OpenAICompatibleProvider  │
│                              │    │                              │
│ Local Llama 3 / Mistral      │    │ Claude / GPT-4o / vLLM       │
│ via Ollama HTTP API          │    │ via Standard Cloud API       │
└──────────────────────────────┘    └──────────────────────────────┘
```

## 7.2 Structured Output Enforcement

LLM interactions must never return unvalidated free-form text when structured data is required.

### Enforcement Mechanism:
1. **JSON Schema Injection:** The target Pydantic schema is serialized to JSON Schema and injected into the prompt system instructions.
2. **Native JSON Mode:** Where supported (e.g., Ollama `format="json"` parameter), enforce strict JSON output from the model.
3. **Pydantic Validation:** The returned string is deserialized into the specified Pydantic model (`schema.model_validate_json(response)`).
4. **Self-Correction Retry:** If validation fails due to malformed JSON or missing attributes, a single repair prompt is issued with the validation error message. If the second attempt fails, the task aborts gracefully and logs the raw output.

## 7.3 Resilience, Timeouts & Local/Cloud Parity

- **Timeouts:**
  - JD Analysis: 60 seconds.
  - Resume Tailoring: 120 seconds.
- **Local Model Recommendation:** `llama3.1:8b` or `mistral:7b-instruct` running locally via Ollama.
- **Cloud Parity:** The `OpenAICompatibleProvider` uses standard OpenAI-compatible API schemas, enabling immediate configuration for Groq, DeepSeek, OpenAI, or local vLLM instances without altering business logic.

---

# 8. Document & PDF Processing Stack

## 8.1 PDF Compilation: WeasyPrint

### Decision
Adopt **WeasyPrint (>= 62)** for compiling HTML/CSS templates into pixel-perfect PDF resumes.

### Why
- **Modern Web Standards:** Full support for CSS Paged Media (`@page`), Flexbox, CSS Grid, custom web fonts, and precise margins.
- **Template Maintainability:** Resumes are authored as standard HTML/Jinja2 templates and styled with CSS, making layout adjustments vastly simpler than programmatic canvas drawing.
- **Deterministic Rendering:** Produces identical visual output across platforms (unlike headless Chrome which can suffer from font rendering variations across operating systems).
- **ATS Compliance:** Emits clean, searchable vector text streams rather than rasterized images, ensuring complete ATS readability.

### Alternatives Considered
- **ReportLab:** Python standard for PDFs, but requires tedious manual coordinate calculations (`canvas.drawString()`); maintaining complex resume templates is painful and slow.
- **Puppeteer / Playwright (Headless Chrome):** Heavyweight; requires running a complete Node.js/Chromium browser instance inside Docker, consuming 500MB+ RAM per instance.
- **LaTeX:** Outstanding typography, but complex binary distribution (TeX Live is multiple gigabytes), slow compilation, and difficult to sanitize against injection vulnerabilities.

---

## 8.2 Document Parsing: pdfplumber & python-docx

### Decision
- Use **`pdfplumber`** for extracting structured text, layout bounding boxes, and font properties from candidate master PDF resumes.
- Use **`python-docx`** for direct XML inspection, style preservation, and content replacement when the candidate uploads a `.docx` resume.

---

# 9. Testing Strategy Stack

| Test Level | Tool | Strategy |
| :--- | :--- | :--- |
| **Test Runner** | `pytest` | Test execution, parameterized test cases, assertions |
| **Async Harness** | `pytest-asyncio` | Native async fixture management and coroutine execution |
| **API Client** | `httpx.AsyncClient` | In-process HTTP testing against FastAPI `app` without socket overhead |
| **Database Mocking** | PostgreSQL Test Container | Real PostgreSQL database running in Docker; isolated transactions |
| **Mocking / Stubs** | `pytest-mock` / `respx` | Intercepting external HTTP calls (Greenhouse, Lever, Ollama) |
| **Code Coverage** | `pytest-cov` | Line and branch coverage reporting (target > 85% core modules) |

---

# 10. Code Quality & Developer Tooling

## 10.1 Formatting and Linting: Ruff

### Decision
Standardize on **Ruff (>= 0.6)**, replacing Black, Flake8, isort, and Bandit.

### Why
- **Performance:** Written in Rust; executes 10x to 100x faster than traditional Python linting toolchains.
- **Unified Rule Engine:** Enforces formatting, import sorting, docstring conventions, bug identification, and security linting in a single pass.
- **Zero Config Fatigue:** Single configuration block inside `pyproject.toml`.

## 10.2 Static Type Checking: Mypy

### Decision
Enforce **strict Mypy (`mypy --strict`)** across all backend code.

### Guidelines:
- Disallow untyped defs (`disallow_untyped_defs = true`).
- Disallow any unannotated function arguments or return types.
- Ensure all SQLAlchemy models and Pydantic schemas are type-checked via the `pydantic.mypy` and `sqlalchemy.ext.mypy.plugin` plugins.

---

# 11. Technology Decisions Summary Table

```text
┌──────────────────────┬──────────────────────┬───────────────────────────────────────────────────────┐
│ Decision             │ Recommendation       │ Key Justification                                     │
├──────────────────────┼──────────────────────┼───────────────────────────────────────────────────────┤
│ Language Runtime     │ Python 3.12 LTS      │ Performance optimizations, modern typing, async speed │
│ Web API Framework    │ FastAPI 0.115+       │ Native async, Pydantic v2, auto OpenAPI documentation │
│ Validation / DTOs    │ Pydantic v2.9+       │ High-speed Rust core, strict schemas, JSON mode       │
│ ORM Engine           │ SQLAlchemy 2.0+      │ Strict typing, unit-of-work, async session support    │
│ Primary DB Driver    │ asyncpg 0.29+        │ Binary PostgreSQL protocol, highest async throughput  │
│ Database Engine      │ PostgreSQL 16.x      │ Durable truth, JSONB indexing, pg_trgm fuzzy search   │
│ Migration Engine     │ Alembic 1.13+        │ Declarative autogenerate, deterministic migrations    │
│ Task Queue / Broker  │ Celery 5.4 + Redis   │ Multi-queue routing, retries with backoff, scheduling │
│ Distributed Caching  │ Redis 7.2+           │ Concurrency locks, rate limiting, ephemeral broker    │
│ Local LLM Provider   │ Ollama (Llama 3.1)   │ Local-first, private inference, zero API cost for dev │
│ PDF Rendering Engine │ WeasyPrint 62+       │ CSS Paged Media, ATS-readable text, clean templates   │
│ Resume Docx Parser   │ python-docx 1.1+     │ Native XML layout and style extraction                │
│ Resume PDF Parser    │ pdfplumber 0.11+     │ Layout bounding box, font property, table extraction  │
│ Linter / Formatter   │ Ruff 0.6+            │ Blazing-fast Rust-based unified code quality tool     │
│ Type Checker         │ Mypy (Strict)        │ Static verification across all domain modules         │
│ Test Framework       │ Pytest + respx       │ Async fixtures, transaction isolation, HTTP mocking   │
└──────────────────────┴──────────────────────┴───────────────────────────────────────────────────────┘
```

