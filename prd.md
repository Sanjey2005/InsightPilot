# Product Requirements Document: Insight (InsightPilot)
**Version:** 1.0  
**Status:** Pilot Draft  
**Author:** Principal PM  
**Last Updated:** March 2026  

---

## 1. Introduction

### What Insight Is
Insight (codename: InsightPilot) is an AI-driven analytics copilot that transforms raw business data — uploaded as CSVs or connected via a database — into narrative insights, KPI summaries, and anomaly alerts. It uses a LangGraph-style multi-agent system (Schema Discovery → SQL Generation → Insight Discovery → Visualization → Supervisor) to autonomously explore data and surface "story cards": short, readable summaries of the most important trends, drops, and patterns in a dataset. Users get a structured insight feed, a KPI header, and a chat interface to ask follow-up questions in plain English.

### Who It Is For
- **Early-stage SaaS founders** who have data in spreadsheets or product databases but no analyst or BI team.
- **PMs and ops leads** who track business metrics but spend too much time pulling numbers manually.
- **Sales and growth leads** who want to understand customer behavior, segment performance, or revenue trends without needing SQL.

### Why This Pilot Exists Now
Three trends converge to make this the right moment:
1. **LLMs are now reliable enough** to generate accurate SQL and business-readable narratives at low cost via API.
2. **Multi-agent orchestration frameworks** (LangGraph, CrewAI) enable composable, inspectable AI pipelines that are production-viable for a solo dev.
3. **Self-serve analytics demand is high** but existing tools (Tableau, Metabase, Looker) are too slow to set up, too passive (no proactive insights), or require SQL expertise. Insight fills this gap for the non-technical operator.

---

## 2. Problem Statement

- **Fragmented data, no synthesis:** Business data sits across CSVs, Notion exports, and Postgres databases with no single layer that tells you what matters most today.
- **Manual, reactive reporting:** Users pull numbers only when asked. They build static dashboards that go stale and miss emerging anomalies entirely.
- **SQL is a bottleneck:** Even if data is in a database, most operators and founders cannot write the window functions or multi-table joins needed for segment-level analysis.
- **Context-switching kills focus:** Analysts switch between SQL editors, Excel, Slack threads, and BI tools to answer a single business question, wasting 2–4 hours per report.
- **Surface-level metrics only:** Teams typically monitor topline KPIs (total revenue, DAU) and miss "why" signals — e.g., a specific customer segment's retention collapsed two weeks ago.

**Current workaround:** Export CSV → paste into Excel/Sheets → write pivot tables → create a chart → share in Slack. Drawbacks: slow (hours), non-repeatable, error-prone, requires manual interpretation, and produces no narrative or "so what."

---

## 3. Goals and Success Metrics

| # | Goal | Metric | Pilot Target |
|---|------|--------|-------------|
| G1 | Reduce time-to-first-insight | Time from data upload to first rendered insight card | < 3 minutes |
| G2 | Deliver perceived value | % of pilot users who mark ≥ 1 insight as "useful" | ≥ 70% |
| G3 | Drive repeat usage | Weekly active users returning ≥ 2 sessions in 8 weeks | ≥ 60% of enrolled users |
| G4 | Insight depth beyond topline | % of insights that are segment-level or anomaly-type (not just totals) | ≥ 50% of all generated insights |
| G5 | NLQ engagement | % of sessions where user sends ≥ 1 chat query | ≥ 40% |

> **Assumption:** Pilot will onboard 10–20 real users over 8 weeks using the Olist / Target Brazilian e-commerce dataset as the default demo dataset. Real user data uploads are opt-in.

---

## 4. Key Use Cases & User Stories

### Persona 1: The Founder
Early-stage founder of a B2C/B2B SaaS or e-commerce business. Has a Postgres database or exports monthly CSVs from Stripe/Shopify. Wants to know what's going wrong before a board meeting.

