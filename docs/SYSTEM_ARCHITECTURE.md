# AI Job Intelligence Platform — System Architecture

**Architecture Style:** Modular Monolith + Background Workers  
**Development Model:** Local-first, cloud-ready

---

# 1. Architecture Overview

The platform uses a modular monolith for core business functionality and separate background workers for asynchronous processing.

This approach provides:

- Clear module boundaries.
- Lower operational complexity.
- Easier local development.
- Easier debugging.
- Durable background processing.
- Future extraction paths for resource-intensive components.

The initial architecture does not use microservices.

---

# 2. High-Level Architecture

```text
┌──────────────────────────────────────────────┐
│              React Frontend                  │
│                                              │
│ Profile / Jobs / Resumes / Settings          │
└──────────────────────┬───────────────────────┘
                       │
                       │ REST API
                       ▼
┌──────────────────────────────────────────────┐
│                FastAPI Backend               │
│                                              │
│ API + Application Services + Domain Modules  │
└──────────────────────┬───────────────────────┘
                       │
        ┌──────────────┼──────────────────┐
        │              │                  │
        ▼              ▼                  ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ PostgreSQL  │  │ Redis       │  │ File Storage│
│ Durable DB  │  │ Queue/Broker│  │ Resume Files│
└─────────────┘  └──────┬──────┘  └─────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────┐
│           Background Processing              │
│                                              │
│ Discovery / Matching / Resume / Email        │
└───────┬──────────────┬──────────────┬────────┘
        │              │              │
        ▼              ▼              ▼
   Job Sources      Ollama       Email Provider
```

---

# 3. Architectural Components

## 3.1 Frontend

Technology:

- React.
- TypeScript.
- Tailwind CSS.

Responsibilities:

- Display dashboard.
- Manage candidate profile.
- Manage job preferences.
- Upload resumes.
- Display jobs.
- Show matching insights.
- Display generated resume history.
- Display notifications and processing status.

The frontend should not contain critical business logic.

---

## 3.2 FastAPI Backend

Responsibilities:

- HTTP API.
- Request validation.
- Authentication when introduced.
- Application orchestration.
- Domain service coordination.
- Database access coordination.

The API should not execute long-running AI or document-generation tasks synchronously.

---

## 3.3 PostgreSQL

PostgreSQL is the durable source of truth.

It stores:

- Candidate information.
- Preferences.
- Resume metadata.
- Job records.
- Source provenance.
- Job analysis.
- Match results.
- Generated resume metadata.
- Notification history.
- Discovery history.
- Application tracking.

---

## 3.4 Redis

Redis is used for:

- Background task broker functionality.
- Short-lived infrastructure state.
- Optional caching.

Redis must not be treated as permanent business history.

---

## 3.5 Background Workers

Background workers execute:

- Job discovery.
- Job processing.
- Matching.
- AI analysis.
- Resume generation.
- PDF generation.
- Email delivery.

Workers should be independently scalable in future deployments.

---

## 3.6 Ollama

Ollama provides local LLM capabilities during initial development.

Primary uses:

- Structured job-description analysis.
- Semantic match interpretation.
- Resume tailoring assistance.

LLM access must be abstracted behind a provider interface.

---

# 4. Backend Module Architecture

Recommended structure:

```text
backend/
│
├── app/
│   │
│   ├── api/
│   │   ├── routes/
│   │   └── dependencies/
│   │
│   ├── core/
│   │   ├── config/
│   │   ├── logging/
│   │   └── security/
│   │
│   ├── modules/
│   │   ├── candidate/
│   │   ├── resume/
│   │   ├── jobs/
│   │   ├── discovery/
│   │   ├── matching/
│   │   ├── analysis/
│   │   ├── tailoring/
│   │   ├── notifications/
│   │   └── applications/
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── storage/
│   │   ├── queue/
│   │   ├── email/
│   │   └── llm/
│   │
│   ├── workers/
│   │
│   └── main.py
│
├── tests/
│
└── alembic/
```

---

# 5. Core Domain Boundaries

