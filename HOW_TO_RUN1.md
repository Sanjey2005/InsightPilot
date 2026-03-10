# InsightPilot — End-to-End Setup Guide

Two processes must run simultaneously: the **FastAPI backend** (port 8000) and the **Next.js frontend** (port 3000). Open two terminal windows.

---

## Prerequisites

| Tool | Minimum version | Check |
|------|----------------|-------|
| Node.js | 18+ | `node -v` |
| Python | 3.10+ | `python --version` |
| pip | any | `pip --version` |

---

## 1 — Backend (FastAPI)

### 1.1 Create a virtual environment

```bash
cd C:\Users\acer\Desktop\InsightPilot\backend
python -m venv venv
```

Activate it:

```bash
# Windows (PowerShell / CMD)
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

You should see `(venv)` in your prompt.

### 1.2 Install dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, pandas, numpy, LangGraph, and the Google Gemini SDK.

### 1.3 Create the `.env` file

Inside `backend/`, create a file called `.env`:

```env
# Required for the AI pipeline (get a free key at https://aistudio.google.com)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — defaults shown below
DATABASE_URL=sqlite:///./insightpilot.db
DEV_MODE=true
MAX_CSV_SIZE_MB=50
```

> **`DEV_MODE=true`** skips JWT authentication and uses a fixed internal dev user.
> You do NOT need a Supabase account to run locally.

### 1.4 Start the backend

```bash
uvicorn main:app --reload --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

The SQLite database file (`insightpilot.db`) is created automatically in the `backend/` folder on first run.

**Interactive API docs:** http://localhost:8000/docs

---

## 2 — Frontend (Next.js)

### 2.1 Install dependencies

In a **new terminal**, from the project root:

```bash
cd C:\Users\acer\Desktop\InsightPilot
npm install
```

### 2.2 Environment variable (optional)

The frontend already defaults to `http://localhost:8000`. If your backend runs on a different port, create `.env.local` in the project root:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2.3 Start the frontend

```bash
npm run dev
```

You should see:

```
▲ Next.js 16.x.x
- Local: http://localhost:3000
```

Open **http://localhost:3000** in your browser.

---

## 3 — Full end-to-end test (real pipeline)

With both servers running:

1. **Upload a CSV** — drag and drop any `.csv` file onto the drop zone, or click to browse. The file is sent to `POST /datasets/upload`. On success the drop zone shows column count and row count.

2. **Click "Analyze Dataset"** — triggers `POST /runs/` which starts the multi-agent pipeline in the background:
   - Schema Discovery Agent — classifies columns, detects KPIs
   - SQL Generation Agent — generates analytical queries
   - Insight Discovery Agent — finds trends, anomalies, segments
   - Visualization Agent — assigns chart types
   - Supervisor — compiles everything

   The Agent Stepper shows real progress polled every 3 seconds from `GET /runs/{id}`.

3. **Dashboard appears** — KPI tiles animate in, then three story cards with charts. The CopilotChat panel opens on the right.

4. **Ask a question** — type a natural language question in the chat (e.g. "Which category has the highest sales?"). The backend generates SQL, runs it against your uploaded table, and returns a narrative answer with a chart.

---

## 4 — Simulate mode (no API key required)

If you don't have a Gemini API key or just want to test the UI:

1. Start **only** the frontend (`npm run dev`). The backend can be off.
2. Open http://localhost:3000.
3. Click **"Simulate Analysis"** without uploading any file.
4. The app runs a local simulation with mock data — the Agent Stepper animates through all 4 agents, then the dashboard loads with 3 pre-built insight cards and charts.

The CopilotChat also works in simulate mode and returns a canned response.

---

## 5 — Getting a Gemini API key

1. Go to **https://aistudio.google.com**
2. Sign in with a Google account
3. Click **"Get API key"** → **"Create API key"**
4. Copy the key into `backend/.env` as `GEMINI_API_KEY=...`
5. Restart the backend (`CTRL+C` then `uvicorn main:app --reload --port 8000`)

The free tier allows enough calls to fully test the pipeline.

---

## 6 — Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` on backend start | Run `pip install -r requirements.txt` inside the activated venv |
| `EADDRINUSE` on frontend start | Another process is on port 3000 — run `npx kill-port 3000` then retry |
| Agent Stepper stalls at one agent | Check backend terminal for a stack trace; usually a missing `GEMINI_API_KEY` |
| Charts not appearing | Hard-reload the browser (`Ctrl+Shift+R`); if persistent, check browser console for Recharts errors |
| `Network Error` in browser console | Backend is not running — start it with `uvicorn main:app --reload --port 8000` |
| CSV upload returns 400 | File exceeds 50 MB limit or is not valid UTF-8; try a smaller file |
| `sqlite3.OperationalError` | Delete `backend/insightpilot.db` and restart the backend to recreate the schema |

---

## 7 — Project structure (quick reference)

```
InsightPilot/
├── backend/                  FastAPI backend
│   ├── main.py               App entry point, router registration
│   ├── core/
│   │   ├── config.py         Pydantic settings (.env binding)
│   │   ├── database.py       SQLAlchemy engine + session
│   │   └── auth.py           JWT auth (dev_mode bypass)
│   ├── agents/
│   │   ├── supervisor.py     LangGraph StateGraph orchestrator
│   │   ├── schema_agent.py   Column classification
│   │   ├── sql_agent.py      SQL generation + safety validation
│   │   ├── insight_agent.py  Trend/anomaly/segment detection
│   │   ├── viz_agent.py      Chart config generation
│   │   └── utils.py          call_gemini(), Timer, make_log()
│   ├── routers/
│   │   ├── datasets.py       POST /datasets/upload
│   │   ├── runs.py           POST /runs/, GET /runs/{id}
│   │   ├── insights.py       GET/POST /insights/{id}
│   │   └── chat.py           POST /chat/query, GET /chat/suggestions
│   ├── services/
│   │   ├── ingestion.py      CSV → SQLite table
│   │   └── pipeline.py       Background task runner
│   ├── models/               SQLAlchemy ORM models
│   ├── requirements.txt
│   └── .env                  ← create this (see step 1.3)
│
├── src/                      Next.js frontend
│   ├── app/
│   │   ├── page.tsx          Main page (hero / stepper / dashboard)
│   │   └── layout.tsx        Root layout + 3D canvas
│   ├── components/
│   │   ├── 3d/               Three.js particle background
│   │   ├── dashboard/        KPIBar, StoryCard
│   │   ├── chat/             CopilotChat
│   │   └── ui/               AgentStepper
│   └── lib/
│       ├── api.ts            Typed API client + fallback mock data
│       ├── store.ts          Zustand global state
│       └── mockData.ts       Simulate mode data
│
├── package.json
└── HOW_TO_RUN.md             ← this file
```
