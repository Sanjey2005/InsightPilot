"""
InsightPilot FastAPI backend.

Start the server:
    uvicorn main:app --reload --port 8000

Interactive docs:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import Base, engine

# ── Import models so SQLAlchemy registers them before create_all() ────────
import models.user             # noqa: F401
import models.dataset          # noqa: F401
import models.run              # noqa: F401
import models.insight          # noqa: F401
import models.kpi              # noqa: F401
import models.insight_feedback # noqa: F401

from routers import datasets, runs, insights, chat

# ── Create all metadata tables on startup ────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="InsightPilot API",
    description="AI-powered analytics copilot backend.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(datasets.router, prefix="/datasets",  tags=["datasets"])
app.include_router(runs.router,     prefix="/runs",      tags=["runs"])
app.include_router(insights.router, prefix="/insights",  tags=["insights"])
app.include_router(chat.router,     prefix="/chat",      tags=["chat"])


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": "0.3.0"}
