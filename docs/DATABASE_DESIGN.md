# AI Job Intelligence Platform — Database Design

**Database:** PostgreSQL  
**Status:** Initial Logical Database Design

---

# 1. Database Design Principles

The database design follows these principles:

1. PostgreSQL is the durable source of truth.
2. Master resumes are immutable.
3. Generated resumes are separate versioned artifacts.
4. One canonical job should exist across multiple sources.
5. Source provenance must be preserved.
6. Background processing state must be durable.
7. Notifications must support idempotency.
8. Historical processing information should remain traceable.

---

# 2. High-Level ERD

```text
USER
 |
 +── CANDIDATE_PROFILE
 |        |
 |        +── CANDIDATE_PREFERENCES
 |
 +── MASTER_RESUME
 |        |
 |        +── RESUME_VERSION
 |
 +── JOB_MATCH ─────────── JOB
                              |
                              +── JOB_SOURCE_RECORD
                              |
                              +── JOB_ANALYSIS
                              |
                              +── TAILORED_RESUME
                                       |
                                       +── RESUME_VERSION
                              |
                              +── NOTIFICATION_DELIVERY
                              |
                              +── APPLICATION

JOB_SOURCE
    |
    +── DISCOVERY_RUN
    |
    +── JOB_SOURCE_RECORD
```

---

# 3. Entity Relationships

## User → Candidate Profile

A user owns one candidate profile in the initial product.

Future architecture may allow multiple profiles.

---

## Candidate Profile → Preferences

Candidate preferences define job-search constraints.

---

## Candidate Profile → Master Resume

A candidate can maintain multiple master resumes.

One resume may be marked active.

---

## Master Resume → Resume Versions

A master resume may have multiple versions.

Versions support:

- Content history.
- Template metadata.
- Checksums.
- Active version tracking.

---

## Job → Source Records

One canonical job may be discovered through multiple sources.

Each discovery source is stored separately.

---

## Job → Analysis

Job analysis stores extracted intelligence from the JD.

---

## Job → Match

A job match represents the relationship between:

- Candidate profile.
- Job.
- Eligibility.
- Scores.
- Match explanation.

---

## Job → Tailored Resume

Generated resumes are associated with:

- A specific job.
- A specific source resume version.

---

## Job → Notification Delivery

Each notification is tracked independently.

---

# 4. Core Tables

## 4.1 users

Purpose: User identity.

```text
id
email
created_at
updated_at
```

---

## 4.2 candidate_profiles

Purpose: Structured candidate information.

```text
id
user_id
full_name
professional_summary
current_role
total_experience_months
created_at
updated_at
```

Relationship:

```text
users.id
    ↓
candidate_profiles.user_id
```

---

## 4.3 candidate_preferences

Purpose: Job-search preferences.

```text
id
candidate_profile_id
minimum_relevance_score
remote_preference
preferred_locations
employment_preferences
created_at
updated_at
```

Some preference structures may later use normalized tables rather than JSON storage depending on query requirements.

---

## 4.4 master_resumes

Purpose: Original resume artifact metadata.

```text
id
candidate_profile_id
original_filename
storage_key
mime_type
checksum
is_active
created_at
updated_at
```

The original file should never be overwritten.

---

## 4.5 resume_versions

Purpose: Versioned structured representation of a master resume.

```text
id
master_resume_id
version_number
structured_content
template_metadata
checksum
created_at
```

Possible structured fields may include:

- Summary.
- Skills.
- Experience.
- Projects.
- Education.
- Certifications.

---

## 4.6 job_sources

Purpose: Discovery source configuration.

```text
id
name
source_type
is_enabled
configuration
created_at
updated_at
```

Examples:

```text
Greenhouse
Lever
Career Page
```

---

## 4.7 discovery_runs

Purpose: Historical discovery execution.

```text
id
job_source_id
started_at
completed_at
status
jobs_found
jobs_created
jobs_updated
error_summary
```

This allows source health and operational monitoring.

---

## 4.8 jobs

Purpose: Canonical job entity.

```text
id
canonical_company_name
title
normalized_location
employment_type
description
canonical_application_url
posted_at
first_seen_at
status
created_at
updated_at
```

The canonical job should represent the platform's normalized understanding of the opportunity.

---

## 4.9 job_source_records

Purpose: Preserve source-specific job provenance.

```text
id
job_id
job_source_id
external_job_id
source_url
raw_posted_at
first_seen_at
raw_payload_reference
created_at
```