| Story | Scope |
|-------|-------|
| As a founder, I want to upload my revenue CSV and immediately see MoM trends and anomalies, so I can prepare for investor updates without waiting for my analyst. | ✅ Pilot |
| As a founder, I want to ask "Which customer segment churned the most last month?" in plain English and get a direct answer with a chart. | ✅ Pilot |
| As a founder, I want to receive a weekly email digest of top insights from my data. | ❌ v2 |
| As a founder, I want to connect my Stripe account directly instead of exporting CSVs. | ❌ v2 |

### Persona 2: The PM / Ops Lead
Manages product metrics, support ops, or growth analytics. Knows what KPIs matter but cannot write SQL to break them down by segment.

| Story | Scope |
|-------|-------|
| As a PM, I want Insight to automatically detect my date and metric columns and suggest relevant KPIs, so I don't have to configure anything manually. | ✅ Pilot |
| As a PM, I want to view a structured feed of insight cards that covers trends, drops, and outliers for my uploaded dataset. | ✅ Pilot |
| As a PM, I want to mark an insight as "useful" or "not useful" so the system can improve over time. | ✅ Pilot |
| As a PM, I want to share a specific insight card as a shareable link with my team. | ❌ v2 |

### Persona 3: The Data-Curious IC
An engineer, designer, or growth marketer who is "data curious" but not a data analyst. Wants to explore a dataset they were given without needing to set up Metabase or write Python.

| Story | Scope |
|-------|-------|
| As a data-curious IC, I want to upload a CSV and immediately see which columns look interesting and why. | ✅ Pilot |
| As a data-curious IC, I want to type a question like "What are the top-selling product categories?" and see the answer as a chart. | ✅ Pilot |
| As a data-curious IC, I want to see the raw SQL that generated an insight, so I can trust and verify it. | ✅ Pilot |
| As a data-curious IC, I want to export a chart as a PNG to paste into a deck. | ❌ v2 |

---

## 5. Functional Requirements

### 5.1 Data Ingestion & Connections

| Short Name | Description | Priority | Dependencies / Notes |
|------------|-------------|----------|----------------------|
| CSV Upload | User uploads a CSV file (max 50MB). Stored in backend, parsed into a managed SQLite/Postgres table scoped to the user's session. | P0 | Requires file upload endpoint in FastAPI |
| Schema Preview | After upload, display detected columns, inferred data types, sample rows, and basic quality stats (nulls %, unique values). | P0 | Output of Schema Discovery Agent |
| DB Connection | User optionally enters a Postgres connection string. Backend validates the connection and enumerates accessible tables. | P1 | Assumed read-only access; no writes to user DB |
| Multi-table Detection | If DB connection is used, detect foreign key relationships between tables and propose a join graph. | P1 | Used by SQL Generation Agent |

### 5.2 Multi-Agent Insight Generation

| Short Name | Description | Priority | Dependencies / Notes |
|------------|-------------|----------|----------------------|
| Schema Discovery Agent | Inspects dataset: infers column types, detects date/metric/dimension columns, flags nulls/duplicates/outliers, proposes candidate KPIs. | P0 | LangGraph node 1; runs first |
| SQL Generation Agent | Converts hypotheses or NLQ questions into optimized SQL; handles aggregations, window functions, and JOINs. Must validate SQL before execution. | P0 | Depends on Schema Discovery output + LLM |
| Insight Discovery Agent | Runs a fixed playbook: MoM/WoW trends, segment breakdowns (top 3 dimensions), anomaly detection (z-score > 2), correlation hints. Calls SQL Agent per hypothesis. | P0 | Core intelligence; depends on SQL Agent |
| Visualization Agent | For each insight object, selects chart type (line/bar/scatter) and generates chart config (axes, labels, series, colors). | P0 | Depends on Insight Discovery output |
| Supervisor Orchestrator | Routes tasks, manages agent state via LangGraph, handles retries (max 2), compiles final insight list, tracks run metadata. | P0 | LangGraph supervisor node; coordinates all agents |
| Run Execution | A "Run" represents one full pipeline pass. Stored with status (queued/running/completed/failed), timestamps, and agent step logs. | P0 | Enables History screen |

### 5.3 Insight Surfacing

