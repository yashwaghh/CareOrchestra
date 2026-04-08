# CareOrchestra — Diagrams

> All diagrams are written in [Mermaid](https://mermaid.js.org/) and render
> natively on GitHub.  Open any `.md` file on GitHub to see the rendered
> charts.

---

## 1 · System Architecture

The diagram below shows every layer of the system and how they are wired together.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"primaryColor": "#2563eb", "primaryTextColor": "#fff", "primaryBorderColor": "#1d4ed8", "lineColor": "#64748b", "secondaryColor": "#f0f7ff", "tertiaryColor": "#f8fafc"}}}%%

graph TB
    %% ─── External Actors ───
    subgraph ACTORS["👤  External Actors"]
        direction LR
        PAT["Patient\n(Browser)"]
        DOC["Doctor /\nProvider"]
    end

    %% ─── Frontend ───
    subgraph FRONTEND["🖥️  Frontend  (frontend/)"]
        UI["Patient Chat UI\nindex.html"]
    end

    %% ─── API Layer ───
    subgraph API["🌐  REST API  (apps/api/)"]
        direction LR
        EP_CHAT["POST /chat\nor GET /main-adk"]
        EP_VITALS["GET /vitals/{id}\n/vitals/{id}/trend/{type}"]
        EP_MED["POST /medication/checkin\nGET /medication/{id}/adherence"]
    end

    %% ─── Orchestration / Agent Layer ───
    subgraph AGENTS["🤖  Agent Layer  (apps/adk_app/agents/)"]
        direction TB
        COORD["Coordinator Agent\nGemini 2.5 Flash\n(orchestrator + LLM chat)"]
        VITALS_A["Vitals Agent\n(vital sign analysis & trends)"]
        MED_A["Medication Agent\n(adherence tracking)"]
        MON_A["Monitoring Agent\n(event detection & routing)"]
        ANAL_A["Analysis Agent\n(composite risk scoring)"]
        ESC_A["Escalation Agent\n(high-risk alerting)"]
        REP_A["Reporting Agent\n(clinical summaries)"]
        SYM_A["Symptoms Agent\nGroq llama-3.3-70b\n(NLP symptom extraction)"]
    end

    %% ─── Service Layer ───
    subgraph SERVICES["🗂️  Service Layer  (apps/adk_app/services/)"]
        direction LR
        PAT_SVC["PatientService"]
        VIT_SVC["VitalsService"]
        MED_SVC["MedicationService"]
        ALT_SVC["AlertService"]
        SCH_SVC["SchedulerService"]
    end

    %% ─── Tools Layer ───
    subgraph TOOLS["🔧  Tools Layer  (apps/adk_app/tools/)"]
        direction LR
        BQ_T["BigQuery Tools\n(queries / mutations)"]
        GMAIL_T["Gmail Tools\n(email alerts)"]
        CAL_T["Calendar Tools\n(appointment scheduling)"]
        RISK_R["Risk Rules\n(BP / glucose thresholds)"]
        FMT["Formatter\n(report templates)"]
    end

    %% ─── Data / External ───
    subgraph GCP["☁️  Google Cloud Platform"]
        BQ[("BigQuery\npatients · vitals\nmedications · alerts")]
        GMAIL_API["Gmail API"]
        GCAL_API["Google Calendar API"]
        GEMINI_API["Gemini 2.5 Flash\n(Google AI)"]
    end

    subgraph EXTERNAL["🌍  External APIs"]
        GROQ_API["Groq API\nllama-3.3-70b-versatile"]
    end

    %% ─── Connections ───
    PAT -->|"HTTPS"| UI
    UI  -->|"REST"| EP_CHAT
    EP_CHAT --> COORD
    EP_VITALS --> VITALS_A
    EP_MED --> MED_A

    COORD -->|"tool call"| VITALS_A
    COORD -->|"tool call"| MED_A
    COORD -->|"tool call"| ANAL_A
    COORD -->|"tool call"| SYM_A
    COORD -->|"tool call"| MON_A
    COORD -->|"tool call"| ESC_A

    MON_A --> ANAL_A
    ANAL_A --> ESC_A
    ANAL_A --> REP_A

    VITALS_A --> VIT_SVC
    MED_A    --> MED_SVC
    MON_A    --> PAT_SVC
    ESC_A    --> ALT_SVC
    REP_A    --> SCH_SVC

    VIT_SVC --> BQ_T
    MED_SVC --> BQ_T
    PAT_SVC --> BQ_T
    ALT_SVC --> BQ_T
    SCH_SVC --> BQ_T

    BQ_T    -->|"SQL"| BQ
    GMAIL_T -->|"SMTP/API"| GMAIL_API
    CAL_T   -->|"REST"| GCAL_API

    ESC_A --> GMAIL_T
    ESC_A --> CAL_T
    REP_A --> FMT
    VITALS_A --> RISK_R

    COORD  -.->|"LLM inference"| GEMINI_API
    SYM_A  -.->|"LLM inference"| GROQ_API

    GMAIL_API -->|"email alert"| DOC
    GCAL_API  -->|"appointment"| DOC

    style ACTORS  fill:#f0f9ff,stroke:#0ea5e9
    style FRONTEND fill:#eff6ff,stroke:#3b82f6
    style API      fill:#eef2ff,stroke:#6366f1
    style AGENTS   fill:#faf5ff,stroke:#a855f7
    style SERVICES fill:#fdf4ff,stroke:#c084fc
    style TOOLS    fill:#fff7ed,stroke:#f97316
    style GCP      fill:#f0fdf4,stroke:#22c55e
    style EXTERNAL fill:#fef9c3,stroke:#eab308
