# CLAUDE.md — InsightPilot Backend

## Project Overview
InsightPilot is an AI-powered analytics copilot. This file tells you everything you need to know to build and extend the FastAPI backend. Read it fully before writing any code.

---

## Tech Stack
- **Framework:** FastAPI (Python)
- **ORM:** SQLAlchemy (async)
- **Database:** SQLite (pilot) — scoped per user
- **Data parsing:** pandas
- **Agent orchestration:** LangGraph
- **LLM:** Anthropic Claude Haiku via `anthropic` Python SDK
- **Auth:** Supabase Auth (JWT) — all endpoints require valid JWT
- **Deployment:** Railway or Render (uvicorn)

---

## Folder Structure
```
backend/
├── main.py                  # FastAPI app init, CORS, router registration
├── requirements.txt
├── core/
│   ├── config.py            # Env vars via pydantic-settings
│   └── database.py          # SQLAlchemy engine, session factory, Base
├── models/
│   ├── user.py
│   ├── dataset.py
│   ├── run.py
│   ├── insight.py
│   ├── kpi.py
│   └── feedback.py
├── routers/
│   ├── datasets.py          # POST /datasets/upload, GET /datasets/{id}
│   ├── runs.py              # POST /runs, GET /runs/{id}, GET /runs/{id}/insights
│   ├── insights.py          # GET /insights/{id}, POST /insights/{id}/feedback
│   └── chat.py              # POST /chat/query
├── schemas/
│   ├── dataset.py
│   ├── run.py
│   ├── insight.py
│   └── chat.py
├── services/
│   ├── ingestion.py         # CSV parsing, SQLite table creation
│   └── pipeline.py          # Orchestrates full LangGraph run
└── agents/
    ├── supervisor.py        # LangGraph StateGraph definition
    ├── schema_agent.py
    ├── sql_agent.py
    ├── insight_agent.py
    └── viz_agent.py
```

---

## Data Model

```
users:          id, email, created_at, auth_provider
datasets:       id, user_id, name, source_type, storage_ref, schema_json, created_at
runs:           id, dataset_id, user_id, status, agent_logs (JSON), insights_count, started_at, completed_at
insights:       id, run_id, user_id, type, title, narrative, sql_used, chart_config (JSON), kpi_column, severity, created_at
insight_feedback: id, insight_id, user_id, signal, note, created_at
kpis:           id, run_id, name, value, delta_pct, period_label
```

**Run status values:** `queued` | `running` | `completed` | `failed`
**Insight type values:** `trend` | `anomaly` | `segment` | `kpi`
**Insight severity values:** `low` | `medium` | `high`
**Feedback signal values:** `thumbs_up` | `thumbs_down` | `saved`

---

## Critical Rules — Read Before Writing Any Code

### SQL Safety (Non-Negotiable)
- ALL generated SQL must be SELECT-only
- Validate every SQL string before execution — reject if it contains any of: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`
- If mutation keyword detected: log the violation, skip that insight step, do NOT raise a 500

### LLM: Google Gemini via google-generativeai Python SDK
- Model: gemini-1.5-flash (all agents)
- API key env var: GEMINI_API_KEY
- Max tokens per call: 1000
- Retries: exponential backoff, max 3

### Agent Pipeline Rules
- Each agent step must be logged: `{ agent, status, duration_ms, error }` → stored in `runs.agent_logs`
- Max 2 retries per agent step before marking that step as failed
- If any single agent fails, pipeline continues with partial results — never return a blank response
- Run only degrades to `failed` status if the Supervisor itself crashes

### Anomaly Detection
- Use z-score threshold of `> 2.0` for anomaly flagging
- For z-score between `1.5` and `2.0`, use hedged language: "appears to show", "may indicate"
- Require minimum 500 rows before running anomaly detection

### Insight Playbook (Insight Discovery Agent)
Run these analyses in order per dataset:
1. MoM trend on primary metric column
2. WoW trend on primary metric column
3. Top 3 segment breakdowns by dimension columns
4. Anomaly detection (z-score) on metric columns
5. Correlation hints between numeric columns

### CSV Ingestion
- Max file size: 50MB
- Max rows for analysis: 100K (sample if larger)
- Store parsed data as SQLite table named: `upload_{user_id}_{timestamp}`
- Reject non-CSV files with a clear 400 error message
- Schema preview must return: column name, inferred type, null %, 3 sample values

---

## Environment Variables
```
DATABASE_URL=sqlite:///./insightpilot.db
GEMINI_API_KEY=
SUPABASE_JWT_SECRET=
MAX_CSV_SIZE_MB=50
MAX_ROWS_FOR_ANALYSIS=100000
```
Never log these. Never return them to the frontend.

---

## API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| POST | `/datasets/upload` | Upload CSV, returns schema preview |
| GET | `/datasets/{id}` | Get dataset metadata |
| POST | `/runs` | Trigger a new pipeline run |
| GET | `/runs/{id}` | Get run status + agent logs |
| GET | `/runs/{id}/insights` | Get all insights for a run |
| GET | `/insights/{id}` | Get single insight detail |
| POST | `/insights/{id}/feedback` | Submit thumbs up/down/saved |
| POST | `/chat/query` | NLQ → SQL → narrative + chart config |

All endpoints return JSON. All endpoints require JWT auth header: `Authorization: Bearer <token>`

---

## Performance Targets
- Full pipeline (schema → SQL → insights → viz): **under 3 minutes** for 50K row CSV
- NLQ query response: **under 15 seconds**
- CSV upload + schema preview: **under 30 seconds** for files up to 10MB

---

## Build Order
Build and fully test each phase before starting the next:

1. **Phase 1** — `core/`, `models/`, `routers/datasets.py`, `services/ingestion.py`
2. **Phase 2** — `agents/`, `services/pipeline.py`, `routers/runs.py`
3. **Phase 3** — `routers/insights.py`, `routers/chat.py`

Use `POST /runs/test-agent` as a debug endpoint to test individual agents in Phase 2 before wiring the full supervisor graph.

---

## Frontend Contract (What the Frontend Expects)

### Schema Preview Response
```json
{
  "dataset_id": "string",
  "columns": [
    { "name": "string", "type": "string", "null_pct": 0.0, "samples": ["a", "b", "c"] }
  ],
  "row_count": 0,
  "quality_warnings": ["string"]
}
```

### Insight Object
```json
{
  "id": "string",
  "type": "trend | anomaly | segment | kpi",
  "title": "string",
  "narrative": "string ending with ⚠️ AI-generated. Verify before acting.",
  "chart_config": { "type": "line | bar | scatter", "x": "string", "y": "string", "data": [] },
  "sql_used": "string",
  "severity": "low | medium | high",
  "created_at": "ISO timestamp"
}
```

### Run Status Response
```json
{
  "id": "string",
  "status": "queued | running | completed | failed",
  "agent_logs": [
    { "agent": "string", "status": "string", "duration_ms": 0, "error": null }
  ],
  "insights_count": 0,
  "started_at": "ISO timestamp",
  "completed_at": "ISO timestamp | null"
}
```

### Chat Query Response
```json
{
  "answer": "string",
  "sql_used": "string",
  "chart_config": { "type": "string", "x": "string", "y": "string", "data": [] }
}
```
