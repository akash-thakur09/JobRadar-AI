# AI Job Intelligence Platform — MVP Scope

**Status:** Approved Initial Scope

---

# 1. MVP Objective

The MVP must prove the complete core workflow:

```text
Job Discovery
      ↓
Job Normalization
      ↓
Deduplication
      ↓
Eligibility
      ↓
Job Matching
      ↓
JD Analysis
      ↓
Truthful Resume Tailoring
      ↓
PDF Generation
      ↓
Resume Storage
      ↓
Immediate Email Notification
      ↓
Manual Review
      ↓
Manual Application
```

The goal is not to build every possible job-search feature.

The goal is to validate a reliable end-to-end job intelligence pipeline.

---

# 2. MVP Included Features

## 2.1 Candidate Profile

The MVP includes:

- Candidate profile management.
- Professional summary.
- Work experience.
- Technical skills.
- Projects.
- Education.
- Certifications.
- Job preferences.

The initial architecture may support one primary candidate account while remaining extensible for future multi-user support.

---

## 2.2 Master Resume Management

The MVP includes:

- Resume upload.
- Original file preservation.
- Resume parsing.
- Structured resume representation.
- Resume versioning.
- Active resume selection.

The master resume is immutable source material.

---

## 2.3 Job Discovery

The MVP supports:

### Greenhouse

Discovery through supported and permitted public job endpoints.

### Lever

Discovery through supported and permitted public job endpoints.

### Permitted Company Career Pages

Discovery only where technically and legally appropriate.

The system must respect:

- Terms and restrictions.
- Rate limits.
- Authentication boundaries.
- Anti-bot protections.

---

## 2.4 Job Normalization

The MVP normalizes:

- Job titles.
- Companies.
- Locations.
- Employment types.
- Job URLs.
- Source identifiers.

All source-specific data is transformed into a common internal job model.

---

## 2.5 Duplicate Detection

The MVP prevents unnecessary duplicate jobs.

Deduplication may use:

- Source job ID.
- Canonical URL.
- Company.
- Job title.
- Location.

The exact canonicalization strategy will be finalized during detailed technical design.

---

## 2.6 Job Freshness

The MVP supports:

- `posted_at`
- `first_seen_at`

Possible freshness preferences include:

- Last 24 hours.
- Last 7 days.
- Last 30 days.
- Any available date.

The platform must never fabricate posting dates.

---

## 2.7 Hybrid Job Matching

The MVP includes:

### Deterministic Eligibility

For hard constraints.

### Weighted Scoring

For measurable relevance.

### LLM Semantic Analysis

For contextual interpretation and match explanations.

The result is an internal relevance score.

The score is not an employer ATS score.

---

## 2.8 Job Description Analysis

The MVP extracts:

- Required skills.
- Preferred skills.
- Responsibilities.
- Experience requirements.
- Seniority.
- Keywords.
- Location.
- Employment type.

---

## 2.9 Resume Optimization

The MVP supports:

- Evidence selection.
- Relevant content prioritization.
- Truthful rephrasing.
- Relevant skill emphasis.
- Project prioritization.
- Job-specific resume generation.

The system must never fabricate:

- Skills.
- Experience.
- Projects.
- Achievements.
- Qualifications.

---

## 2.10 Resume Rendering

The MVP supports two strategies.

### Preferred

Original-template preservation where technically reliable.

### Fallback

A standardized professional ATS-friendly resume template.

---

## 2.11 PDF Generation

The MVP includes:

- Job-specific PDF generation.
- File validation.
- Resume checksum or hash.
- Persistent resume metadata.
- Storage association with the corresponding job.

---

## 2.12 Immediate Email Notification

The MVP sends an immediate email after successful processing.

The email contains:

- Job information.
- Match insights.
- Application URL.
- Tailored PDF attachment.

Duplicate notifications must be prevented.

---

## 2.13 Basic Dashboard

The MVP dashboard includes:

- Overview.
- Candidate profile.
- Master resume management.
- Job explorer.
- Job details.
- Match insights.
- Generated resume history.
- Notification history.
- Source management.

---

# 3. Explicitly Deferred Features

The following are intentionally outside the initial MVP.

## 3.1 Automated Applications

Not included:

- Automatic form filling.
- Automatic application submission.
- CAPTCHA bypassing.
- Login automation for restricted job platforms.
- Universal auto-apply.

Applications remain manual.

---

## 3.2 Additional Job Platforms

Initially deferred:

- LinkedIn.
- Indeed.
- Naukri.
- Instahyre.
- Cutshort.
- Hirist.
- Foundit.

These may later be supported through compliant integrations.

---

## 3.3 Daily Email Digest

The initial notification mode is immediate delivery.

Daily digest support is deferred.

---

## 3.4 Multi-User SaaS Features

Initially deferred:

- Organization accounts.
- Teams.
- Subscription billing.
- Role-based enterprise administration.

---

## 3.5 Advanced AI Features

Initially deferred:

- Complex autonomous agent workflows.
- Advanced multi-agent systems.
- Unnecessary LangGraph orchestration.
- Universal embedding-based semantic search.

These technologies should be introduced only when they solve a demonstrated problem.

---

## 3.6 Advanced Analytics

Initially deferred:

- Complex trend dashboards.
- Market intelligence.
- Salary prediction.
- Advanced recommendation models.

---

# 4. MVP Success Criteria

The MVP succeeds when a candidate can complete the following workflow:

```text
1. Configure candidate profile
2. Configure job preferences
3. Upload master resume
4. Activate resume version
5. Configure supported job source
6. Run scheduled discovery
7. Discover new jobs
8. Normalize jobs
9. Deduplicate jobs
10. Evaluate freshness
11. Calculate eligibility
12. Generate relevance score
13. Analyze the JD
14. Generate a truthful tailored resume
15. Produce a PDF
16. Store the resume
17. Send immediate notification
18. Receive tailored PDF by email
19. Review the job
20. Apply manually
```

---

# 5. MVP Technical Boundaries

The MVP should use:

```text
Frontend:
React + TypeScript + Tailwind CSS

Backend:
FastAPI

Database:
PostgreSQL

Background Processing:
Celery + Redis

AI:
Ollama with provider abstraction

Infrastructure:
Docker + Docker Compose

Testing:
Pytest + Vitest
```

The architecture should remain cloud-ready without introducing unnecessary distributed-system complexity.

---

# 6. MVP Definition of Done

The MVP is complete when:

- Core workflow works end to end.
- Automated tests cover critical business logic.
- Duplicate processing is prevented.
- Resume claims remain evidence-based.
- Failed tasks can be retried.
- Email delivery history exists.
- Generated resumes remain associated with jobs.
- The application can run consistently using the documented local environment.
- Major operational failures are observable through logs and persistent status records.