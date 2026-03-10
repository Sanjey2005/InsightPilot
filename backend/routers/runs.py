"""
Runs router.

  POST  /runs/                    Trigger a new analysis run (202 Accepted)
  GET   /runs/                    List all runs for the current user
  GET   /runs/{run_id}            Full run detail: logs + KPIs + insights
  GET   /runs/{run_id}/insights   Insights only for a run
  POST  /runs/test-agent          Dev endpoint to invoke a single agent in isolation
"""
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.database import get_db
from models.dataset import Dataset
from models.insight import Insight
from models.kpi import KPI
from models.run import Run
from models.user import User
from services.pipeline import execute_pipeline

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas (local to this router — Phase 3 may promote them)
# ---------------------------------------------------------------------------

class RunCreateRequest(BaseModel):
    dataset_id: str


class AgentLog(BaseModel):
    """Typed schema for a single agent's execution log entry."""
    agent: str
    status: str                    # "completed" | "failed" | "partial"
    started_at: str                # ISO-8601 datetime string
    duration_ms: int = 0
    error: Optional[str] = None
    details: Dict[str, Any] = {}


class RunResponse(BaseModel):
    id: str
    dataset_id: str
    user_id: str
    status: str
    insights_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    agent_logs: List[AgentLog] = []

    model_config = {"from_attributes": True}


class KPIResponse(BaseModel):
    id: str
    name: str
    value: Optional[float] = None
    delta_pct: Optional[float] = None
    period_label: Optional[str] = None


class InsightResponse(BaseModel):
    id: str
    type: str
    title: str
    narrative: str
    sql_used: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    data: Optional[List[Dict[str, Any]]] = None
    kpi_column: Optional[str] = None
    severity: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RunDetailResponse(RunResponse):
    kpis: List[KPIResponse] = []
    insights: List[InsightResponse] = []


# ── Test-agent request ────────────────────────────────────────────────────

class TestAgentRequest(BaseModel):
    agent: str       # schema_agent | sql_agent | insight_agent | viz_agent
    dataset_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_agent_logs(raw: Optional[str]) -> List[AgentLog]:
    """
    Deserialise the JSON agent_logs column into a list of typed AgentLog objects.
    Returns [] on missing/invalid data so RunDetailResponse is always well-formed.
    """
    if not raw:
        return []
    try:
        entries = json.loads(raw)
        return [AgentLog(**entry) for entry in (entries or [])]
    except Exception:
        return []


def _serialize_run(run: Run) -> RunResponse:
    return RunResponse(
        id=run.id,
        dataset_id=run.dataset_id,
        user_id=run.user_id,
        status=run.status,
        insights_count=run.insights_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        agent_logs=_parse_agent_logs(run.agent_logs),
    )


