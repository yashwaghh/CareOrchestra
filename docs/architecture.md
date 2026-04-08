# CareOrchestra Architecture

## Overview

CareOrchestra is a multi-agent system for chronic care coordination using Google's ADK (Agent Development Kit). The system helps monitor patient conditions, detect high-risk situations, manage medications, and escalate alerts to healthcare providers.

## System Design Philosophy

- **Modular Architecture**: Each agent is independent and can be tested/deployed separately
- **Separation of Concerns**: Agents focus on specific tasks, services handle data access, tools provide integrations
- **Clean Domain Model**: Schemas define data structure independent of persistence
- **Extensibility**: Room for new agents, services, and integrations without refactoring core

## Core Components

### 1. Agents (Multi-Agent Orchestration)
Located in `apps/adk_app/agents/`

Agents use Google ADK framework to implement autonomous reasoning and decision-making.

- **Coordinator Agent**: Main orchestrator that delegates to specialist agents and makes final decisions
- **Monitoring Agent**: Watches for patient events and triggers analysis
- **Vitals Agent**: Analyzes vital signs for abnormalities and trends
- **Medication Agent**: Tracks medication adherence and schedules
- **Analysis Agent**: Synthesizes data from multiple agents for risk assessment
- **Escalation Agent**: Handles high-risk situations and alerts doctors
- **Reporting Agent**: Creates clinical summaries for doctors and nurses

### 2. Services (Data Access Layer)
Located in `apps/adk_app/services/`

Services provide abstraction for data operations and business logic.

- **PatientService**: Patient information and history
- **VitalsService**: Vital signs data access
- **MedicationService**: Medication tracking and adherence
- **AlertService**: Alert creation and management
- **SchedulerService**: Appointments and follow-ups

### 3. Tools (Integration Layer)
Located in `apps/adk_app/tools/`

Tools provide integrations with external systems.

- **bigquery_tools/**: BigQuery client, queries, and mutations
- **gmail_tools/**: Email alert delivery
- **calendar_tools/**: Google Calendar integration
- **formatter/**: Alert and report formatting
- **risk_rules/**: Clinical decision rules for vitals and medication

### 4. Data Schemas
Located in `apps/adk_app/schemas/`

Dataclasses that define data structure.

- **patient.py**: Patient information
- **vitals.py**: Vital signs readings
- **medication.py**: Medications and adherence
- **alert.py**: Alerts and escalations
- **appointment.py**: Appointments and follow-ups

## Data Flow

```
Patient Events / Scheduled Checks
         ↓
Monitoring Agent (detects)
         ↓
Coordinator Agent (orchestrates)
         ├→ Vitals Agent (analyzes)
         ├→ Medication Agent (checks adherence)
         └→ Analysis Agent (synthesizes)
         ↓
Risk Assessment (low/moderate/high/critical)
         ↓
    ┌────┴────┐
    ↓         ↓
 Routine    High-Risk
Actions     ↓
         Escalation Agent
         ├→ Gmail (sends alert)
         └→ Calendar (schedules follow-up)
         ↓
Reporting Agent (generates updates)
```

## Technology Stack

- **Agent Framework**: Google ADK (Agent Development Kit)
- **Language**: Python 3.9+
- **Database**: BigQuery (GCP)
- **Integrations**: Gmail, Google Calendar
- **Testing Framework**: pytest
- **Code Quality**: mypy for type checking

## Deployment Target

- **Platform**: Google Cloud Run
- **Container**: Docker (dockerfile not included in starter)
- **Configuration**: Environment variables (.env)

## Module Organization

```
apps/adk_app/
├── agents/           # Agent definitions
├── prompts/          # LLM prompts for agents
├── tools/            # External integrations
├── services/         # Data access layer
├── schemas/          # Data models
├── config.py         # Configuration
└── app.py            # Main entry point
```

## Configuration

Configuration is managed through environment variables in `.env` file.

Key settings:
- `GCP_PROJECT_ID`: Google Cloud project
- `BIGQUERY_DATASET`: BigQuery dataset name
- `GMAIL_SENDER_EMAIL`: Email for sending alerts
- `USE_MOCK_DATA`: Enable mock mode for development
- `DEBUG`: Enable debug logging

## Future Enhancements

- [ ] MCP Toolbox for BigQuery
- [ ] FastAPI wrapper for REST API
- [ ] Streamlit frontend for patient/provider interface
- [ ] Advanced ML models for risk prediction
- [ ] Multi-tenant support
- [ ] Audit logging and compliance features

## Getting Started

See [Demo Script](docs/demo_script.md) for running the system with mock data.

---

## Visual Diagrams

For rendered Mermaid diagrams (system architecture, workflow, and use case diagrams), see
[docs/diagrams.md](diagrams.md).