| Short Name | Description | Priority | Dependencies / Notes |
|------------|-------------|----------|----------------------|
| Insight Feed | Scrollable list of story cards. Each card shows: title, narrative (1–2 sentences), mini chart, insight type badge (trend/anomaly/segment), thumbs up/down. | P0 | Depends on completed Run |
| KPI Header Bar | Pinned top bar showing 3–5 auto-detected KPIs with current value and delta vs prior period. Animate number count-up. | P0 | Derived from Schema Discovery + SQL Agent |
| Insight Detail View | Expanded view on card click: full narrative, full chart, raw SQL used, data table (first 10 rows), and metadata (generated at, model used). | P1 | Must show SQL for trust/transparency |
| Filter & Sort | Basic client-side filters on the insight feed: by type (trend, anomaly, segment), by KPI column, by time range. | P1 | Frontend only; no re-run needed |

### 5.4 Natural Language Querying (NLQ / Copilot Chat)

| Short Name | Description | Priority | Dependencies / Notes |
|------------|-------------|----------|----------------------|
| Chat Interface | Persistent sidebar or drawer. User types a question; system calls SQL Agent, runs query, and returns a narrative answer + mini chart. | P0 | Relies on SQL Generation Agent |
| Query History | Show last 10 chat exchanges in the current session. Not persisted across sessions in pilot. | P1 | Simple in-memory state |
| Suggested Questions | After schema discovery, show 3 pre-generated suggested questions the user can click (e.g., "Which category has the highest revenue?"). | P1 | Generated by LLM post-schema-discovery |

### 5.5 Feedback Loop

| Short Name | Description | Priority | Dependencies / Notes |
|------------|-------------|----------|----------------------|
| Thumbs Up/Down | One-click feedback on each insight card. Stored to `insight_feedback` table. | P0 | Core pilot success signal |
| Mark as Useful | Explicit "Save" action on insight cards that moves them to a "Saved" view. | P1 | — |
| Regenerate Insight | Button on Insight Detail view to re-run just that insight with a fresh LLM call. | P1 | Useful for iterating on quality |
| Text Note | Optional free-text note on a saved insight ("Share this with the team on Friday"). | P2 | Nice to have |

---

## 6. Non-Functional Requirements

### Performance
- **Time-to-first-insight:** Full pipeline (schema → SQL → insights → visualization metadata) must complete in under 3 minutes for datasets up to 100K rows.
- **NLQ query latency:** From user submitting a question to answer rendered: under 15 seconds (LLM + SQL execution).
- **UI responsiveness:** All pages must load under 2 seconds; insight cards animate in progressively (no full-page blocking spinner).

### Reliability & Data Freshness
- For the pilot, data is uploaded once per session; no live refresh. "Fresh enough" = same session's data.
- Agent pipeline must have retry logic (max 2 retries per agent step) with graceful fallback: if Insight Discovery Agent fails, still surface KPIs and allow NLQ.
- LLM API rate limits (Gemini/Claude free tier) must be handled with exponential backoff and a user-visible "system is thinking" state.

### Security & Privacy
- No PII in this pilot (assumption: users upload anonymized business/e-commerce datasets, not customer records).
- All uploaded files stored in server-local temp storage, deleted after session ends or after 24 hours.
- API keys (LLM, DB connection strings) stored as environment variables only; never logged or returned to frontend.
- Auth via Supabase Auth (JWT). All API endpoints require a valid JWT. User data is row-level scoped by `user_id`.
- HTTPS enforced on deployment (Render/Railway with auto TLS).

### Observability
- Log every agent step: agent name, status, duration, token count, error (if any) → structured JSON logs.
- Track per-run metrics: total duration, number of insights generated, number of SQL queries executed, LLM model used.
- Track user events: file upload, run triggered, insight viewed, thumbs up/down, NLQ query submitted.
- Use a lightweight logging solution: Python `logging` → stdout → Railway/Render log tailing. No need for Datadog/Sentry in pilot; a simple `/admin/logs` internal route is sufficient.

---

## 7. Data & Integrations