```

### Key Architecture Decisions

| Aspect | Detail |
|--------|--------|
| **Orchestration model** | Single Coordinator Agent (Gemini 2.5 Flash) drives conversation; worker agents are called as async tools |
| **Dual LLM strategy** | Gemini for orchestration reasoning; Groq llama-3.3-70b for fast NLP symptom extraction |
| **Data persistence** | All structured data lives in BigQuery; no local stateful DB |
| **Alert delivery** | Gmail API for doctor alerts; Google Calendar API for scheduling follow-ups |
| **Deployment target** | Google Cloud Run (containerised with Docker) |
| **API surface** | FastAPI with CORS; two main endpoints (`/chat`, `/main-adk`) plus direct agent endpoints |

---

## 2 · Workflow Diagrams

### 2a · Primary Patient Chat Workflow

Covers the happy path: patient opens chat → Coordinator gathers context → collects symptoms → routes to Monitoring → escalates if needed.

```mermaid
sequenceDiagram
    autonumber
    actor P  as Patient
    participant UI  as Chat UI
    participant API as FastAPI
    participant CO  as Coordinator<br/>(Gemini 2.5 Flash)
    participant BQ  as BigQuery
    participant VA  as Vitals Agent
    participant MA  as Medication Agent
    participant AA  as Analysis Agent
    participant SA  as Symptoms Agent<br/>(Groq)
    participant MO  as Monitoring Agent
    participant EA  as Escalation Agent
    participant RA  as Reporting Agent
    actor DOC as Doctor

    P  ->> UI  : Opens chat, enters patient_id
    UI ->> API : POST /chat {message, patient_id}
    API ->> CO : coordinate(event)

    %% Step 1 – load context
    CO ->> BQ  : get_patient_profile(patient_id)
    BQ -->> CO : {name, age, conditions, last_visit}

    %% Step 2 – gather clinical data in parallel
    par Parallel tool calls
        CO ->> VA : call_vitals_agent(patient_id)
        VA ->> BQ : query recent vitals (30 days)
        BQ -->> VA : vitals rows
        VA -->> CO : {issues, trend, severity_flag}
    and
        CO ->> MA : call_medication_agent(patient_id)
        MA ->> BQ : query medication_logs (7 days)
        BQ -->> MA : adherence rows
        MA -->> CO : {adherence_rate, missed_doses, risk}
    end

    %% Step 3 – composite risk
    CO ->> AA : call_analysis_agent(patient_id)
    AA -->> CO : {risk_level, composite_score, findings, escalate}

    %% Step 4 – greet & ask symptoms
    CO -->> UI : "Hi [Name]! How are you feeling today?"
    UI -->> P  : (displays message)
    P  ->> UI : Describes symptoms
    UI ->> API: POST /chat {symptoms message}
    API ->> CO: coordinate(event)

    %% Step 5 – symptom extraction
    CO ->> SA : call_symptoms_agent(raw_message, age, conditions, vitals_flag)
    SA -->> CO : {risk_score, severity, escalation, red_flags}

    %% Step 6 – monitoring decision
    CO ->> MO : send_to_monitoring_agent(patient_id, full_summary)
    MO -->> CO : {risk_level, action, escalation_needed}

    alt escalation_needed = true
        CO ->> EA : escalate_patient(patient_id, risk_level, summary)
        EA ->> BQ : record alert
        EA -->> DOC : Gmail alert (urgent)
        EA -->> DOC : Google Calendar (follow-up appointment)
        EA -->> CO : {escalation_status: "sent"}
    end

    %% Step 7 – reporting
    CO ->> RA : generate summary/report
    RA -->> CO : formatted clinical report

    CO -->> UI : Warm response + advice
    UI -->> P  : (displays response)
