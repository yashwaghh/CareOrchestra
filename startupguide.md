# CareOrchestra — Startup Guide

A step-by-step guide to get CareOrchestra running from a fresh clone through local development, mock-data testing, and production deployment on Google Cloud Run.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Clone the Repository](#2-clone-the-repository)
3. [Python Environment Setup](#3-python-environment-setup)
4. [Environment Configuration](#4-environment-configuration)
5. [Google Cloud Setup](#5-google-cloud-setup)
6. [BigQuery Initialization](#6-bigquery-initialization)
7. [MCP Toolbox Setup (Optional)](#7-mcp-toolbox-setup-optional)
8. [Run the Application](#8-run-the-application)
9. [Run with Mock Data](#9-run-with-mock-data)
10. [Running Tests](#10-running-tests)
11. [Production Deployment (Cloud Run)](#11-production-deployment-cloud-run)
12. [CI/CD with GitHub Actions](#12-cicd-with-github-actions)
13. [Environment Variables Reference](#13-environment-variables-reference)
14. [Project Structure Reference](#14-project-structure-reference)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Prerequisites

Make sure the following are installed and available on your system before starting:

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Python | 3.9+ | Runtime |
| pip | latest | Package installer |
| Git | any | Clone the repo |
| Google Cloud SDK (`gcloud`) | latest | GCP access, BigQuery, Cloud Run |
| Docker | latest | Container builds (production only) |

A **Google Cloud Project** with billing enabled is required for BigQuery, Gmail, Calendar, and Cloud Run integrations.

---

## 2. Clone the Repository

```bash
git clone https://github.com/yashwaghh/CareOrchestra.git
cd CareOrchestra
```

---

## 3. Python Environment Setup

Create and activate an isolated virtual environment, then install all dependencies.

```bash
# Create the virtual environment
python -m venv care-env

# Activate it
# macOS / Linux:
source care-env/bin/activate
# Windows (PowerShell):
# .\care-env\Scripts\Activate.ps1

# Install application dependencies
pip install -r requirements.txt

# (Optional) Install developer tools (linters, type checker, extra test utilities)
pip install -e ".[dev]"
```

> **Tip:** The `care-env/` directory is already in `.gitignore`. Keep it in the project root so the `source care-env/bin/activate` command in the README works out of the box.

---

## 4. Environment Configuration

CareOrchestra is configured entirely through environment variables loaded from a `.env` file.

```bash
# Copy the example template
cp .env.example .env
```

Open `.env` and fill in the values for your environment. The most important fields for a first run are:

```env
# Your Google Cloud project ID
GCP_PROJECT_ID=your-gcp-project-id

# Set to true to skip real GCP calls during local development
USE_MOCK_DATA=true
GMAIL_USE_MOCK=true
CALENDAR_USE_MOCK=true

# Gemini API key (from Google AI Studio or Vertex AI)
GOOGLE_API_KEY=your-google-api-key
```

> For a full list of every variable and its meaning see [Section 13 – Environment Variables Reference](#13-environment-variables-reference).

---

## 5. Google Cloud Setup

Skip this section if you are running in fully mock mode (`USE_MOCK_DATA=true`).

### 5.1 Authenticate the `gcloud` CLI

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 5.2 Enable Required APIs

```bash
gcloud services enable \
  bigquery.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  gmail.googleapis.com \
  calendar-json.googleapis.com
```

### 5.3 Application Default Credentials (ADC)

Local code uses ADC to call GCP services:

```bash
gcloud auth application-default login
```

For service account authentication (CI/CD or production), create a key and export it:

```bash
gcloud iam service-accounts create care-orchestra-sa \
  --display-name "CareOrchestra Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:care-orchestra-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud iam service-accounts keys create key.json \
  --iam-account=care-orchestra-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com

export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/key.json"
```

---

## 6. BigQuery Initialization

Skip this section if `USE_MOCK_DATA=true`.

### 6.1 Create Dataset and Tables, Load Seed Data

```bash
chmod +x infra/scripts/setup_bigquery.sh
./infra/scripts/setup_bigquery.sh YOUR_PROJECT_ID
```

This single script:
- Creates the `careorchestra` dataset in BigQuery.
- Creates all required tables: `patients`, `vitals`, `medications`, `alerts`, `doctors`, `nurses`, `family_members`.
- Loads CSV seed files from `data/seed/` (patients, vitals, medications, alerts, appointments, medication logs).

### 6.2 Custom Parameters (Optional)

```bash
# Signature: setup_bigquery.sh <PROJECT_ID> [DATASET_NAME] [LOCATION] [SEED_DIR]
./infra/scripts/setup_bigquery.sh my-project careorchestra EU data/seed
```

### 6.3 Verify

```bash
bq ls YOUR_PROJECT_ID:careorchestra
```

---

## 7. MCP Toolbox Setup (Optional)

The MCP Toolbox exposes BigQuery data to agents over the Model Context Protocol.

```bash
chmod +x infra/scripts/setup_toolbox.sh
./infra/scripts/setup_toolbox.sh          # downloads binary to mcp/toolbox/
```

Start the MCP server:

```bash
cd mcp/toolbox
./toolbox --tools-file="tools.yaml"
```

Verify it is running:
- `http://localhost:5000/api/toolset` — lists registered tools
- `http://localhost:5000/ui` — interactive query interface

---

## 8. Run the Application

CareOrchestra exposes a **FastAPI** HTTP server as its primary entry point.

```bash
# Make sure the virtual environment is active
source care-env/bin/activate

# Run from the project root (PYTHONPATH must include the root)
PYTHONPATH=. uvicorn apps.api.main:app --reload
```

The API is now available at `http://localhost:8000`.

To run the raw ADK application (direct Python, no HTTP layer):

```bash
python -m apps.adk_app.app
```

---

## 9. Run with Mock Data

Mock mode lets you develop and test locally without any GCP resources.

1. Ensure `.env` has:
   ```env
   USE_MOCK_DATA=true
   GMAIL_USE_MOCK=true
   CALENDAR_USE_MOCK=true
   ```
2. Start the server:
   ```bash
   PYTHONPATH=. uvicorn apps.api.main:app --reload
   ```
3. Trigger demo scenarios using the payloads in `data/mock_payloads/`:

   **Scenario 1 – High Blood Pressure**
   ```bash
   curl -X POST http://localhost:8000/events \
     -H "Content-Type: application/json" \
     -d @data/mock_payloads/high_bp_event.json
   ```

   **Scenario 2 – Missed Medication**
   ```bash
   curl -X POST http://localhost:8000/events \
     -H "Content-Type: application/json" \
     -d @data/mock_payloads/missed_medication.json
   ```

   **Scenario 3 – Upcoming Appointment**
   ```bash
   curl -X POST http://localhost:8000/events \
     -H "Content-Type: application/json" \
     -d @data/mock_payloads/followup_needed.json
   ```

See [`docs/demo_script.md`](docs/demo_script.md) for expected output and full scenario descriptions.

---

## 10. Running Tests

```bash
# Activate the virtual environment first
source care-env/bin/activate

# Unit tests only (fast, no GCP required)
python -m pytest tests/unit/ -v --tb=short

# Integration tests
python -m pytest tests/integration/ -v --tb=short

# End-to-end tests
python -m pytest tests/e2e/ -v --tb=short

# All tests
python -m pytest tests/ -v --tb=short

# With coverage report
python -m pytest tests/unit/ --cov=apps --cov-report=term-missing
```

> Unit tests stub out all Google / OpenAI SDK calls via `tests/conftest.py`, so no real credentials are needed.

### Code Quality Checks

```bash
# Format code
black apps/ tests/

# Sort imports
isort apps/ tests/

# Lint
flake8 apps/ tests/

# Type check
mypy apps/
```

---

## 11. Production Deployment (Cloud Run)

### 11.1 Build and Push the Docker Image

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export IMAGE=us-central1-docker.pkg.dev/$PROJECT_ID/care-orchestra/care-orchestra:latest

# Authenticate Docker with GCP
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build and push
docker build -t $IMAGE .
docker push $IMAGE
```

### 11.2 Deploy to Cloud Run

```bash
gcloud run deploy care-orchestra \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,GOOGLE_API_KEY=$GOOGLE_API_KEY,GMAIL_USE_MOCK=true,USE_MOCK_DATA=false
```

### 11.3 Verify Deployment

```bash
gcloud run services describe care-orchestra --region $REGION --format="value(status.url)"
```

Open the returned URL in a browser or use `curl` to hit an endpoint.

---

## 12. CI/CD with GitHub Actions

The pipeline defined in `.github/workflows/deploy.yml` runs automatically on every push to `main`:

1. **`bq-setup` job** — Authenticates with GCP using Workload Identity Federation and runs `infra/scripts/setup_bigquery.sh` to create/update the dataset and tables.
2. **`deploy` job** — Builds the Docker image, pushes it to Artifact Registry, and deploys to Cloud Run.

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Federation provider resource name |
| `GCP_SERVICE_ACCOUNT` | Service account email used by the CI pipeline |
| `GOOGLE_API_KEY` | Gemini API key |

Set these under **Settings → Secrets and variables → Actions** in your GitHub repository.

---

## 13. Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | _(required)_ | Google Cloud project ID |
| `GCP_LOCATION` | `us-central1` | GCP region |
| `BIGQUERY_DATASET` | `care_orchestra` | BigQuery dataset name |
| `GOOGLE_API_KEY` | _(required)_ | Gemini / Google AI API key |
| `GMAIL_SENDER_EMAIL` | `alerts@careorchestra.app` | From-address for email alerts |
| `GMAIL_USE_MOCK` | `true` | `true` = log emails instead of sending |
| `CALENDAR_ID` | `primary` | Google Calendar ID |
| `CALENDAR_USE_MOCK` | `true` | `true` = skip real Calendar calls |
| `USE_MOCK_DATA` | `true` | `true` = use in-memory mock data |
| `MOCK_DATA_PATH` | `data/mock_payloads` | Path to mock event JSON files |
| `DEBUG` | `false` | Enable verbose debug logging |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `BQ_BATCH_SIZE` | `1000` | BigQuery batch insert size |
| `BQ_TIMEOUT_SECONDS` | `30` | BigQuery query timeout |
| `API_TIMEOUT` | `30` | HTTP API timeout (seconds) |
| `PATIENT_CACHE_TTL` | `3600` | Patient record cache TTL (seconds) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `PROVIDER_EMAILS` | _(empty)_ | Comma-separated provider emails for escalation |
| `DATABASE_URL` | _(optional)_ | PostgreSQL URL (future use) |

---

## 14. Project Structure Reference

```
CareOrchestra/
├── apps/
│   ├── adk_app/              # Core ADK multi-agent application
│   │   ├── agents/           # 8 specialized agents
│   │   │   ├── coordinator.py
│   │   │   ├── monitoring.py
│   │   │   ├── vitals.py
│   │   │   ├── medication.py
│   │   │   ├── analysis.py
│   │   │   ├── escalation.py
│   │   │   ├── reporting.py
│   │   │   └── Symptoms_agent.py
│   │   ├── prompts/          # LLM prompt templates per agent
│   │   ├── tools/            # Integrations: BigQuery, Gmail, Calendar
│   │   ├── services/         # Data access layer (patient, vitals, …)
│   │   ├── schemas/          # Pydantic/dataclass models
│   │   ├── config.py         # Configuration dataclasses
│   │   └── app.py            # CareOrchestraApp container
│   └── api/                  # FastAPI REST wrapper (main entry point)
├── data/
│   ├── seed/                 # CSV files loaded into BigQuery
│   └── mock_payloads/        # Sample event JSON for local testing
├── docs/                     # Architecture, workflows, agent docs
├── infra/
│   └── scripts/
│       ├── setup_bigquery.sh # One-shot BigQuery init + seed load
│       └── setup_toolbox.sh  # MCP Toolbox binary download + config
├── mcp/toolbox/              # MCP Toolbox binary + tools.yaml
├── tests/
│   ├── unit/                 # Fast, no-GCP tests
│   ├── integration/          # Multi-component tests
│   └── e2e/                  # Full workflow tests
├── .env.example              # Template for .env
├── Dockerfile                # Container definition
├── pyproject.toml            # Build config, tool settings, test markers
├── requirements.txt          # Runtime dependencies
└── startupguide.md           # This file
```

---

## 15. Troubleshooting

### `ModuleNotFoundError` when running the app

Ensure `PYTHONPATH` is set to the project root:
```bash
PYTHONPATH=. uvicorn apps.api.main:app --reload
# or
PYTHONPATH=. python -m apps.adk_app.app
```

### `google.auth.exceptions.DefaultCredentialsError`

Run application default credential setup:
```bash
gcloud auth application-default login
```
Or set `GOOGLE_APPLICATION_CREDENTIALS` to a service account key file path.

### `USE_MOCK_DATA` is ignored / real GCP calls still happen

Make sure `.env` is in the project root and was loaded before any imports. The app calls `load_dotenv()` at the top of `app.py` and `config.py`.

### BigQuery `Table not found` errors

The BigQuery dataset and tables must exist before running with `USE_MOCK_DATA=false`. Run:
```bash
./infra/scripts/setup_bigquery.sh YOUR_PROJECT_ID
```

### Tests fail with import errors for `google.*` or `openai`

The test suite stubs these SDKs in `tests/conftest.py`. Run tests from the project root with:
```bash
python -m pytest tests/unit/ -v --tb=short
```

### Port already in use

```bash
# Find and kill the process on port 8000
lsof -ti:8000 | xargs kill -9
```

---

> **Need more detail?**
> - Architecture: [`docs/architecture.md`](docs/architecture.md)
> - Agent responsibilities: [`docs/agent_responsibilities.md`](docs/agent_responsibilities.md)
> - Workflow diagrams: [`docs/workflows.md`](docs/workflows.md)
> - BigQuery schema: [`docs/bigquery_schema.md`](docs/bigquery_schema.md)
> - Demo scenarios: [`docs/demo_script.md`](docs/demo_script.md)