Suggested uniqueness:

```text
(job_source_id, external_job_id)
```

This prevents duplicate ingestion from the same source.

---

## 4.10 job_analysis

Purpose: Structured job-description intelligence.

```text
id
job_id
required_skills
preferred_skills
responsibilities
experience_requirements
seniority
summary
analysis_version
created_at
updated_at
```

The exact design of structured fields should be finalized during detailed schema design.

---

## 4.11 job_matches

Purpose: Candidate-job relevance evaluation.

```text
id
job_id
candidate_profile_id
eligibility_status
deterministic_score
semantic_score
final_score
match_explanation
created_at
updated_at
```

A match record should explain why the score was produced.

---

## 4.12 tailored_resumes

Purpose: Generated job-specific resume artifacts.

```text
id
job_id
resume_version_id
rendering_strategy
storage_key
checksum
generation_status
validation_status
created_at
updated_at
```

Rendering strategy examples:

```text
ORIGINAL_TEMPLATE
STANDARD_FALLBACK
```

Suggested uniqueness:

```text
(job_id, resume_version_id)
```

The final implementation may include a generation version if multiple valid variants are required.

---

## 4.13 notification_deliveries

Purpose: Email delivery history.

```text
id
job_id
tailored_resume_id
delivery_type
recipient
status
attempt_count
provider_message_id
last_error
sent_at
created_at
updated_at
```

Suggested idempotency constraint:

```text
(job_id, recipient, delivery_type)
```

This prevents duplicate notifications.

---

## 4.14 applications

Purpose: Manual application tracking.

```text
id
job_id
candidate_profile_id
status
applied_at
notes
created_at
updated_at
```

Possible statuses may include:

```text
SAVED
APPLIED
INTERVIEWING
REJECTED
OFFER
WITHDRAWN
```

Exact status modeling will be finalized during detailed design.

---

# 5. Job Processing State

The database should track meaningful lifecycle states.

Conceptually:

```text
DISCOVERED
    ↓
NORMALIZED
    ↓
ELIGIBILITY_EVALUATED
    ↓
MATCHED
    ↓
ANALYZED
    ↓
RESUME_GENERATED
    ↓
RESUME_VALIDATED
    ↓
NOTIFICATION_PENDING
    ↓
NOTIFIED
```

Failures should be explicit and observable.

Example:

```text
MATCHING_FAILED
RESUME_GENERATION_FAILED
NOTIFICATION_FAILED
```

The exact state-machine design should be finalized before implementation.

---

# 6. Important Constraints

## Canonical Job

The system must prevent unnecessary duplicate canonical jobs.

The final strategy may use a combination of:

- External source ID.
- Canonical application URL.
- Company normalization.
- Title normalization.
- Location.

---

## Resume Generation

Tailored resumes should be linked to:

```text
Job
+
Specific Resume Version
```

This preserves historical reproducibility.

---

## Notifications

A notification must be uniquely identifiable by:

```text
Job
+
Recipient
+
Delivery Type
```

---

# 7. Recommended Initial Indexes

Potential indexes include:

```text
jobs(posted_at)

jobs(first_seen_at)

job_source_records(job_source_id, external_job_id)

job_matches(candidate_profile_id, final_score)

tailored_resumes(job_id)

notification_deliveries(status)

discovery_runs(job_source_id, started_at)
```

Indexes should be validated against real query patterns during implementation.

Avoid creating unnecessary indexes because every index increases:

- Storage usage.
- Write cost.
- Update cost.

---

# 8. JSON and Structured Data

Some fields may initially use structured JSON storage.

Potential examples:

- Parsed resume content.
- Source configuration.
- Extracted skill lists.
- Template metadata.

However, data frequently queried, filtered, joined, or constrained should be considered for normalization.

The detailed schema phase must determine:

- Which data belongs in relational tables.
- Which data is appropriate for JSONB.
- Which fields require indexes.

---

# 9. Data Integrity Principles

The database must enforce important business rules where possible.

Examples:

- Foreign keys for ownership.
- Unique source identifiers.
- Unique resume versions.
- Notification idempotency.
- Valid processing statuses.

Business logic alone should not be the only protection against duplicate or invalid data.

---

# 10. Future Schema Extensions

Future versions may introduce:

- Multiple candidate accounts.
- Multiple active job searches.
- Cloud object storage.
- Daily notification digests.
- More source adapters.
- Advanced analytics.
- Semantic embeddings.

These features should not distort the MVP schema prematurely.