# JobRadar AI — Backup & Disaster Recovery Runbook

**Document Version:** 1.0.0  
**Milestone:** 16 — End-to-End Validation & Deployment Readiness  
**Target:** PostgreSQL 16, Redis 7, Local File Storage  
**Date:** 2026-11-17  

---

## 1. Objectives & Recovery Targets

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Recovery Point Objective (RPO)** | **< 1 hour** | Maximum acceptable data loss duration in the event of disaster. |
| **Recovery Time Objective (RTO)** | **< 30 minutes** | Maximum allowable duration to restore full operational service. |

---

## 2. Backup Strategy by Component

```
+---------------------------------------------------------------------------------+
|                               JobRadar AI Storage                               |
+-----------------------+---------------------------------+-----------------------+
                        |                                 |
                        v                                 v
        +-------------------------------+  +-------------------------------+
        |     PostgreSQL 16 Database     |  |      Local File Storage       |
        |  - Candidate Profiles         |  |  - Raw Uploaded Master Resumes|
        |  - Job Catalog & Matches      |  |  - Tailored ATS PDF Documents |
        |  - Tailored Content & Logs    |  +---------------+---------------+
        +---------------+---------------+                  |
                        |                                  |
            pg_dump (Custom / Gzip)                  tar / rsync / S3
                        v                                  v
        +------------------------------------------------------------------+
        |                 Offsite Encrypted Backup Storage                 |
        |              (AWS S3 / GCP Cloud Storage / NAS)                  |
        +------------------------------------------------------------------+
```

---

## 3. PostgreSQL Database Backup & Restore

### 3.1. Automated Daily Full Backup (`pg_dump`)

Execute a compressed custom-format dump using Docker Compose:
```bash
# Create timestamped dump
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups/postgres"
mkdir -p "${BACKUP_DIR}"

docker compose exec -T postgres pg_dump -U postgres -d jobradar_ai -Fc > "${BACKUP_DIR}/jobradar_ai_${TIMESTAMP}.dump"
```

To create a plain compressed SQL file:
```bash
docker compose exec -T postgres pg_dump -U postgres -d jobradar_ai | gzip > "${BACKUP_DIR}/jobradar_ai_${TIMESTAMP}.sql.gz"
```

### 3.2. Database Restoration Procedure

#### Step 1: Terminate Active Connections
Before restoration, stop backend and worker containers to terminate active connection pools:
```bash
docker compose stop backend worker beat
```

#### Step 2: Restore from Dump File
To restore from a custom-format dump (`.dump`):
```bash
docker compose exec -T postgres pg_restore -U postgres -d jobradar_ai --clean --if-exists < "${BACKUP_DIR}/jobradar_ai_20261117_120000.dump"
```

To restore from a gzip SQL archive (`.sql.gz`):
```bash
gunzip -c "${BACKUP_DIR}/jobradar_ai_20261117_120000.sql.gz" | docker compose exec -T postgres psql -U postgres -d jobradar_ai
```

#### Step 3: Verify Migration Version
Confirm that Alembic schema revision matches expectations:
```bash
docker compose run --rm backend alembic current
```

#### Step 4: Restart Application Services
```bash
docker compose start backend worker beat
```

---

## 4. Local File Storage Backup & Restore

JobRadar AI stores candidate master resumes and generated PDFs in `/app/storage`:
- `/app/storage/resumes/raw/{candidate_id}/{filename}`: Original PDF/DOCX master resumes.
- `/app/storage/resumes/tailored/{candidate_id}/{tailored_id}.pdf`: ATS-tailored generated PDFs.

### 4.1. Backup Procedure
Archive the shared Docker volume:
```bash
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups/storage"
mkdir -p "${BACKUP_DIR}"

# Archive directly from volume mount or backend container
docker compose exec -T backend tar -czf - -C /app storage > "${BACKUP_DIR}/storage_${TIMESTAMP}.tar.gz"
```

### 4.2. Restore Procedure
Restore the file storage archive into the volume:
```bash
docker compose stop backend worker beat

cat "${BACKUP_DIR}/storage_20261117_120000.tar.gz" | docker compose exec -T backend tar -xzf - -C /app

docker compose start backend worker beat
```

---

## 5. Redis State & Task Queue Resilience

### 5.1. Append-Only File (AOF)
In `docker-compose.yml`, Redis is started with:
```yaml
command: ["redis-server", "--appendonly", "yes"]
```
This forces Redis to log every write operation to disk in `/data/appendonly.aof`, guaranteeing minimal message loss if the container terminates abruptly.

### 5.2. Disaster Recovery for Redis
Redis queues (`discovery`, `processing`, `tailoring`, `notifications`) hold transient task state. In the event of catastrophic volume destruction:
1. Re-initialize Redis container (`docker compose up -d redis`).
2. The database state remains the single source of truth:
   - Resumes with `processing_status = 'PENDING'` can be re-parsed.
   - Notifications with `status = 'PENDING'` or `status = 'FAILED'` can be re-queued via `POST /api/v1/notifications/{id}/retry`.
   - Pipeline runs with `status = 'PENDING'` can be re-executed via `POST /api/v1/pipeline/runs/{id}/execute`.

---

## 6. Complete Disaster Recovery Simulation (Drill)

To simulate complete infrastructure recovery from backups:

```bash
# 1. Stop and remove all containers and volumes (Destructive Test)
docker compose down -v

# 2. Re-create base infrastructure
docker compose up -d postgres redis

# 3. Restore database schema and data from backup
cat /backups/postgres/jobradar_ai_latest.dump | docker compose exec -T postgres pg_restore -U postgres -d jobradar_ai --clean --if-exists

# 4. Restore file storage volume
docker compose run --rm -v storage_data:/target busybox sh -c "tar -xzf /backups/storage_latest.tar.gz -C /target"

# 5. Launch full application stack
docker compose --profile full up -d

# 6. Verify health probes
curl http://localhost:8000/ready
# Expected: {"status":"ready","database":"healthy","redis":"healthy"}
```

