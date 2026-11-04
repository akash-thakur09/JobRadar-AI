# AI Job Intelligence Platform — Product Requirements

**Status:** Architecture Baseline  
**Project Type:** AI-powered Job Intelligence Platform  
**Development Model:** Local-first, cloud-ready  
**Application Strategy:** Automated discovery and preparation with manual job application

---

# 1. Product Overview

## 1.1 Vision

The AI Job Intelligence Platform is designed to continuously discover relevant job opportunities, analyze job descriptions, evaluate their relevance against a candidate profile, optimize an existing resume truthfully for suitable jobs, generate job-specific PDF resumes, and notify the candidate through email.

The platform automates the preparation stages of the job-search workflow while keeping the final application decision under the candidate's control.

The primary objective is to reduce repetitive manual work involved in:

- Searching multiple job sources.
- Reviewing large numbers of job descriptions.
- Identifying relevant opportunities.
- Comparing jobs against candidate skills and experience.
- Identifying important requirements and keywords.
- Manually tailoring a resume for each job.

The platform does **not** automatically submit job applications in the initial product.

The candidate reviews the opportunity and applies manually.

---

## 1.2 Core Product Workflow

```text
Candidate Profile + Master Resume + Job Preferences
                    |
                    v
             Discovery Scheduler
                    |
                    v
             Job Source Adapters
        /          |           \
 Greenhouse      Lever    Career Pages
                    |
                    v
              Job Normalizer
                    |
                    v
          Duplicate Detection Engine
                    |
                    v
          Freshness + Eligibility Rules
                    |
                    v
             Hybrid Matching Engine
          Deterministic + LLM Analysis
                    |
                    v
             JD Analysis Engine
                    |
                    v
          Resume Evidence Selection
                    |
                    v
           Resume Tailoring Engine
                    |
                    v
        Template Preservation / Fallback
                    |
                    v
              PDF Generation
                    |
                    v
             Resume Validation
                    |
                    v
              Resume Storage
                    |
                    v
          Immediate Email Notification
                    |
                    v
        Job Details + Tailored PDF
                    |
                    v
              Manual Review
                    |
                    v
             Manual Application
```

---

# 2. Product Goals

The platform must:

1. Discover jobs from supported and permitted sources.
2. Normalize inconsistent job information.
3. Prevent duplicate job processing.
4. Track job freshness accurately.
5. Evaluate job relevance against the candidate profile.
6. Explain why a job received its relevance score.
7. Analyze job descriptions and extract important requirements.
8. Tailor resumes using truthful candidate evidence.
9. Preserve the original resume template when technically reliable.
10. Use a standardized ATS-friendly fallback template when necessary.
11. Generate job-specific PDF resumes.
12. Store generated resume history.
13. Send immediate email notifications for suitable jobs.
14. Attach the corresponding tailored PDF resume.
15. Prevent duplicate notifications.
16. Allow the candidate to manually track application status.

---

# 3. Finalized Product Decisions

## 3.1 Job Discovery Sources

The initial supported discovery sources are:

- Greenhouse.
- Lever.
- Permitted company career pages.

The platform will use:

- Publicly available and permitted endpoints.
- Authorized APIs.
- Supported public job feeds.
- Permitted crawling where appropriate.

The platform must not:

- Bypass authentication.
- Bypass CAPTCHA systems.
- Circumvent anti-bot protections.
- Violate platform restrictions.
- Perform unauthorized scraping.

### Deferred Sources

The following are not part of the initial automated discovery MVP:

- LinkedIn.
- Indeed.
- Naukri.
- Instahyre.
- Cutshort.
- Hirist.
- Foundit.

They may be considered later through compliant and authorized integrations.

---

## 3.2 Resume Template Preservation

The platform supports two resume rendering strategies.

### Strategy A: Original Template Preservation

The preferred strategy.

When technically reliable, the system attempts to preserve the original resume's:

- Layout.
- Section structure.
- Formatting.
- Typography characteristics.
- Visual hierarchy.

### Strategy B: Standardized Fallback Template

When original-template preservation is unreliable or unsupported, the system uses a professional standardized template.

The fallback template must be:

- ATS-readable.
- Professional.
- Consistent.
- Easy to parse.
- Free from unnecessary graphics.

