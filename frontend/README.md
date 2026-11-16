# JobRadar AI — Frontend Application (Milestone 11)

Production-grade React + TypeScript frontend web console for **JobRadar AI**, providing real-time telemetry, candidate profile management, and end-to-end pipeline run orchestration.

---

## 1. Technology Stack

- **Runtime & Bundler:** Vite 6 + React 18 + TypeScript 5
- **Styling:** Tailwind CSS 3 (JobRadar AI design system: Deep Slate `#0F172A` with Blue 600 `#2563EB` interactive accent)
- **Routing:** React Router v6 (`createBrowserRouter`)
- **Server State & Caching:** TanStack Query v5 (`@tanstack/react-query`)
- **Client UI State:** Zustand v5 (lightweight sidebar & drawer state)
- **Forms & Validation:** React Hook Form + Zod (`@hookform/resolvers`)
- **HTTP Client:** Centralized Axios instance with RFC 7807 Problem Details interceptors
- **Icons:** Lucide React
- **Testing:** Vitest + React Testing Library + `@testing-library/jest-dom` + jsdom

---

## 2. Directory Layout & Architecture

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layouts/            # Application Shell (Sidebar, Header, AppLayout)
│   │   ├── providers/          # React Query and theme context providers
│   │   └── router/             # React Router routing configuration
│   ├── components/
│   │   ├── ui/                 # Reusable headless UI (Button, Card, Badge, Input, Textarea, Alert, Spinner)
│   │   └── common/             # Common composite patterns (PageHeader, Breadcrumbs, EmptyState, ErrorState, LoadingState)
│   ├── features/
│   │   ├── dashboard/          # Dashboard telemetry cards (Candidate, Pipeline, Health)
│   │   ├── candidate/          # Candidate profile card, preferences, verified skills, and edit form
│   │   ├── pipeline/           # Pipeline runs table, detail modal, trigger modal, status badges
│   │   └── placeholder/        # Clean milestone placeholder pages (Discovery, Matches, Resumes, Notifications, Settings)
│   ├── hooks/                  # TanStack Query custom hooks (useCandidateProfile, usePipelineRuns, useSystemHealth)
│   ├── lib/                    # Core utilities (api-client.ts, query-client.ts, utils.ts)
│   ├── services/               # Centralized typed API service contracts
│   ├── stores/                 # Zustand UI state stores
│   ├── styles/                 # Tailwind CSS styles and custom scrollbar
│   ├── test/                   # Vitest setup and DOM mocks
│   └── types/                  # Strict TypeScript contracts matching backend Pydantic models
├── index.html                  # HTML5 entry document
├── package.json                # Dependencies and npm scripts
├── tailwind.config.js          # Design tokens and JobRadar AI brand palette
├── tsconfig.json               # Strict TypeScript configuration
└── vite.config.ts              # Vite bundler, proxy to localhost:8000, and Vitest configuration
```

---

## 3. Environment Configuration

Copy the example environment template into `.env`:

```bash
cp .env.example .env
```

| Variable | Default Value | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Base URL prefix for backend REST API. Proxied to `http://localhost:8000` in dev mode. |
| `VITE_APP_NAME` | `JobRadar AI` | Application brand name displayed in header and page titles. |
| `VITE_REQUEST_TIMEOUT_MS` | `15000` | HTTP request timeout in milliseconds before triggering timeout error. |

---

## 4. Development & Build Commands

All commands should be executed from the `frontend/` directory:

```bash
# 1. Install dependencies
npm install

# 2. Start local Vite development server (with hot module replacement)
npm run dev

# 3. Run strict TypeScript typecheck
npm run typecheck

# 4. Run ESLint code quality analysis
npm run lint

# 5. Run automated Vitest test suite
npm run test

# 6. Run Vitest in interactive watch mode
npm run test:watch

# 7. Compile production bundle
npm run build
```

Production build artifacts are compiled into `frontend/dist/`.

---

## 5. Backend Integration & RFC 7807 Error Handling

The application communicates with the FastAPI backend via a centralized Axios instance configured in [`src/lib/api-client.ts`](src/lib/api-client.ts):

- **Relative Proxying:** In development, Vite proxies `/api` and `/health` requests to `http://127.0.0.1:8000`, eliminating CORS obstacles.
- **RFC 7807 Problem Details:** If the backend returns validation errors (422) or domain exceptions (404, 409, 500), the response interceptor automatically parses the `ProblemDetails` object:
  ```json
  {
    "type": "https://api.jobradar.ai/v1/errors/validation-error",
    "title": "Validation Error",
    "status": 422,
    "detail": "Full name cannot be blank or whitespace only.",
    "invalid_params": [{ "name": "full_name", "reason": "...", "type": "..." }]
  }
  ```
  The resulting `ApiError` is surfaced directly in form input error messages and alert banners.
- **Cache Invalidation:** Mutations (e.g. updating a profile or triggering a pipeline run) automatically invalidate corresponding TanStack Query caches, guaranteeing instant UI synchronization without manual refetches.
- **Polling:** Active pipeline runs automatically poll every 4 seconds until reaching a terminal state (`COMPLETED`, `FAILED`, `CANCELLED`).

