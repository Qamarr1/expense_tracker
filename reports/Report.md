# Expense Tracker (MoneyFlow) – CI/CD & Cloud Deployment Report

## 1. Introduction
This report documents the end-to-end DevOps transformation of MoneyFlow, a full-stack Expense Tracker built with FastAPI, JavaScript, HTML/CSS, and PostgreSQL. The project started as a local SQLite app with minimal automation; it now runs as a production-ready, containerized, cloud-deployed, and continuously tested system.

Goals:
- Refactor code for maintainability and SOLID compliance.
- Achieve strong automated testing (unit, API, integration, Postgres) with a coverage gate (>= 70%).
- Build a CI/CD pipeline (GitHub Actions) that builds, tests, and deploys.
- Containerize with Docker and publish images to Azure Container Registry (ACR).
- Deploy to Azure Web App for Containers, backed by Azure PostgreSQL Flexible Server.
- Add observability: health checks, Prometheus metrics, and logging.

## 2. Architecture Overview
MoneyFlow is now three cooperating pieces: a stateless FastAPI backend, a managed Postgres database, and a container registry.

### 2.1 Textual System Diagram
```
┌─────────────────────┐      ┌──────────────────────────┐
│     Developer       │      │        GitHub            │
│  (code, commits)    │----->│ Repo + Actions Workflow  │
└─────────────────────┘      └───────────┬──────────────┘
                                        │
                                        ▼
                               ┌────────────────┐
                               │  CI Pipeline   │
                               │  (Tests +      │
                               │   Coverage +   │
                               │   Docker Build)│
                               └───────┬────────┘
                                       │ if main
                                       ▼
                              ┌───────────────────┐
                              │ Azure Container   │
                              │    Registry (ACR) │
                              └─────────┬─────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │ Azure Web App (Container│
                            │  Pulls Image from ACR   │
                            └─────────┬───────────────┘
                                      │
                                      ▼
                       ┌───────────────────────────┐
                       │ Azure PostgreSQL Flexible │
                       │   Server (Production DB)  │
└───────────────────────────┘
```

### 2.2 Layered Stack (alternative view)
```
┌───────────────────────────┐
│        Front-End UI        │
│  (HTML/CSS/JS from /static)│
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│     FastAPI Application    │
│  Auth, Income, Expenses,   │
│  Categories, Summary       │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│    Database (Postgres)    │
│   SQLModel ORM interfaces  │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│  Docker Container (Uvicorn)│
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Azure Deployment Pipeline  │
│   ACR → Web App → Logs     │
└───────────────────────────┘
```

### 2.2 Components
- Backend: FastAPI, stateless, containerized; serves API and HTML; JWT authentication.
- Database: Azure PostgreSQL Flexible Server; firewall rules restricted to Web App outbound IPs and developer IPs.
- Registry: Azure Container Registry; stores versioned Docker images pushed from CI.

### 2.3 High-Level System Architecture 
```
                            ┌──────────────────────────┐
                            │  GitHub Repository       │
                            │  (main + assignment-2)   │
                            └───────────┬──────────────┘
                                        │ (push / PR)
                                        ▼
                            ┌──────────────────────────┐
                            │  GitHub Actions: CI Job  │
                            │  - Start PostgreSQL svc  │
                            │  - Install deps          │
                            │  - Run 80+ tests         │
                            │  - Enforce 70% coverage  │
                            │  - Build Docker image    │
                            └───────────┬──────────────┘
                             if main    │
                                        ▼
                            ┌──────────────────────────┐
                            │ Azure Container Registry │
                            │ moneyflowacr.azurecr.io  │
                            │ Stores expense_tracker   │
                            │ image:latest             │
                            └───────────┬──────────────┘
                                        │
                                        ▼
                       ┌──────────────────────────────────────┐
                       │ Azure Web App for Containers         │
                       │ moneyflow-web-qamar                  │
                       │ Pulls latest ACR image → runs app    │
                       └──────────────────┬───────────────────┘
                                          │
                                          ▼
                       ┌──────────────────────────────────────┐
                       │ Azure PostgreSQL Flexible Server     │
                       │ Production DB for all transactions   │
                       └──────────────────────────────────────┘
```