The original master resume always remains immutable.

---

## 3.3 Job Matching Strategy

The platform uses a hybrid matching model.

### Deterministic Rules

Used for objective and hard constraints, including:

- Experience requirements.
- Location preferences.
- Employment type.
- Required skills.
- Candidate preferences.

### Weighted Matching

Used to calculate measurable relevance using factors such as:

- Required skill coverage.
- Preferred skill coverage.
- Experience alignment.
- Job-title relevance.
- Location compatibility.

### LLM Semantic Analysis

Used where exact keyword matching is insufficient.

Examples include:

- Responsibility alignment.
- Related technology interpretation.
- Project relevance.
- Contextual skill similarity.
- Match explanations.

The LLM is not the sole source of truth.

---

## 3.4 Email Delivery

The initial notification strategy is:

> **Immediate email notification with the tailored PDF resume attached.**

An email is sent only after:

1. The job is successfully processed.
2. The job meets the configured relevance threshold.
3. A tailored resume is successfully generated.
4. Resume validation succeeds.
5. A duplicate notification does not already exist.

---

## 3.5 Deployment Strategy

The project follows a:

> **Local-first development, cloud-ready architecture.**

Initial development supports:

- Docker Compose.
- PostgreSQL.
- Redis.
- Local Ollama.
- Local storage abstraction.
- Local SMTP testing.

The architecture must remain suitable for future cloud deployment without requiring major redesign.

---

# 4. Non-Goals

The initial product will not:

- Automatically submit job applications.
- Implement universal auto-apply.
- Bypass job platform protections.
- Guarantee interviews or job selection.
- Claim to calculate an employer's actual ATS score.
- Fabricate candidate skills.
- Fabricate work experience.
- Fabricate projects.
- Fabricate achievements.
- Fabricate qualifications.
- Fabricate job posting dates.
- Support every job platform.
- Become a multi-user SaaS platform in the MVP.

---

# 5. Functional Requirements

## FR-01: Candidate Profile Management

The platform shall maintain a structured candidate profile.

Information may include:

- Full name.
- Contact information.
- Professional summary.
- Current role.
- Total years of experience.
- Previous work experience.
- Technical skills.
- Programming languages.
- Frameworks and libraries.
- Databases.
- Cloud skills.
- DevOps skills.
- Projects.
- Education.
- Certifications.

The candidate profile supports matching and resume optimization.

---

## FR-02: Candidate Job Preferences

The platform shall allow configuration of:

- Preferred job titles.
- Preferred locations.
- Remote preference.
- Hybrid preference.
- Onsite preference.
- Employment type preferences.
- Experience preferences.
- Salary expectations where applicable.
- Minimum relevance score.

---

## FR-03: Master Resume Management

The system shall support:

- Resume upload.
- Original resume preservation.
- Resume content extraction.
- Structured resume representation.
- Resume versioning.
- Active master resume selection.

The master resume remains the source material and must not be overwritten by tailored versions.

---

## FR-04: Automated Job Discovery

The platform shall support a source-adapter architecture.

Initial adapters include:

```text
JobSourceAdapter
       |
       +-- GreenhouseAdapter
       |
       +-- LeverAdapter
       |
       +-- CareerPageAdapter
```

Each adapter must transform source-specific data into a normalized internal representation.

---

## FR-05: Job Freshness Management

The platform must distinguish between:

### `posted_at`

The publication time reported by the source.

### `first_seen_at`

The time when the platform first discovered the job.

These values must never be treated as equivalent.

The system must never fabricate posting dates.

---

## FR-06: Job Normalization and Deduplication

The platform shall normalize:

- Job titles.
- Company names.
- Locations.
- Employment types.
- Application URLs.
- Source identifiers.

One canonical job should exist even when discovered through multiple sources.

Source provenance must still be preserved.

---

## FR-07: Intelligent Job Matching

The platform shall generate an internal relevance score.

The score may consider:

- Required skills.
- Preferred skills.
- Experience requirements.
- Job title.
- Responsibilities.
- Location.
- Employment type.
- Candidate preferences.

The relevance score must include an explanation.

The score must not be presented as an employer's ATS score or as a guarantee of selection.

---

## FR-08: Job Description Analysis

The platform shall analyze job descriptions and extract:

