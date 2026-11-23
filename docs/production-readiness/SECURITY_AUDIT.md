# JobRadar AI — Comprehensive Security Audit & Threat Assessment

**Document Version:** 1.0.0  
**Milestone:** 16 — End-to-End Validation & Deployment Readiness  
**Target Environment:** Local Docker Compose / Cloud Deployment  
**Audit Date:** 2026-11-17  

---

## 1. Executive Summary

A comprehensive security audit of JobRadar AI was conducted covering the API gateway, database queries, file storage mechanisms, background job execution, external third-party integrations, and environment variable management.

### Key Risk Summary
| Threat Domain | Severity | Current Status | Remediation Required |
| :--- | :---: | :---: | :--- |
| **Authentication & Authorization** | **CRITICAL** | Absent on API routes | Reverse proxy auth or JWT middleware required |
| **Server-Side Request Forgery (SSRF)**| **HIGH** | Present in discovery adapters | URL allowlist & private IP restriction required |
| **Cross-Origin Resource Sharing (CORS)**| **MEDIUM** | Configurable via env | Restrict origins in production deployments |
| **File Upload & Path Traversal** | **LOW** | Secured | MIME validation & UUID-isolated storage paths |
| **SQL Injection** | **LOW** | Secured | 100% parameterized SQLAlchemy 2.0 ORM queries |
| **PII & Data Storage Security** | **MEDIUM** | In-transit TLS supported | Enable DB encryption at rest in production |
| **Hardcoded Secrets** | **LOW** | None detected | Environment-variable driven configuration |

---

## 2. Threat Analysis & Vulnerability Findings

### 2.1. Authentication & Authorization (CRITICAL)

#### Vulnerability Description
The FastAPI backend routes under `/api/v1/` contain no authentication or role-based access control middleware. Any HTTP client capable of reaching port 8000 can invoke candidate profile CRUD, resume uploads, tailoring operations, email retries, and pipeline triggers without providing credentials or API keys.

#### Architectural Context
In Milestones 1–15, JobRadar AI was scoped as a single-user local intelligence terminal. A default user and candidate profile are provisioned automatically. While suitable for single-user local deployment behind `localhost`, exposing this port directly to an untrusted or shared network exposes all candidate data.

#### Mandatory Deployment Controls
1. **Private Network Boundary:** For local single-user operation, bind ports strictly to `127.0.0.1` and never publish to `0.0.0.0`.
2. **Reverse Proxy Authentication:** In hosted environments, place JobRadar AI behind an authenticating reverse proxy (e.g., Cloudflare Access, Nginx HTTP Basic Auth, Authelia, or AWS Cognito / OAuth2 Proxy).
3. **Application Middleware (Future Roadmap):** Introduce Bearer JWT or API Key header validation (`HTTPBearer`) in `app/core/dependencies.py`.

---

### 2.2. Server-Side Request Forgery (SSRF) (HIGH)

#### Vulnerability Description
The job discovery subsystem allows configuring external job boards (`GreenhouseAdapter`, `LeverAdapter`) by specifying a `base_url` on the `JobSource` model:
- `GreenhouseAdapter.discover_jobs(base_url=...)`
- `LeverAdapter.discover_jobs(base_url=...)`

If an attacker or malicious user can register or alter a `JobSource` record, they could set `base_url` to:
- `http://169.254.169.254/latest/meta-data/` (AWS Instance Metadata Service)
- `http://10.0.0.0/8` or `http://192.168.1.1/` (Internal network infrastructure)
- `http://localhost:6379` (Local Redis instance)

#### Remediation Plan
1. **Protocol Restriction:** Enforce `https://` only; reject plain `http://`.
2. **Hostname Allowlist:** Validate configured hostnames against approved patterns:
   - Greenhouse: `boards-api.greenhouse.io`
   - Lever: `api.lever.co`
3. **Private IP Disallowance:** Resolve DNS hostnames before initiating HTTP requests using `httpx` and drop requests resolving to `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, or `169.254.169.254`.

---

### 2.3. Cross-Origin Resource Sharing (CORS) (MEDIUM)

#### Current State
The backend uses FastAPI's `CORSMiddleware` configured in `app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Default origins: `["http://localhost", "http://localhost:3000", "http://localhost:5173"]`.

#### Production Recommendation
- Ensure `CORS_ORIGINS` is explicitly defined in `.env` to match the exact production domain (e.g., `https://jobradar.mycompany.com`).
- Never set `CORS_ORIGINS=*` when `allow_credentials=True`.

---

### 2.4. File Upload & Path Traversal Security (LOW RISK)

#### Analysis
Master resume uploads are received via `POST /api/v1/resumes/upload`.

#### Protections in Place
1. **Size Limit:** Enforced at 10 MB via `settings.max_upload_size_bytes`.
2. **MIME Type Validation:** Restricted to `application/pdf` and `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
3. **Storage Isolation:** Files are written using `LocalFileStorage`:
   - Storage keys follow structured paths: `resumes/raw/{candidate_id}/{filename}` and `resumes/tailored/{candidate_id}/{tailored_id}.pdf`.
   - File keys are strictly scoped by candidate profile UUID and generated UUIDs.
   - User-supplied filenames are sanitized and never used directly as absolute filesystem paths.

---

### 2.5. SQL Injection & ORM Safety (LOW RISK)

#### Analysis
- The codebase exclusively utilizes SQLAlchemy 2.0 ORM and `select(...)`, `update(...)`, `delete(...)` constructs.
- All query parameters are bound via parameterized SQL execution in both `asyncpg` and `psycopg` drivers.
- No dynamic SQL string formatting (`f"SELECT ... WHERE id = '{user_input}'"`) was found in any repository or service file.
- Database constraints (check constraints, foreign key cascades, partial unique indexes) enforce structural data integrity at the PostgreSQL engine level.

---

### 2.6. PII & Data Transmission Privacy (MEDIUM)

#### Analysis
JobRadar AI stores candidate PII including full legal name, email, phone number, employment history, and master resumes.

#### Recommendations
1. **In-Transit Encryption:** Always terminate SSL/TLS at the reverse proxy (Nginx / Cloudflare / ALB) using modern TLS 1.3 ciphers.
2. **Database at Rest:** In production cloud deployments (AWS RDS, GCP Cloud SQL, or Azure Database), ensure storage volume encryption (AES-256 / KMS) is enabled.
3. **Email Transmission:** Ensure `SMTP_PORT=587` with STARTTLS or `SMTP_PORT=465` with SSL to encrypt tailored resume transmissions.

---

### 2.7. Secrets Management & Credential Exposure

#### Audit Findings
- No hardcoded API keys, database passwords, or SMTP credentials exist in repository tracking.
- All credentials are read from environment variables via Pydantic `BaseSettings` (`app/core/config.py`).
- `.env` is properly excluded by `.gitignore`.
- `.env.example` provides sanitized template values with no production credentials.

---

## 3. Security Scorecard & Action Items

| Item | Action | Priority | Target Release |
| :--- | :--- | :---: | :---: |
| SEC-01 | Deploy behind authenticating reverse proxy (Nginx / Cloudflare) | Critical | Immediate / Pre-prod |
| SEC-02 | Add hostname allowlist & SSRF check to discovery adapters | High | Patch 1.0.1 |
| SEC-03 | Configure explicit production `CORS_ORIGINS` | Medium | Deployment setup |
| SEC-04 | Enable TLS 1.3 on public web server & SMTP | High | Deployment setup |
| SEC-05 | Implement Redis `requirepass` in production docker-compose | Medium | Deployment setup |