```

---

### 2b · High Blood Pressure Alert Workflow

```mermaid
flowchart TD
    A([▶ Vitals Submitted\nBP 165/100]) --> B[Monitoring Agent\nDetect & enrich event]
    B --> C[Coordinator Agent\nReceive enriched event]
    C --> D[Vitals Agent\nQuery 30-day BP history\nApply Stage 2 HTN rule]
    D --> E{BP Risk Level?}
    E -->|HIGH| F[Coordinator Agent\nRequest medication check]
    F --> G[Medication Agent\nCheck antihypertensive adherence\nLast 7 days = 60%]
    G --> H[Analysis Agent\nHigh BP + Poor adherence\n= HIGH RISK]
    H --> I[Escalation Agent\nFormat clinical alert]
    I --> J[Gmail API\nSend urgent alert → Doctor]
    I --> K[Google Calendar API\nSchedule follow-up appointment]
    I --> L[(BigQuery\nRecord escalation)]
    H --> M[Reporting Agent\nCreate doctor summary:\nVitals trend, adherence, recommendations]
    E -->|NORMAL| N([✅ Routine action])

    style A fill:#fee2e2,stroke:#ef4444
    style E fill:#fef9c3,stroke:#eab308
    style J fill:#dcfce7,stroke:#22c55e
    style K fill:#dcfce7,stroke:#22c55e
    style N fill:#dcfce7,stroke:#22c55e
```

---

### 2c · Missed Medication Workflow

```mermaid
flowchart TD
    A([▶ Scheduled Check\nInsulin due @ 8 AM\nnot logged by 8:30 AM]) --> B[Monitoring Agent\nCreate medication_missed event]
    B --> C[Coordinator Agent\nReceive missed event]
    C --> D[Medication Agent\nConfirm insulin critical\nAdherence pattern = 70%]
    D --> E{Severity?}
    E -->|CRITICAL MED| F[Analysis Agent\nMissed insulin = HIGH risk\nfor hyperglycemia]
    F --> G{Risk Level?}
    G -->|MODERATE| H[Coordinator Agent\nSend urgent patient reminder]
    G -->|HIGH| I[Escalation Agent\nAlert doctor + schedule call]
    H --> J([📲 Patient reminder sent])
    I --> K([📧 Doctor alerted\n📅 Follow-up scheduled])

    style A fill:#fff7ed,stroke:#f97316
    style E fill:#fef9c3,stroke:#eab308
    style G fill:#fef9c3,stroke:#eab308
```

---

### 2d · Appointment Pre-Visit Workflow

```mermaid
flowchart TD
    A([▶ Appointment in 3 days]) --> B[Monitoring Agent\nDetect upcoming appointment]
    B --> C[Coordinator Agent\nRoute to Scheduler Service]
    C --> D[Scheduler Service\nGet appointment details\nCheck vitals since last visit]

    D --> E1[Vitals Agent\nRecent vitals analysis]
    D --> E2[Medication Agent\nCurrent adherence check]

    E1 --> F[Analysis Agent\nPre-visit synthesis]
    E2 --> F

    F --> G[Coordinator Agent\nSend appointment reminder:\n'Please prepare vitals']
    G --> H[Reporting Agent\nCreate pre-visit doctor summary:\nVitals, meds, risk level]
    H --> I([📧 Doctor inbox:\npre-visit summary])
    G --> J([📲 Patient reminder\n'Appointment in 3 days – check BP/weight'])

    style A fill:#eff6ff,stroke:#3b82f6
    style I fill:#dcfce7,stroke:#22c55e
    style J fill:#dcfce7,stroke:#22c55e
