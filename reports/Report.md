# Expense Tracker (MoneyFlow) – CI/CD & Cloud Deployment Report

## 1. Introduction
This report summarizes the end-to-end DevOps implementation of the MoneyFlow Expense Tracker application. The focus areas include:
- Automated testing across unit, API, integration, and Postgres layers
- GitHub Actions pipeline automation
- Docker-based containerization
- Azure deployment (Web App + ACR + PostgreSQL Flexible Server)
- Monitoring, health checks, and observability
- Refactoring for maintainability and reliability

The goal was to transform a local FastAPI project into a production-ready, continuously tested, containerized, and cloud-deployed system.

## 2. Testing Strategy & Quality Improvements
### 2.1 Test Suite Structure

| Layer                     | Purpose                                                                          |
|---------------------------|----------------------------------------------------------------------------------|
| Unit tests                | Validate individual functions (e.g., `utils.py`, `auth.py`, validation helpers)  |
| API endpoint tests        | Verify FastAPI routes using `TestClient`                                          |
| Integration tests (SQLite)| Exercise real workflows end-to-end (login, CRUD, categories, summary)            |
| Postgres integration      | Run the app against a real Postgres instance in CI                               |
| Utility tests             | Validate filtering, date normalization, classification logic                     |

### 2.2 Fix: `compute_summary`
- Tests expected the signature `compute_summary(incomes, expenses)` but the code used `compute_summary(transactions)`.
- Refactored to a stable two-argument API with consistent keys (`total_income`, `total_expenses`, `balance`) and monetary rounding.

### 2.3 Authentication Coverage
Added tests for: register, login, wrong password, expired JWT, token for deleted user, change username, change password, and access to protected routes. This improves security confidence.

### 2.4 Postgres Integration Tests
- CI spins up a Postgres 15 service via GitHub Actions `services`.
- Confirms DB readiness, table creation, and CRUD against real Postgres.

### 2.5 Coverage
- Coverage enforced at 70% minimum; current runs exceed 90% locally.

## 3. Continuous Integration (CI)
### 3.1 Pipeline Overview (GitHub Actions)
1. Checkout  
2. Install dependencies  
3. Start Postgres service  
4. Run unit + integration tests  
5. Enforce coverage (`--cov --cov-fail-under=70`)  
6. Docker build  
7. On main: push image to Azure Container Registry  

### 3.2 Outcome
After the `compute_summary` fix, all tests pass, coverage stays high (~94%), and CI on branch `assignment-2` succeeds.

## 4. Continuous Deployment (CD)
### 4.1 Dockerization
- Production Dockerfile based on `python:3.11-slim`, installs deps, runs Uvicorn in production mode, and uses build caching.

### 4.2 Azure Container Registry (ACR)
- Registry: `moneyflowacr.azurecr.io`
- GitHub Secrets store credentials (ACR_NAME, ACR_LOGIN_SERVER, ACR_USERNAME, ACR_PASSWORD, AZURE_WEBAPP_NAME, AZURE_CREDENTIALS).

### 4.3 Deployment Workflow
- On push to `main`: build image → login to ACR → push image → deploy to Azure Web App for Containers.

## 5. Cloud Architecture (Azure)
| Component                                | Purpose                                |
|------------------------------------------|----------------------------------------|
| Azure Web App for Containers             | Hosts the FastAPI app                  |
| Azure Container Registry (ACR)           | Stores Docker images                   |
| Azure Database for PostgreSQL Flexible   | Production database                    |
| Firewall Rules                           | Allow Web App → Postgres               |
| Public Networking                        | Enabled for testing                    |

**Production backend URL:**  
https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net

## 6. Monitoring & Health Checks
### 6.1 `/health`
Returns:
```json
{
  "status": "ok",
  "timestamp": "2025-11-30T20:40:06Z",
  "app": "expense-tracker",
  "version": "0.1.0"
}
```
Used by Azure liveness probes, GitHub deployment checks, and Prometheus scraping.

### 6.2 Prometheus Metrics
- Enabled via `prometheus_fastapi_instrumentator` with `Instrumentator().instrument(app).expose(app, endpoint="/metrics")`.
- Exposes request count, latency histograms, error counts, and path-level performance.

### 6.3 Log Streaming
- Azure Log Stream used to debug startup issues (image arch, ACR auth, Postgres firewall). All resolved during deployment.

## 7. Key Improvements Summary
### 7.1 Functional
- Authentication (login, register, logout), change username/password, JWT session flow, and UI flow from login to dashboard.

### 7.2 Code Refactoring
- `utils.py` rewritten for clarity and correctness; summary logic fixed; date parsing strengthened; classification rules codified.

### 7.3 DevOps
- Automated tests with coverage gate, Dockerized builds, CI/CD, Azure deployment, Prometheus monitoring.

## 8. Conclusion
The project now demonstrates a full DevOps lifecycle: robust code, comprehensive testing (unit/API/integration/Postgres), Docker-based CI/CD, Azure deployment, and live monitoring. It is production-ready, reproducible, testable, and fully automated.

## 9. Screenshots
There is the screenshots folder, if you want to check .