### Data Sources (Pilot)
1. **CSV Upload** (P0): User uploads `.csv` file. Backend parses using `pandas`, stores in a scoped SQLite table named `upload_{user_id}_{timestamp}`.
2. **Postgres DB Connection** (P1): User provides read-only connection string. Backend uses `sqlalchemy` to enumerate tables and run queries directly (no data copying).

### Rough Data Model

```text
users
  id, email, created_at, auth_provider

datasets
  id, user_id, name, source_type (csv|postgres), 
  storage_ref (file path or connection metadata), 
  schema_json, created_at

runs
  id, dataset_id, user_id, status (queued|running|completed|failed),
  agent_logs (JSONB), insights_count, started_at, completed_at

insights
  id, run_id, user_id, type (trend|anomaly|segment|kpi),
  title, narrative, sql_used, chart_config (JSONB),
  kpi_column, severity (low|medium|high), created_at

insight_feedback
  id, insight_id, user_id, signal (thumbs_up|thumbs_down|saved),
  note (text, nullable), created_at

kpis
  id, run_id, name, value, delta_pct, period_label
```

### Constraints & Assumptions
- Tabular data only: no images, PDFs, free text blobs, or nested JSON.
- English only for insight narratives (LLM prompt in English).
- No PII: assume datasets do not contain names, emails, SSNs, or phone numbers.
- No streaming: data is point-in-time at upload/connection; no CDC or live sync.
- Max CSV size: 50MB / ~500K rows. Above this, sample to 100K rows for analysis.
- Single dataset per run: no cross-dataset joins in pilot.

---

## 8. AI / LLM Requirements

### What the Model Needs to Do

| Task | Agent | Model Suggestion |
|------|-------|-----------------|
| Interpret schema, suggest KPIs and dimensions | Schema Discovery | Gemini 1.5 Flash (fast, cheap) |
| Generate SQL from hypothesis or NLQ | SQL Generation | Gemini 1.5 Pro or Claude 3 Haiku |
| Summarize numeric query results into narrative | Insight Discovery | Claude 3 Haiku or Gemini 1.5 Flash |
| Detect anomalies from tabular outputs | Insight Discovery | Heuristic (z-score) first; LLM for narrative only |
| Suggest chart type and config | Visualization | Gemini 1.5 Flash |

### Guardrails
- **SQL Safety:** All generated SQL is validated against a whitelist (SELECT only; no INSERT/UPDATE/DELETE/DROP). Reject and retry if any mutation keyword detected.
- **Hallucination limit:** LLM narrative output must reference only column names and values confirmed in the query result. Include a post-processing check: if any number in the narrative does not appear in the result, flag and regenerate.
- **Uncertainty phrasing:** If confidence in an anomaly is low (z-score between 1.5 and 2), use hedged language: "appears to show," "may indicate."
- **Mandatory disclaimer:** Every insight card and chat answer includes a footer: `⚠️ AI-generated. Verify before acting.`
- **Token budget:** Cap each LLM call at 1,500 output tokens. For narrative, aim for 2–3 sentences max per insight.

### Feedback Signals to Capture
- Thumbs up / thumbs down per insight card → `insight_feedback` table.
- "Regenerate" clicks → logged as `regenerate_requested` event with insight_id.
- User edits to narrative (if editable in v2) → stored as `user_edited_narrative`.
- Saved/archived insights → strong positive signal for insight quality scoring in v2.

---

## 9. UX & UI Requirements

### Expected First-Run Flow
```
Login → "Upload your dataset" screen → 
Upload CSV → Schema preview loads → 
"Analyze Dataset" button → Agent Stepper (5 steps animating) →
Insights Overview screen (KPI bar + insight feed) →
User clicks a card → Insight Detail view →
User types question in Copilot Chat sidebar →
Answer + chart returned inline
```

---

### Screen 1: Dataset Onboarding

**Purpose:** Get user's data into the system and build trust before analysis starts.