```

---

### 2e · Data Ingestion (Seed Data) Workflow

```mermaid
flowchart LR
    CSV1["data/seed/patients.csv"] --> LOADER["infra/scripts/\nload_seed_data.py"]
    CSV2["data/seed/vitals.csv"] --> LOADER
    CSV3["data/seed/medications.csv"] --> LOADER
    CSV4["data/seed/medication_logs.csv"] --> LOADER

    LOADER --> BQ_P[("BigQuery\npatients")]
    LOADER --> BQ_V[("BigQuery\nvitals")]
    LOADER --> BQ_M[("BigQuery\nmedications")]
    LOADER --> BQ_L[("BigQuery\nmedication_logs")]

    LOADER --> PAY["Mock payloads\nhigh_bp_event.json\nmissed_medication.json\nfollowup_needed.json"]

    PAY --> TEST["Demo / Testing\nenvironment ready"]

    style LOADER fill:#eff6ff,stroke:#3b82f6
    style TEST   fill:#dcfce7,stroke:#22c55e
```

---

## 3 · Use Case Diagram

```mermaid
%%{init: {"theme": "base"}}%%

flowchart LR

    %% ── Actors ──
    PAT(["👤 Patient"])
    DOC(["🩺 Doctor /\nProvider"])
    SCHED(["⏰ Scheduler\n(System)"])

    %% ── System boundary ──
    subgraph SYSTEM["CareOrchestra System"]
        direction TB

        subgraph UC_PATIENT["Patient Use Cases"]
            UC1["Send chat message"]
            UC2["Report symptoms"]
            UC3["Receive medication reminder"]
            UC4["Receive appointment reminder"]
            UC5["Get clinical advice\n(low / moderate / high / critical)"]
            UC6["View vital sign feedback"]
        end

        subgraph UC_DOCTOR["Doctor / Provider Use Cases"]
            UC7["Receive escalation alert\n(email)"]
            UC8["Receive pre-visit summary"]
            UC9["Review vital trend report"]
            UC10["Acknowledge escalation"]
            UC11["Schedule follow-up\n(calendar invite)"]
        end

        subgraph UC_SYSTEM["Automated / Scheduled Use Cases"]
            UC12["Monitor vitals (scheduled)"]
            UC13["Check medication adherence (scheduled)"]
            UC14["Detect missed medication dose"]
            UC15["Run composite risk analysis"]
            UC16["Generate clinical report"]
            UC17["Load / refresh patient data"]
        end

        subgraph UC_SHARED["Shared / Included Behaviours"]
            UC18["«include» Authenticate patient_id"]
            UC19["«include» Query BigQuery"]
            UC20["«include» Apply clinical risk rules"]
            UC21["«include» Format alert / report"]
            UC22["«extend» Escalate to emergency"]
        end
    end

    %% ── Patient associations ──
    PAT --- UC1
    PAT --- UC2
    PAT --- UC3
    PAT --- UC4
    PAT --- UC5
    PAT --- UC6

    %% ── Doctor associations ──
    DOC --- UC7
    DOC --- UC8
    DOC --- UC9
    DOC --- UC10
    DOC --- UC11

    %% ── Scheduler associations ──
    SCHED --- UC12
    SCHED --- UC13
    SCHED --- UC14
    SCHED --- UC16
    SCHED --- UC17

    %% ── Include/Extend relationships ──
    UC1  --> UC18
    UC12 --> UC19
    UC13 --> UC19
    UC15 --> UC20
    UC16 --> UC21
    UC7  --> UC21
    UC5  --> UC22

    style UC_PATIENT fill:#eff6ff,stroke:#3b82f6
    style UC_DOCTOR  fill:#f0fdf4,stroke:#22c55e
    style UC_SYSTEM  fill:#faf5ff,stroke:#a855f7
    style UC_SHARED  fill:#fff7ed,stroke:#f97316
