# JobRadar AI — Email Notification & Reliable Delivery Architecture (Milestone 9)

## 1. Executive Summary

Milestone 9 introduces the immediate, asynchronous, and reliable candidate notification system into JobRadar AI. When a candidate profile achieves a qualified job match (evaluated deterministically and semantically) and tailored resume generation succeeds with valid PDF artifacts, the notification pipeline dispatches an actionable alert email with the tailored resume PDF attached.

---

## 2. Architecture Overview

```text
Qualified Match + Tailored PDF Complete
                    │
                    ▼
┌───────────────────────────────────────────────┐
│ Tailoring Task Worker (Queue: tailoring)      │
│  - Verifies TailoredResume status == COMPLETED │
│  - Calls create_or_get_delivery_for_tailored_resume
└───────────────────────┬───────────────────────┘
                        │
                        ▼ (Enqueue)
┌───────────────────────────────────────────────┐
│ Celery Queue: notifications                   │
│  - Task: send_email_notification_task         │
└───────────────────────┬───────────────────────┘
                        │
                        ▼ (Worker picks up)
┌───────────────────────────────────────────────┐
│ Notification Worker                           │
│  1. Acquire Redis Lock (120s TTL)             │
│     lock:notification_delivery:{id}           │
│  2. Read Delivery & Relations (DB)            │
│  3. Verify State: PENDING or FAILED           │
│  4. Read & Validate Tailored PDF Binary       │
│  5. Render Responsive HTML + Plaintext Email  │
│  6. Transition Status -> PROCESSING           │
│  7. Dispatch via EmailProvider (SMTP / Mock)  │
│  8. Transition Status -> SENT + Record SentAt │
└───────────────────────────────────────────────┘
```

---

## 3. Database Schema & Migration

### Migration Reference
`backend/alembic/versions/20261105_0009_notification_deliveries.py`

### Table: `notification_deliveries`

| Column | Type | Constraints / Modifiers | Description |
|---|---|---|---|
| `id` | `UUID` | Primary Key, default `uuid4` | Unique delivery identifier |
| `candidate_profile_id` | `UUID` | FK `candidate_profiles.id` ON DELETE CASCADE | Target candidate |
| `job_id` | `UUID` | FK `jobs.id` ON DELETE CASCADE | Associated canonical job |
| `job_match_id` | `UUID` | FK `job_matches.id` ON DELETE CASCADE | Qualified match score and insights |
| `tailored_resume_id` | `UUID` | FK `tailored_resumes.id` ON DELETE SET NULL | Tailored PDF resume record |
| `recipient_email` | `VARCHAR(255)` | NOT NULL | Delivery destination email |
| `status` | `notification_delivery_status_enum` | NOT NULL, default `PENDING` | `PENDING`, `PROCESSING`, `SENT`, `FAILED` |
| `attempt_count` | `INTEGER` | NOT NULL, default `0` | Execution attempts count |
| `max_attempts` | `INTEGER` | NOT NULL, default `3` | Maximum retry attempts |
| `last_attempt_at` | `TIMESTAMPTZ` | NULL | Timestamp of most recent attempt |
| `sent_at` | `TIMESTAMPTZ` | NULL | Timestamp of successful transmission |
| `provider` | `VARCHAR(64)` | NOT NULL, default `'mock'` | Email provider used (`smtp`, `mock`) |
| `provider_message_id` | `VARCHAR(255)` | NULL | Upstream message identifier / SMTP Message-ID |
| `failure_reason` | `TEXT` | NULL | Error summary on failure |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, default UTC now | Audit timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, default UTC now | Audit timestamp |

### Indexes & Constraints
- Compound Unique Index: `uq_notification_deliveries_job_recipient` on `(job_id, recipient_email)`.
- Status Index: `ix_notification_deliveries_status` on `(status)`.
- Candidate Profile Index: `ix_notification_deliveries_candidate_profile_id` on `(candidate_profile_id)`.
- Job Index: `ix_notification_deliveries_job_id` on `(job_id)`.

---

## 4. Idempotency Guarantees & Concurrency Control

The notification engine provides dual-layer protection against duplicate emails:

1. **Persistent Database-Level Idempotency:**
   The unique constraint `UNIQUE (job_id, recipient_email)` guarantees that only one notification record can exist for a candidate and job combination. `create_or_get_delivery_for_tailored_resume` checks for existing records before insertion and returns the active delivery.
2. **Distributed Concurrency Lock:**
   A Redis key `lock:notification_delivery:{id}` with a 120-second TTL is acquired before execution begins. If a concurrent worker attempts to process the same notification, it immediately aborts without re-transmitting.
3. **State Guard:**
   Before dispatch, the worker verifies that the delivery is in `PENDING` or `FAILED` state. If already `SENT`, the pipeline exits immediately as a no-op.

---

## 5. Distributed Systems Semantics & Delivery Trade-Offs

Standard Internet SMTP is fundamentally an **at-least-once** communication protocol. While the JobRadar AI architecture guarantees:
- Exactly-once database record generation per `(job_id, recipient_email)`
- Exactly-once task lock acquisition via Redis
- Pre-dispatch state verification

If an unrecoverable worker crash or network timeout occurs after SMTP socket acknowledgment but before the database `SENT` state commit, retry mechanisms could retransmit. This distributed systems trade-off is documented and managed by recording the RFC 2822 `Message-ID` and committing state transitions immediately upon socket confirmation.

---

## 6. Email Content & ATS Resume Attachment

- **Responsive HTML Template:** Clean slate-styled notification rendered with XSS-safe escaping via `html.escape`.
- **Match Insights:** Displays canonical job title, company name, match score percentage, recommendation badge, and AI match explanation.
- **Action Links:** Direct link to canonical application URL.
- **Attachment Delivery:** The tailored PDF resume is validated for integrity, magic number bytes (`%PDF`), and SHA-256 checksum before being attached as a standard MIME part (`application/pdf`).

---

## 7. REST API Endpoints

All endpoints follow RFC 7807 structured error responses:

- `GET /api/v1/notifications`: Paginated list of deliveries, filterable by candidate and status.
- `GET /api/v1/notifications/{id}`: Full delivery details including provider message ID and timestamps.
- `POST /api/v1/notifications/{id}/retry`: Manual or operator retry for a delivery in `FAILED` state.