| Component | Must-Have | Nice-to-Have |
|-----------|-----------|-------------|
| Drag-and-drop CSV dropzone | ✅ | — |
| Postgres connection form | ✅ | Connection test button |
| Schema preview table (col name, type, null %, sample) | ✅ | — |
| Detected KPI suggestions (e.g., "revenue", "orders") | ✅ | User can toggle KPIs on/off |
| "Analyze Dataset" CTA button | ✅ | — |
| Data quality warnings (e.g., "32% nulls in `price`") | ✅ | — |

---

### Screen 2: Insights Overview

**Purpose:** The main dashboard. Central destination after a run completes.

| Component | Must-Have | Nice-to-Have |
|-----------|-----------|-------------|
| KPI header bar (3–5 metrics, animated delta) | ✅ | Period picker |
| Insight card feed (title, 1-line narrative, mini chart, type badge) | ✅ | Masonry layout |
| Insight type filter tabs (All, Trends, Anomalies, Segments) | ✅ | — |
| Thumbs up / thumbs down per card | ✅ | — |
| Copilot Chat sidebar / drawer toggle | ✅ | — |
| Agent Stepper (shown while run is in progress) | ✅ | — |

---

### Screen 3: Insight Detail

**Purpose:** Full deep-dive on a single insight. Builds trust through transparency.

| Component | Must-Have | Nice-to-Have |
|-----------|-----------|-------------|
| Full narrative (2–4 sentences) | ✅ | — |
| Full Recharts/Plotly chart | ✅ | Chart type switcher |
| Raw SQL used to generate insight | ✅ | "Copy SQL" button |
| Data table (first 10 rows of query result) | ✅ | — |
| Metadata (generated at, model, run ID) | ✅ | — |
| "Regenerate" button | ✅ | — |
| Save / Archive action | ✅ | — |

---

### Screen 4: Copilot Chat ("Ask Insight")

**Purpose:** Continuous natural language interface over the same dataset.

| Component | Must-Have | Nice-to-Have |
|-----------|-----------|-------------|
| Message history (current session) | ✅ | Persisted across sessions (v2) |
| Text input + submit button | ✅ | Voice input (v2) |
| Answer: narrative + mini chart | ✅ | Follow-up suggestions |
| SQL accordion (click to reveal SQL behind the answer) | ✅ | — |
| Suggested starter questions (3, generated post-schema) | ✅ | — |

---

### Screen 5: Runs / History

**Purpose:** Minimal log of past analysis runs. Useful for debugging and re-running.

| Component | Must-Have | Nice-to-Have |
|-----------|-----------|-------------|
| List of runs (dataset name, status, timestamp, insight count) | ✅ | — |
| "View Insights" link per run | ✅ | — |
| "Re-run" button | ✅ | — |
| Agent step log expandable per run | P1 | — |

---

## 10. Pilot Scope & Out-of-Scope

### ✅ Included in Pilot
- Single-user, single-tenant (each user sees only their own data and runs)
- CSV upload (up to 50MB)
- One Postgres DB connection per user
- 5-agent LangGraph pipeline (schema → SQL → insights → visualization → supervisor)
- Auto-generated insight feed (trends, anomalies, segment breakdowns)
- KPI header bar
- Insight detail with raw SQL visibility
- Copilot Chat (NLQ → SQL → answer)
- Thumbs up/down feedback
- Run history view
- Basic auth (Supabase Auth, email/password + Google OAuth)
- Deployment on Vercel (frontend) + Railway or Render (backend)
- Demo dataset: Olist Brazilian E-Commerce (Kaggle)

### ❌ Excluded from Pilot
- Multi-tenant org workspaces (team accounts, shared dashboards)
- Row-level security or column-level access control
- Real-time or streaming data connections
- Scheduled runs or alerting (Slack, email digests)
- Stripe, Salesforce, HubSpot, or other SaaS data connectors
- Fine-tuned or self-hosted LLMs
- Export to PDF, PNG, or Notion/Google Slides
- Mobile-responsive design (desktop-first only)
- Advanced anomaly ML (ARIMA, Prophet) — z-score heuristics only in pilot

### 🔭 v2 Directions
1. **Scheduled Alerts:** Nightly or weekly runs with email/Slack delivery of top insights.
2. **Org Workspaces:** Multi-user teams sharing datasets, runs, and saved insights with role-based access.