```

### Actor Summary

| Actor | Role | Primary Interactions |
|-------|------|---------------------|
| **Patient** | Chronic-care patient with one or more conditions (hypertension, diabetes, heart disease) | Opens chat, reports symptoms, receives advice and reminders |
| **Doctor / Provider** | Primary care physician or specialist | Receives email escalation alerts, pre-visit summaries, and calendar invitations |
| **Scheduler (System)** | Automated cron / event trigger | Drives periodic vitals checks, medication adherence scans, appointment reminders, and seed data loading |

---

## 4 · Component Dependency Map

Shows which files depend on which — useful for understanding impact of changes.

```mermaid
graph LR
    APP["app.py\nCareOrchestraApp"] --> COORD
    APP --> VITALS_A
    APP --> MED_A
    APP --> MON_A
    APP --> ANAL_A
    APP --> REP_A

    subgraph Agents
        COORD["coordinator.py"]
        VITALS_A["vitals.py"]
        MED_A["medication.py"]
        MON_A["monitoring.py"]
        ANAL_A["analysis.py"]
        ESC_A["escalation.py"]
        REP_A["reporting.py"]
        SYM_A["Symptoms_agent.py"]
    end

    COORD --> VITALS_A
    COORD --> MED_A
    COORD --> MON_A
    COORD --> ANAL_A
    COORD --> ESC_A
    COORD --> SYM_A
    MON_A  --> ESC_A
    MON_A  --> ANAL_A
    ANAL_A --> REP_A

    subgraph Services
        PAT_SVC["patient_service.py"]
        VIT_SVC["vitals_service.py"]
        MED_SVC["medication_service.py"]
        ALT_SVC["alert_service.py"]
        SCH_SVC["scheduler_service.py"]
    end

    VITALS_A --> VIT_SVC
    MED_A    --> MED_SVC
    MON_A    --> PAT_SVC
    ESC_A    --> ALT_SVC
    REP_A    --> SCH_SVC

    subgraph Tools
        BQ_T["bigquery_tools/"]
        GMAIL_T["gmail_tools/"]
        CAL_T["calendar_tools/"]
        RISK_R["risk_rules/"]
        FMT["formatter/"]
        BQ_CLIENT["bigquery_client.py"]
    end

    VIT_SVC --> BQ_T
    MED_SVC --> BQ_T
    PAT_SVC --> BQ_T
    ALT_SVC --> BQ_T
    SCH_SVC --> BQ_T
    BQ_T --> BQ_CLIENT

    ESC_A --> GMAIL_T
    ESC_A --> CAL_T
    VITALS_A --> RISK_R
    REP_A --> FMT

    subgraph Schemas
        S_PAT["patient.py"]
        S_VIT["vitals.py"]
        S_MED["medication.py"]
        S_ALT["alert.py"]
        S_APT["appointment.py"]
    end

    PAT_SVC --> S_PAT
    VIT_SVC --> S_VIT
    MED_SVC --> S_MED
    ALT_SVC --> S_ALT
    SCH_SVC --> S_APT

    style Agents   fill:#faf5ff,stroke:#a855f7
    style Services fill:#fdf4ff,stroke:#c084fc
    style Tools    fill:#fff7ed,stroke:#f97316
    style Schemas  fill:#f0fdf4,stroke:#22c55e
```

---

## 5 · Risk Level Decision Matrix

```mermaid
quadrantChart
    title Risk Assessment — Vitals vs Medication Adherence
    x-axis Low Medication Adherence --> High Medication Adherence
    y-axis Normal Vitals --> Critical Vitals
    quadrant-1 MODERATE RISK
    quadrant-2 HIGH RISK
    quadrant-3 LOW RISK
    quadrant-4 MODERATE RISK
    Missed insulin + Normal vitals: [0.2, 0.3]
    Good adherence + Stage 1 HTN: [0.75, 0.5]
    Poor adherence + Stage 2 HTN: [0.15, 0.75]
    Good adherence + Normal vitals: [0.8, 0.2]
    Critical vitals + Poor adherence: [0.1, 0.92]
    HR trend declining + Good meds: [0.72, 0.6]
```

---

*Generated from live codebase. Update this file whenever new agents, services, or integrations are added.*