### 2.4 Azure Resource Architecture
| Resource                          | Name                     | Purpose                              |
|-----------------------------------|--------------------------|--------------------------------------|
| Azure Container Registry          | moneyflowacr             | Stores Docker images                 |
| Azure Web App for Containers      | moneyflow-web-qamar      | Runs the API/UI container            |
| Azure PostgreSQL Flexible Server  | moneyflow-postgres       | Production relational database       |
| GitHub Actions Secrets            | ACR_LOGIN_SERVER, ACR_USERNAME, ACR_PASSWORD, AZURE_CREDENTIALS | Secure deployment |
| GitHub Branches                   | assignment-2 (dev) → main (prod) | Controls CI/CD promotion      |

### 2.5 Deployment URL (Production)
All production components share:  
https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net

Key endpoints: `/login`, `/dashboard`, `/income-ui`, `/expenses-ui`, `/settings-ui`, `/api/*`, `/metrics`, `/health`, `/docs`.

## 3. Refactoring and Code Quality
Key refactors applied before and during CI/CD enablement:
- Decomposed long functions into focused helpers: `compute_summary`, `normalize_iso_date`, `filter_transactions`, `classify_expense`.
- Standardized error handling with FastAPI `HTTPException` (400/401/404) instead of ad-hoc prints.
- Consistent date handling (ISO-8601) via `normalize_iso_date`.
- Authentication rewrite: Argon2 hashing, JWT with expiration, change-password and change-username flows, token refresh on username change, `/auth/me` correctness.
- Routing/UI cleanup: coherent routes `/login`, `/dashboard`, `/income-ui`, `/expenses-ui`, `/settings-ui`; root redirects to `/login`.

Other cleanups:
- Reduced duplication in endpoints (shared helpers like `save_and_refresh`, `get_category_or_400`).
- Clear defaults and seeding for categories to avoid flaky startup/state.
- Stronger type hints and docstrings for maintainability.

### 3.1 Backend Logic Improvements (deep detail)
**Summary logic (compute_summary)**  
Problem: tests expected `compute_summary(incomes, expenses)`; code assumed `compute_summary(transactions)` leading to TypeError/KeyError and inconsistent rounding.  
Fix: explicit two-list interface, financial rounding, stable keys:
```
{
  "income_total": ...,
  "expense_total": ...,
  "total_income": ...,
  "total_expenses": ...,
  "balance": ...
}
```
Benefits: deterministic, idempotent, UI/test alignment, avoids float drift, no category/timestamp dependency.

**Authentication rewrite**  
- Argon2id hashing, JWT with expiration, `/auth/me`, change-password (requires old password), change-username (refresh JWT), OAuth2PasswordBearer 401 handling.  
- Addresses plaintext passwords, missing session invalidation, absent update flows, and missing security tests.

**Category logic**  
- Duplicate prevention, existence checks before expenses, ON CONFLICT handling for Postgres, validated `CategoryUpdate`.

**Transaction logic**  
- Validates positive amounts, ISO dates, partial updates; uses `save_and_refresh`; consistent CRUD behavior improves testability.

## 4. Testing (Unit, API, Integration, Database)
Testing is layered to cover logic, APIs, end-to-end flows, and Postgres:

| Layer              | Purpose                                         | Tools                    |
|--------------------|-------------------------------------------------|--------------------------|
| Unit               | Core logic (summary, utils, auth helpers)       | pytest                   |
| API                | FastAPI routes via TestClient                   | pytest + TestClient      |
| Auth               | Register, login, expired/tampered tokens        | pytest + TestClient      |
| Integration SQLite | Full flows: register → login → CRUD → summary   | pytest + TestClient      |
| Postgres           | Real Postgres service in CI                     | GitHub Actions services  |

Key fix: `compute_summary` now accepts `(incomes, expenses)` and returns stable keys (`total_income`, `total_expenses`, `balance`), eliminating TypeErrors and aligning UI and tests. Coverage target is 70%; current runs exceed 90%.

Authentication test coverage includes: duplicate username, wrong password, invalid/expired/tampered tokens, `/auth/me` with deleted user, change-password (forces re-login), change-username (token refresh).

Additional test highlights:
- Postgres integration verifies schema, CRUD, categories, summary with real DB in CI.
- Coverage ~93% (branch + functional paths), including error paths.