## Candidate Module

Responsible for:

- Candidate profile.
- Skills.
- Experience.
- Preferences.

---

## Resume Module

Responsible for:

- Master resume metadata.
- Resume versions.
- Resume parsing.
- Structured resume representation.

---

## Discovery Module

Responsible for:

- Source registry.
- Source adapters.
- Scheduled discovery.
- Discovery history.
- Source health.

---

## Jobs Module

Responsible for:

- Canonical jobs.
- Job normalization.
- Deduplication.
- Source provenance.

---

## Matching Module

Responsible for:

- Eligibility rules.
- Skill normalization.
- Deterministic scoring.
- Final relevance scoring.

---

## Analysis Module

Responsible for:

- JD extraction.
- Required skills.
- Preferred skills.
- Responsibilities.
- Semantic interpretation.

---

## Tailoring Module

Responsible for:

- Candidate evidence selection.
- Resume tailoring plans.
- LLM-assisted rewriting.
- Evidence validation.

---

## Notifications Module

Responsible for:

- Notification creation.
- Email delivery.
- Retry handling.
- Delivery history.
- Idempotency.

---

# 6. Job Discovery Architecture

```text
Discovery Scheduler
        |
        ▼
Source Registry
        |
        ├── Greenhouse Adapter
        ├── Lever Adapter
        └── Career Page Adapter
                  |
                  ▼
           Raw Job Data
                  |
                  ▼
            Normalization
                  |
                  ▼
          Canonical Job Logic
                  |
                  ▼
         Duplicate Detection
                  |
                  ▼
             Persist Job
```

Source adapters must remain isolated from matching and resume logic.

---

# 7. End-to-End Job Processing Flow

```text
1. Scheduler starts discovery
        |
2. Source adapter fetches jobs
        |
3. Raw source data is normalized
        |
4. Duplicate detection runs
        |
5. Canonical job is created or updated
        |
6. Freshness rules are evaluated
        |
7. Eligibility rules run
        |
8. Relevance score is calculated
        |
9. JD analysis runs
        |
10. Candidate evidence is selected
        |
11. Resume tailoring plan is created
        |
12. Resume content is generated
        |
13. Rendering strategy is selected
        |
14. PDF is generated
        |
15. Resume validation runs
        |
16. Resume artifact is stored
        |
17. Email notification is queued
        |
18. Email is delivered
```

---

# 8. Background Processing Architecture

## 8.1 Worker Types

### Discovery Worker

Responsibilities:

- Fetch jobs.
- Respect rate limits.
- Record discovery runs.
- Trigger normalization.

### Matching Worker

Responsibilities:

- Run eligibility rules.
- Calculate deterministic scores.
- Trigger semantic analysis where required.

### Resume Worker

Responsibilities:

- Select evidence.
- Generate tailoring plans.
- Call LLM provider.
- Render documents.
- Generate PDFs.
- Validate generated resumes.

### Notification Worker

Responsibilities:

- Send emails.
- Attach tailored PDFs.
- Retry failures.
- Record delivery attempts.

---

## 8.2 Scheduling

Scheduling and polling intervals are separate from freshness filters.

Example:

```text
Discovery schedule:
Every 6 hours

Freshness filter:
Jobs posted within the last 7 days
```

These represent different concerns.

---

## 8.3 Idempotency

Every background operation must be safe to retry.

Example:

```text
Resume generated successfully
        |
Worker crashes
before notification
        |
Task retries
        |
Existing valid resume detected
        |
Skip regeneration
        |
Continue notification
```

The database must persist processing state.

---

# 9. Job Matching Architecture

The matching engine uses three layers.

## Layer 1: Hard Eligibility

Examples:

- Location incompatibility.
- Employment type incompatibility.
- Clear experience mismatch.
- Mandatory candidate preferences.

Hard constraints may reject a job or significantly reduce its score.

---

## Layer 2: Weighted Deterministic Matching

Possible scoring categories:

