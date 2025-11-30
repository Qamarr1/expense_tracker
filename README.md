# MoneyFlow — Expense Tracker (FastAPI + Docker + CI/CD + Monitoring)

MoneyFlow is a full-stack FastAPI application for tracking personal income and expenses. It includes authentication, dashboards, charts, filtering, and financial summaries, backed by SQLModel and a production-ready CI/CD pipeline.

## Core  Features
- Add, edit, delete income and expense entries
- Category management (default + custom)
- Financial summary: total income, total expenses, balance
- 30/60-day visual trends (Chart.js)
- Filtering: date range, search, category
- Warnings: large expense and exceeds balance
- Dark, responsive UI with redesigned layout

### Authentication
- Register, login, JWT-based session
- Change username and password
- Logout
- Secure password hashing (Argon2)

### DevOps
- Automated testing pipeline (unit + integration + Postgres)
- Coverage threshold enforced (>= 70%)
- Docker container build
- Deployment to Azure Web App for Containers
- Azure PostgreSQL Flexible Server as production DB
- Prometheus metrics exposed; health check endpoint
- Secrets stored in GitHub Actions secrets

## Project Structure
```
expense_tracker/
├── main.py
├── auth.py
├── models.py
├── schemas.py
├── utils.py
├── tests/
├── monitoring/
├── static/
├── reports/
├── Screenshots/
├── .github/workflows/
├── package.json        
├── package-lock.json           
├── Dockerfile
├── docker-compose.yml
└── README.md
```
Notes:
- `package.json` / `package-lock.json` hold the frontend toolchain (Jest config and JS unit tests).
- `.github/workflows/` contains the CI/CD pipeline.
- `reports/` stores coverage and CI artifacts.
- `Screenshots/` for UI snapshots, and workflow, and azure deployments.
- `static/` contains frontend resources (HTML, JS, CSS).

## Local Development Setup
### 1) Clone
```bash
git clone https://github.com/Qamarr1/expense_tracker.git
cd expense_tracker
```

### 2) Virtual Environment
macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```
Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\activate
```

### 3) Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Run the Application
```bash
uvicorn main:app --reload
```

Key URLs:
| Page              | URL                              |
|-------------------|----------------------------------|
| API root          | http://127.0.0.1:8000            |
| Health Check      | http://127.0.0.1:8000/health     |
| Login             | http://127.0.0.1:8000/login      |
| Dashboard         | http://127.0.0.1:8000/dashboard  |
| Income UI         | http://127.0.0.1:8000/income-ui  |
| Expenses UI       | http://127.0.0.1:8000/expenses-ui|
| API Docs          | http://127.0.0.1:8000/docs       |
| Prometheus Metrics| http://127.0.0.1:8000/metrics    |

## Running Tests
```bash
pytest --cov=./
```
Coverage target: >= 70% (current runs ~94%). Tests cover unit, integration, PostgreSQL service, authentication, categories/transactions, utilities (summary, filtering, classification).

Frontend JS unit tests are configured via Jest in `package.json`:
```bash
npm test
```

## Production Deployment (Azure)
The app is deployed via CI/CD to Azure Web App for Containers.

Production URL:  
https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net

Azure endpoints:
| Page              | URL                                                                           |
|-------------------|-------------------------------------------------------------------------------|
| API root          | https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net  |
| Health            | https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/health |
| Login             | https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/login |
| Dashboard         | https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/dashboard |
| Income UI         | https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/income-ui |
| Expenses UI       | https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/expenses-ui |
| API Docs          | https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/docs |
| Prometheus Metrics| https://moneyflow-web-qamar-crcndma3eggmd0gh.westeurope-01.azurewebsites.net/metrics |

Environment variables (set in Azure Web App → Configuration → Application Settings):
| Variable      | Value                                                    |
|---------------|----------------------------------------------------------|
| DATABASE_URL  | postgresql+psycopg2://USER:PASSWORD@HOST:5432/expense_db |
| SECRET_KEY    | your-secret                                              |
| ACR_USERNAME  | moneyflowacr                                             |
| ACR_PASSWORD  | registry-password                                        |
| TOKEN_URL     | /auth/login                                              |

## Docker
Build:
```bash
docker build -t moneyflow-api .
```
Run:
```bash
docker run -p 8000:8000 moneyflow-api
```

## Deployment (Azure Web App + Azure Container Registry)
1) Build and push:
```bash
az acr login --name moneyflowacr
docker build -t moneyflowacr.azurecr.io/expense_tracker:latest .
docker push moneyflowacr.azurecr.io/expense_tracker:latest
```
2) Configure Azure Web App image:
```
moneyflowacr.azurecr.io/expense_tracker:latest
```
3) Set environment variables:
```
DATABASE_URL=postgresql+psycopg2://USERNAME:PASSWORD@HOST:5432/expense_db
SECRET_KEY=<your-secret>
ACR_USERNAME=moneyflowacr
ACR_PASSWORD=<registry password>
```

## CI/CD (GitHub Actions)
Workflow: `.github/workflows/ci.yml`
- Trigger: push / pull_request
- Steps: start PostgreSQL service, install deps, run tests + coverage, build Docker image
- If branch = main: deploy to Azure Web App

Pipeline steps:
1. Start PostgreSQL service  
2. Install dependencies  
3. Run unit + integration tests  
4. Enforce coverage >= 70%  
5. Build Docker image  
6. On main branch: login to ACR, push image, deploy to Azure Web App  

## Monitoring
- `/health` for readiness checks
- `/metrics` for Prometheus (request counts, latency, errors, uptime)

The application is production-ready, with automated testing, containerized delivery, and Azure deployment with monitoring.***