---

## 11. Risks & Open Questions

### Product Risks
- **Trust gap:** Users may not act on AI-generated insights without understanding the underlying data. Mitigation: always show raw SQL and source data.
- **Insight fatigue:** Generating 10–15 cards per run may overwhelm users. Mitigation: rank by severity; show top 5 by default.

### Technical Risks
- **SQL correctness:** LLM may generate syntactically valid but semantically wrong SQL (wrong joins, wrong aggregation scope). Mitigation: schema-constrained prompting + result sanity checks.
- **Free tier LLM rate limits:** Gemini/Claude free tiers have low RPM limits. A single run triggers multiple LLM calls. Mitigation: batch calls where possible; cache schema discovery output per dataset.
- **Large dataset performance:** 100K+ row datasets may cause SQLite to slow down. Mitigation: always `LIMIT` queries; use indexed columns for aggregations.

### Data / ML Risks
- **Spurious anomalies:** Z-score detection on small datasets (< 1K rows) will flag many false positives. Mitigation: require minimum row count (500) before anomaly detection.
- **Narrative hallucination:** LLM may invent numbers not present in query results. Mitigation: post-generation validation pass checking all numeric claims against the actual result JSON.

### Open Questions to Validate During Pilot
1. What is the minimum dataset size where users feel the insights are "real"?
2. Do users trust insights more when they see the raw SQL, or does SQL confuse non-technical users?
3. What insight types (trend, anomaly, segment) do users click on and save most?
4. Is 3 minutes an acceptable wait time for the full pipeline, or do users abandon before completion?
5. Do users prefer a few high-confidence insights (top 3) or a comprehensive feed (10–15)?
6. Is the NLQ interface used proactively, or only after reading auto-generated insights?
7. What is the biggest reason users don't mark an insight as "useful"? (Wrong metric? Too obvious? Not actionable?)
8. Do users want to edit/correct insight narratives, or is read-only sufficient?
9. Should suggested questions be personalized per dataset schema, or can generic templates work?
10. Is CSV upload sufficient for the pilot, or is a DB connection prerequisite for most target users?

---

## 12. Implementation Order (for AI Coding Tools)

### Phase 1: Foundation & Data Ingestion
```
backend/
├── main.py                  # FastAPI app init, CORS, router registration
├── core/
│   ├── config.py            # Env vars, settings (DB URL, LLM API keys)
│   └── database.py          # SQLAlchemy engine, session factory, Base model
├── models/
│   ├── user.py              # User ORM model
│   ├── dataset.py           # Dataset ORM model
│   └── run.py               # Run ORM model
├── routers/
│   └── datasets.py          # POST /datasets/upload, GET /datasets/{id}
├── services/
│   └── ingestion.py         # CSV parsing (pandas), schema profiling, SQLite table creation
└── schemas/
    └── dataset.py           # Pydantic request/response models for datasets
```

### Phase 2: Multi-Agent Pipeline
```
backend/
├── agents/
│   ├── supervisor.py        # LangGraph StateGraph definition, agent routing
│   ├── schema_agent.py      # Schema Discovery: column inference, KPI suggestions
│   ├── sql_agent.py         # SQL Generation: hypothesis → validated SQL
│   ├── insight_agent.py     # Insight Discovery: run playbook, interpret results
│   └── viz_agent.py         # Visualization: chart type selector, config generator
├── services/
│   └── pipeline.py          # Orchestrates a full Run: invokes supervisor graph, stores results
├── routers/
│   └── runs.py              # POST /runs (trigger), GET /runs/{id}, GET /runs/{id}/insights
└── models/
    ├── insight.py           # Insight ORM model
    └── kpi.py               # KPI ORM model
```