## 5. Continuous Integration (CI)
GitHub Actions workflow (`.github/workflows/ci.yml`):
1) Checkout code
2) Setup Python 3.12
3) Install dependencies
4) Start Postgres service container  
5) Run tests with coverage gate (`--cov-fail-under=70`)  
6) Build Docker image
7) If branch == main: login to ACR, push image, deploy to Azure Web App

Expanded pipeline rationale:
- Postgres service container ensures parity with production DB.
- Coverage gate prevents regressions slipping into main.
- Docker build in CI validates the production image on every push.
- Main-branch guard (login → push → deploy) keeps production in sync with green builds only.

Pipeline diagram:
```
┌────────────┐     ┌───────────────┐     ┌────────────┐
│   GitHub    │ -->│ Actions (CI)   │ --> │ Docker Build│
└────────────┘     └──────┬────────┘     └───────┬────┘
                           │ main branch          │
                           ▼                      ▼
                    ┌──────────────┐      ┌────────────────┐
                    │   ACR Push    │      │ Azure Web App  │
                    └──────┬───────┘      └────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Production   │
                    └──────────────┘
```

## 6. Docker & Containerization
- Base image: `python:3.11-slim`
- Layer caching, pinned versions, no-cache installs
- Copies only necessary files
- Runs Uvicorn bound to `0.0.0.0`
- Produces a small, fast-to-build image suitable for CI and cloud deployment

## 7. Azure Cloud Deployment
Resources:
- Azure Web App for Containers (runs the FastAPI container)
- Azure Container Registry (stores images)
- Azure PostgreSQL Flexible Server (production DB)
- Networking: outbound IPs from Web App allowed in Postgres firewall; optional developer IP allow-list

Firewall/debugging notes:
- Added Web App outbound IPs to Postgres firewall.
- Temporarily opened 0.0.0.0/0 during early testing, then tightened.
- Resolved ACR auth failures (admin user enabled + GitHub Secrets).
- Resolved image arch mismatch (ARM build vs AMD64 runtime) by building in CI on amd64.

Environment variables (Azure Web App → Configuration):
- `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/expense_db`
- `SECRET_KEY=<your-secret>`
- `ACR_USERNAME=moneyflowacr`
- `ACR_PASSWORD=<registry-password>`
- `TOKEN_URL=/auth/login`

Production URLs:
- API root: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net
- Health: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/health
- Login: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/login
- Dashboard: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/dashboard
- Income UI: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/income-ui
- Expenses UI: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/expenses-ui
- API Docs: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/docs
- Metrics: https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/metrics

## 8. Monitoring & Observability
- `/health`: readiness/liveness for Azure probes and CI checks.
- `/metrics`: Prometheus via `Instrumentator().instrument(app).expose(app, endpoint="/metrics")`; includes request counts, latency histograms, error rates, per-route metrics.
- Azure Log Stream used to debug ACR auth, arch mismatches (arm64 vs amd64), Postgres connectivity, and startup sequencing.

Telemetry targets:
- Request count, latency, error rate, per-path breakdown.
- Uptime and process metrics (via Prometheus client).
- Health endpoint consumed by Azure Web App and CI sanity checks.

## 9. Frontend and UI
- Dark, responsive UI; clearer flows for login, dashboard, income/expenses, settings.
- Charts for 30/60-day trends; improved filters with From/To labels.
- Settings page: tabbed UX for username/password changes; token refresh on username change; logout.

## 10. Final Improvements Summary
- Code quality: modular utilities, standardized errors, robust authentication, cleaner structure.
- Testing: >90% coverage across unit, API, integration (SQLite), and Postgres.
- CI/CD: automated pipeline with coverage gate, Docker build, ACR push, Azure deployment.
- Cloud: secure Postgres, containerized backend, end-to-end flows through UI.
- Monitoring: health endpoints, Prometheus metrics, logs; Azure insights ready.

## 11. Conclusion
MoneyFlow moved from a local prototype to a production-grade DevOps application: scalable, testable, secure, observable, automated, and cloud-ready, demonstrating the full lifecycle from code to monitored deployment.

## 12. Screenshots
Place UI and pipeline images under `Screenshots/` and reference them here (CI runs, ACR panel, Azure Web App logs, health endpoint, UI pages, coverage reports).