```text
Required Skills        40%
Preferred Skills       15%
Experience             20%
Job Title              10%
Location               10%
Other Preferences       5%
```

These values are initial design assumptions and should remain configurable.

---

## Layer 3: LLM Semantic Analysis

The LLM may analyze:

- Responsibility alignment.
- Related technologies.
- Project relevance.
- Contextual skill compatibility.

The LLM must not override explicit hard constraints without a defined business rule.

---

# 10. Resume Processing Architecture

```text
MASTER RESUME
Immutable Source
        |
        ▼
RESUME PARSING
        |
        ▼
STRUCTURED CANDIDATE EVIDENCE
        |
        +-------------------+
        |                   |
        ▼                   ▼
JOB DESCRIPTION       CANDIDATE PROFILE
        |                   |
        +--------+----------+
                 ▼
          EVIDENCE SELECTION
                 |
                 ▼
           TAILORING PLAN
                 |
                 ▼
        RESUME CONTENT OUTPUT
                 |
        +--------+---------+
        |                  |
        ▼                  ▼
Original Template    Standard Fallback
Preservation         Template
        |                  |
        +--------+---------+
                 ▼
           PDF VALIDATION
                 |
                 ▼
         STORED TAILORED RESUME
```

---

# 11. Candidate Evidence Protection

Every generated resume claim must be traceable to known evidence.

Example:

```text
Evidence:
"Developed REST APIs using Node.js and Express."

Allowed:
"Built and maintained REST APIs using Node.js and Express."

Not Allowed:
"Designed distributed Kubernetes microservices."
```

The system must reject unsupported claims.

---

# 12. Resume Rendering Strategies

## Original Template Preservation

Preferred when the source format can be processed reliably.

Goal:

- Preserve structure.
- Preserve visual hierarchy.
- Preserve section ordering where appropriate.

## Standardized Fallback

Used when preservation cannot reliably produce a valid document.

The fallback should prioritize:

- ATS readability.
- Consistent formatting.
- Professional layout.
- Reliable PDF generation.

---

# 13. Email Delivery Architecture

Notification is triggered only after:

```text
Job Eligible
      AND
Score >= Threshold
      AND
Resume Generated
      AND
Resume Validated
      AND
Not Already Delivered
```

The notification worker is independently retryable.

A failed email must not require rediscovering or reprocessing the job.

---

# 14. Frontend Architecture

Recommended structure:

```text
frontend/
│
├── src/
│   ├── app/
│   ├── pages/
│   │   ├── Dashboard/
│   │   ├── Profile/
│   │   ├── Resume/
│   │   ├── Jobs/
│   │   ├── JobDetails/
│   │   ├── TailoredResumes/
│   │   ├── Notifications/
│   │   └── Settings/
│   │
│   ├── components/
│   ├── features/
│   ├── services/
│   ├── hooks/
│   ├── types/
│   └── utils/
```

The frontend should be organized around product features.

---

# 15. LLM Provider Architecture

The application should not directly depend on Ollama throughout the codebase.

Use a provider abstraction.

Conceptually:

```text
LLM Provider Interface
        |
        +── Ollama Provider
        |
        +── Future Cloud Provider
```

The application should interact with domain-level AI capabilities rather than provider-specific APIs.

---

# 16. Cloud-Ready Architecture Principles

The local architecture should avoid assumptions that prevent cloud deployment.

Examples:

- File storage behind an abstraction.
- Email behind a provider abstraction.
- LLM behind a provider abstraction.
- Background workers independently deployable.
- Environment-driven configuration.
- Stateless API processes.

The initial system should not introduce cloud complexity before it is needed.

---

# 17. Architecture Decisions

1. Modular monolith for the MVP.
2. PostgreSQL as the durable source of truth.
3. Redis for task infrastructure.
4. Background workers for long-running operations.
5. Source-adapter architecture for job discovery.
6. Hybrid deterministic and semantic matching.
7. Evidence-based resume generation.
8. Original-template preservation with standardized fallback.
9. Immediate email notification.
10. Local-first, cloud-ready infrastructure.