def _serialize_insight(ins: Insight) -> InsightResponse:
    return InsightResponse(
        id=ins.id,
        type=ins.type,
        title=ins.title,
        narrative=ins.narrative,
        sql_used=ins.sql_used,
        chart_config=json.loads(ins.chart_config) if ins.chart_config else None,
        data=json.loads(ins.data_json) if ins.data_json else None,
        kpi_column=ins.kpi_column,
        severity=ins.severity,
        created_at=ins.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a new analysis run. Returns immediately; pipeline runs in background.",
)
def create_run(
    body: RunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunResponse:
    dataset = (
        db.query(Dataset)
        .filter(Dataset.id == body.dataset_id, Dataset.user_id == current_user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if not dataset.table_name:
        raise HTTPException(status_code=400, detail="Dataset has no associated data table. Re-upload the CSV.")

    run = Run(
        id=str(uuid.uuid4()),
        dataset_id=dataset.id,
        user_id=current_user.id,
        status="queued",
        insights_count=0,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(
        execute_pipeline,
        run_id=run.id,
        dataset_id=dataset.id,
        user_id=current_user.id,
        table_name=dataset.table_name,
    )

    return _serialize_run(run)


@router.get(
    "/",
    response_model=List[RunResponse],
    summary="List all runs for the current user, newest first.",
)
def list_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[RunResponse]:
    rows = (
        db.query(Run)
        .filter(Run.user_id == current_user.id)
        .order_by(Run.created_at.desc())
        .all()
    )
    return [_serialize_run(r) for r in rows]


# ── IMPORTANT: /test-agent MUST be registered before /{run_id} so FastAPI
# does not attempt to match the literal string "test-agent" as a run_id. ─────

@router.post(
    "/test-agent",
    summary="[Dev] Run a single agent in isolation and return its raw output.",
    include_in_schema=True,
)
def test_agent(
    body: TestAgentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Run one agent against a dataset and return its raw state delta.
    Useful for iterating on agent prompts before wiring the full pipeline.

    Upstream agents are automatically chained so that each agent receives
    the outputs it depends on:
      schema_agent  → (no deps)
      sql_agent     → schema_agent output
      insight_agent → schema_agent + sql_agent output
      viz_agent     → schema_agent + sql_agent + insight_agent output
    """
    dataset = (
        db.query(Dataset)
        .filter(Dataset.id == body.dataset_id, Dataset.user_id == current_user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if not dataset.table_name:
        raise HTTPException(status_code=400, detail="Dataset has no data table.")

    base_state: Dict[str, Any] = {
        "run_id": "test",
        "dataset_id": dataset.id,
        "user_id": current_user.id,
        "table_name": dataset.table_name,
        "schema_info": {},
        "hypotheses": [],
        "kpi_candidates": [],
        "sql_results": [],
        "insights": [],
        "agent_logs": [],
        "errors": [],
    }

    agent_map = {
        "schema_agent":  "agents.schema_agent.run_schema_agent",
        "sql_agent":     "agents.sql_agent.run_sql_agent",
        "insight_agent": "agents.insight_agent.run_insight_agent",
        "viz_agent":     "agents.viz_agent.run_viz_agent",
    }

    if body.agent not in agent_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent '{body.agent}'. Valid: {list(agent_map)}",
        )

    import importlib
    module_path, fn_name = agent_map[body.agent].rsplit(".", 1)
    mod = importlib.import_module(module_path)
    fn = getattr(mod, fn_name)

    # Chain upstream agents so each receives its required inputs
    if body.agent in ("sql_agent", "insight_agent", "viz_agent"):
        from agents.schema_agent import run_schema_agent
        base_state.update(run_schema_agent(base_state))
    if body.agent in ("insight_agent", "viz_agent"):
        from agents.sql_agent import run_sql_agent
        base_state.update(run_sql_agent(base_state))
    if body.agent == "viz_agent":
        from agents.insight_agent import run_insight_agent
        base_state.update(run_insight_agent(base_state))

    result = fn(base_state)
    base_state.update(result)

    # Return a clean JSON-safe view (omit raw data rows for brevity)
    return {
        "agent": body.agent,
        "dataset_id": dataset.id,
        "table_name": dataset.table_name,
        "agent_logs": base_state.get("agent_logs", []),
        "errors": base_state.get("errors", []),
        "schema_info": base_state.get("schema_info", {}),
        "hypotheses_count": len(base_state.get("hypotheses", [])),
        "sql_results_count": len(base_state.get("sql_results", [])),
        "insights_count": len(base_state.get("insights", [])),
        "insights_preview": [
            {
                "id": i["id"],
                "type": i["type"],
                "title": i["title"],
                "severity": i["severity"],
                "narrative_snippet": i.get("narrative", "")[:200],
            }
            for i in base_state.get("insights", [])
        ],
    }


@router.get(
    "/{run_id}",
    response_model=RunDetailResponse,
    summary="Full run detail: status, agent logs, KPIs, and all insight cards.",
)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RunDetailResponse:
    run = (
        db.query(Run)
        .filter(Run.id == run_id, Run.user_id == current_user.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    kpis = db.query(KPI).filter(KPI.run_id == run_id).all()
    insights = (
        db.query(Insight)
        .filter(Insight.run_id == run_id)
        .order_by(Insight.created_at)
        .all()
    )

    return RunDetailResponse(
        **_serialize_run(run).model_dump(),
        kpis=[
            KPIResponse(
                id=k.id, name=k.name, value=k.value,
                delta_pct=k.delta_pct, period_label=k.period_label,
            )
            for k in kpis
        ],
        insights=[_serialize_insight(i) for i in insights],
    )


@router.get(
    "/{run_id}/insights",
    response_model=List[InsightResponse],
    summary="Return only the insight cards for a completed run.",
)
def get_run_insights(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[InsightResponse]:
    run = db.query(Run).filter(Run.id == run_id, Run.user_id == current_user.id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    insights = (
        db.query(Insight)
        .filter(Insight.run_id == run_id)
        .order_by(Insight.created_at)
        .all()
    )
    return [_serialize_insight(i) for i in insights]