### Phase 3: Insights API & Frontend
```
backend/
├── routers/
│   └── insights.py          # GET /insights/{id}, POST /insights/{id}/feedback
frontend/
├── app/
│   ├── layout.tsx           # Root layout, auth wrapper, Canvas3D background
│   ├── page.tsx             # Dataset Onboarding screen
│   ├── dashboard/page.tsx   # Insights Overview screen
│   ├── insight/[id]/page.tsx # Insight Detail screen
│   └── history/page.tsx     # Runs History screen
├── components/
│   ├── dashboard/
│   │   ├── KPIBar.tsx
│   │   ├── InsightFeed.tsx
│   │   └── StoryCard.tsx
│   ├── upload/
│   │   └── DropZone.tsx
│   └── ui/
│       ├── AgentStepper.tsx
│       └── GlassCard.tsx
└── lib/
    ├── api.ts               # Axios/fetch API client with auth headers
    └── mockData.ts          # Static mock run/insights for frontend dev without backend
```

### Phase 4: NLQ, Feedback & Polish
```
backend/
├── routers/
│   └── chat.py              # POST /chat/query (NLQ → SQL → answer)
frontend/
├── components/
│   └── chat/
│       └── CopilotChat.tsx  # Sidebar chat interface
```

> **Critical Rule for AI Coding Tools:** Build and test Phase 1 fully before starting Phase 2. Phase 2 agents should be individually testable via a `POST /runs/test-agent` endpoint before the full supervisor graph is wired. Phase 3 frontend should use `mockData.ts` initially and only wire to the real API after Phase 2 is complete.

---

## 13. Acceptance Criteria & Verify Checklist

### Data Ingestion
- ✅ A valid CSV uploads successfully and is parsed into a queryable SQLite table within 30 seconds for files up to 10MB.
- ✅ Schema preview shows column names, inferred types, null %, and at least 3 sample values per column.
- ✅ Invalid file types (PDF, XLSX, images) are rejected with a clear error message.
- ✅ A Postgres connection string is validated; invalid credentials return an error within 5 seconds.

### Multi-Agent Pipeline
- ✅ A full run completes (status = `completed`) within 3 minutes for a 50K-row CSV.
- ✅ At least 5 insights are generated per run; at least 2 must be segment-level or anomaly-type.
- ✅ All generated SQL is SELECT-only; any mutation keyword causes the run to reject that step.
- ✅ If one agent fails, the run degrades gracefully (surfaces partial results, not a blank screen).
- ✅ All agent steps are logged with timestamps and stored in `runs.agent_logs`.

### Insight Surfacing
- ✅ Insights Overview renders all insight cards with title, narrative, mini chart, and type badge.
- ✅ KPI header bar shows at least 3 KPIs with current value and delta.
- ✅ Clicking a card opens Insight Detail with full narrative, chart, and SQL.
- ✅ Every insight card and detail view displays the `⚠️ AI-generated. Verify before acting.` disclaimer.

### NLQ / Copilot Chat
- ✅ A typed question returns a narrative answer and chart within 15 seconds.
- ✅ The SQL used for the answer is expandable/visible.
- ✅ At least 3 suggested starter questions are shown after schema discovery completes.

### Feedback Loop
- ✅ Thumbs up/down registers and persists to the database.
- ✅ "Save" action moves an insight to a Saved view.
- ✅ "Regenerate" triggers a fresh LLM call and replaces the existing narrative.

---

### 🚀 10-Point Demo Readiness Checklist

| # | Check | Pass Condition |
|---|-------|----------------|
| 1 | CSV upload and schema preview | Olist CSV uploads and schema renders in < 30s |
| 2 | Full pipeline completes | Run finishes with status `completed` in < 3 min |
| 3 | Insight feed renders | ≥ 5 cards visible with charts and narratives |
| 4 | At least 1 anomaly/segment insight | Not all cards are topline trends |
| 5 | KPI bar populated | ≥ 3 KPIs with delta shown |
| 6 | NLQ works end-to-end | "Which product category has highest revenue?" returns correct answer |
| 7 | Insight Detail shows SQL | SQL is visible and SELECT-only |
| 8 | Feedback works | Thumbs up registers and persists |
| 9 | Auth works | Login → protected route → logout cycle completes |
| 10 | No blank screens | All failure states show a user-readable error message, not a 500 |
```