- Required skills.
- Preferred skills.
- Responsibilities.
- Experience requirements.
- Seniority.
- Location.
- Employment type.
- Salary when available.
- Important keywords.

Structured outputs should be preferred where possible.

---

## FR-09: AI-Powered Resume Optimization

For suitable jobs, the system shall:

1. Analyze the job description.
2. Extract important requirements.
3. Identify candidate-supported evidence.
4. Select relevant experience and projects.
5. Reorder relevant content where appropriate.
6. Rephrase existing information truthfully.
7. Emphasize supported skills.
8. Generate a job-specific resume.

The system must never add unsupported information simply to improve keyword matching.

---

## FR-10: Resume Validation

Before notification, the platform shall verify:

- Required resume sections exist.
- Generated content is supported by candidate evidence.
- PDF generation succeeded.
- The generated file is readable.
- Duplicate generation is avoided where possible.

---

## FR-11: Email Notifications

The immediate notification shall include:

- Job title.
- Company.
- Location.
- Experience requirements when available.
- Salary when available.
- Source.
- Posting date when available.
- Freshness information.
- Relevance score.
- Important matching skills.
- Job summary.
- Direct application URL.

The corresponding tailored PDF resume shall be attached.

---

# 6. Business Rules

The following rules are mandatory:

1. One canonical job should exist even if multiple sources discover it.
2. Source provenance must be preserved.
3. Job publication dates must never be fabricated.
4. Candidate information must never be fabricated.
5. Master resumes remain immutable source material.
6. Tailored resumes must be associated with specific jobs.
7. Failed email delivery must not invalidate job discovery.
8. Resume generation and notification delivery must be independently retryable.
9. Source access restrictions must be respected.
10. Manual application remains the primary application mechanism.
11. Universal auto-apply is outside the initial product.
12. Inbound job-alert email ingestion is separate from outbound notification delivery.

---

# 7. Security Requirements

The platform processes sensitive candidate information.

## Resume Upload Security

The system should implement:

- File type validation.
- File size limits.
- Filename sanitization.
- Safe storage paths.
- Controlled document processing.

## External Source Security

The system should implement:

- URL validation.
- SSRF protections.
- Request timeouts.
- Redirect controls.
- Source-specific rate limits.

## Secrets Management

Secrets must not be committed to source control.

Examples include:

- SMTP credentials.
- API keys.
- Cloud credentials.
- Provider tokens.

Local development should use environment variables.

Cloud deployments should use appropriate secret management.

---

# 8. Observability Requirements

The system should support structured logging.

Important identifiers include:

```text
job_id
source_id
discovery_run_id
resume_id
notification_id
correlation_id
```

The system should make it possible to determine:

- Which source discovered a job.
- Which worker processed it.
- Why matching failed.
- Why a job was rejected.
- Which resume version was used.
- Why resume generation failed.
- Why an email delivery failed.

---

# 9. Acceptance Criteria

The initial end-to-end workflow is considered successful when the system can perform:

```text
1. Candidate creates or updates profile
2. Candidate uploads master resume
3. System parses and versions the resume
4. Discovery scheduler runs
5. Supported jobs are discovered
6. Jobs are normalized
7. Duplicate jobs are prevented
8. Freshness is evaluated
9. Eligibility is calculated
10. Relevance score is generated
11. Job description is analyzed
12. Resume is tailored truthfully
13. PDF is generated
14. Resume is validated and stored
15. Immediate email is sent
16. Tailored PDF is attached
17. Candidate reviews the opportunity
18. Candidate applies manually
```

The complete workflow should function without manual database manipulation.

---

# 10. Core Engineering Principles

1. PostgreSQL is the durable source of truth.
2. Redis is infrastructure, not permanent business history.
3. Background operations must be retryable.
4. Processing must be idempotent.
5. Source adapters must remain isolated.
6. LLM output must not be blindly trusted as factual candidate data.
7. Candidate evidence must remain traceable.
8. Master resumes are immutable.
9. Generated resumes are versioned artifacts.
10. Notifications must be deduplicated.
11. Job provenance must be preserved.
12. External platform restrictions must be respected.
13. Manual application remains the final decision.
14. The MVP uses a modular monolith.
15. The architecture must remain cloud-ready without overengineering.