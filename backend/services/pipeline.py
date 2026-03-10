"""
Pipeline orchestrator.

execute_pipeline() is called as a FastAPI BackgroundTask. It:
  1. Updates the Run row to status="running".
  2. Invokes each LangGraph agent in sequence, flushing logs to DB after each.
  3. Persists all Insight and KPI records.
  4. Updates the Run row to status="completed" (or "failed").

All DB work uses a fresh SQLAlchemy session so it is safe to run in a
background thread separate from the request session.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from agents.schema_agent import run_schema_agent
from agents.sql_agent import run_sql_agent
from agents.insight_agent import run_insight_agent
from agents.viz_agent import run_viz_agent
from core.database import SessionLocal
from models.insight import Insight
from models.kpi import KPI
from models.run import Run

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# KPI derivation
# ---------------------------------------------------------------------------

def _derive_kpis(state: Dict[str, Any], run_id: str) -> List[KPI]:
    """
    Compute KPI values directly from the SQLite table using proper SQL
    aggregations (SUM, AVG, COUNT).  For time-delta, compares the most
    recent month to the prior month.

    Falls back gracefully: if a query fails, the KPI still appears with
    value=None, delta_pct=None so the frontend can render a placeholder.
    """
    from sqlalchemy import create_engine, text
    from core.config import settings

    kpi_candidates: List[Dict] = state.get("kpi_candidates", [])
    table_name: str = state.get("table_name", "")
    schema_info: Dict = state.get("schema_info", {})
    date_column = schema_info.get("date_column")

    if not table_name:
        return []

    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )

    kpis: List[KPI] = []
    seen: set = set()

    for candidate in kpi_candidates:
        col  = candidate.get("column", "")
        name = candidate.get("name", col)
        agg  = candidate.get("aggregation", "SUM").upper()
        if name in seen:
            continue
        seen.add(name)

        value: float | None = None
        delta_pct: float | None = None
        period_label = "all time"

        # ── 1. Compute the all-time aggregate value ────────────────────
        agg_fn = agg if agg in {"SUM", "AVG", "COUNT", "MAX", "MIN"} else "SUM"
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(f'SELECT {agg_fn}("{col}") AS kpi_val FROM "{table_name}"')
                ).fetchone()
            if row and row[0] is not None:
                value = round(float(row[0]), 2)
        except Exception as exc:
            logger.warning("KPI query failed for %s: %s", col, exc)

        # ── 2. Compute MoM delta if a date column exists ──────────────
        if date_column and value is not None:
            try:
                sql_mom = f"""
                    SELECT strftime('%Y-%m', "{date_column}") AS mo,
                           {agg_fn}("{col}") AS val
                    FROM "{table_name}"
                    GROUP BY mo
                    ORDER BY mo DESC
                    LIMIT 2
                """
                with engine.connect() as conn:
                    rows = conn.execute(text(sql_mom)).fetchall()
                if len(rows) >= 2:
                    curr_val = float(rows[0][1]) if rows[0][1] else 0
                    prev_val = float(rows[1][1]) if rows[1][1] else 0
                    if prev_val != 0:
                        delta_pct = round((curr_val - prev_val) / prev_val * 100, 1)
                    period_label = str(rows[0][0])
                elif len(rows) == 1:
                    period_label = str(rows[0][0])
            except Exception as exc:
                logger.warning("KPI delta query failed for %s: %s", col, exc)

        kpis.append(KPI(
            id=str(uuid.uuid4()),
            run_id=run_id,
            name=name,
            value=value,
            delta_pct=delta_pct,
            period_label=period_label,
            created_at=datetime.utcnow(),
        ))

    # ── Always add "Total Orders" KPI (COUNT of all rows) ─────────────
    if "Total Orders" not in seen:
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}"')
                ).fetchone()
            order_count = int(row[0]) if row else 0
        except Exception:
            order_count = 0
        kpis.append(KPI(
            id=str(uuid.uuid4()),
            run_id=run_id,
            name="Total Orders",
            value=float(order_count),
            delta_pct=None,
            period_label="all time",
            created_at=datetime.utcnow(),
        ))

    return kpis[:5]



# ---------------------------------------------------------------------------
# Helper: flush accumulated logs to the DB mid-run
# ---------------------------------------------------------------------------

def _flush_logs(db: Session, run: Run, logs: List[Dict]) -> None:
    """Commit the current agent_logs list to the Run row immediately."""
    run.agent_logs = json.dumps(logs)
    db.commit()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def execute_pipeline(run_id: str, dataset_id: str, user_id: str, table_name: str) -> None:
    """Run the full pipeline agent-by-agent, flushing logs after each step."""
    db: Session = SessionLocal()
    try:
        # ── Mark as running ────────────────────────────────────────────
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            logger.error("execute_pipeline: run %s not found", run_id)
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        run.agent_logs = json.dumps([])
        db.commit()

        # ── Build initial state ────────────────────────────────────────
        state: Dict[str, Any] = {
            "run_id":       run_id,
            "dataset_id":   dataset_id,
            "user_id":      user_id,
            "table_name":   table_name,
            "schema_info":  {},
            "hypotheses":   [],
            "kpi_candidates": [],
            "sql_results":  [],
            "insights":     [],
            "agent_logs":   [],
            "errors":       [],
        }

        # ── Run agents sequentially, flushing logs after each ──────────
        agent_fns = [
            ("schema_agent",  run_schema_agent),
            ("sql_agent",     run_sql_agent),
            ("insight_agent", run_insight_agent),
            ("viz_agent",     run_viz_agent),
        ]

        accumulated_logs: List[Dict] = []

        for agent_name, agent_fn in agent_fns:
            logger.info("Run %s: starting %s", run_id, agent_name)
            try:
                delta = agent_fn(state)
                state.update(delta)
                # The agent appends its log entry to state["agent_logs"]
                # Accumulate and flush to DB immediately
                accumulated_logs = state.get("agent_logs", [])
                _flush_logs(db, run, accumulated_logs)
                logger.info(
                    "Run %s: %s completed (%d logs so far)",
                    run_id, agent_name, len(accumulated_logs),
                )
            except Exception as agent_exc:
                logger.exception("Run %s: %s raised an exception", run_id, agent_name)
                error_log = {
                    "agent": agent_name,
                    "status": "failed",
                    "started_at": datetime.utcnow().isoformat(),
                    "duration_ms": 0,
                    "error": str(agent_exc),
                    "details": {},
                }
                accumulated_logs.append(error_log)
                state["agent_logs"] = accumulated_logs
                state["errors"].append(f"{agent_name}: {agent_exc}")
                _flush_logs(db, run, accumulated_logs)
                # Continue to next agents even if one fails

        # ── Persist insights ───────────────────────────────────────────
        insight_records: List[Insight] = []
        for ins in state.get("insights", []):
            insight_records.append(Insight(
                id=ins.get("id", str(uuid.uuid4())),
                run_id=run_id,
                user_id=user_id,
                type=ins["type"],
                title=ins["title"],
                narrative=ins["narrative"],
                sql_used=ins.get("sql_used"),
                chart_config=json.dumps(ins["chart_config"]) if ins.get("chart_config") else None,
                data_json=json.dumps(ins.get("data", []), default=str),
                kpi_column=ins.get("kpi_column"),
                severity=ins.get("severity", "medium"),
                created_at=datetime.utcnow(),
            ))
        db.add_all(insight_records)

        # ── Persist KPIs ───────────────────────────────────────────────
        kpi_records = _derive_kpis(state, run_id)
        db.add_all(kpi_records)

        # ── Finalise run ───────────────────────────────────────────────
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.insights_count = len(insight_records)
        run.agent_logs = json.dumps(accumulated_logs)
        db.commit()

        logger.info(
            "Run %s completed: %d insights, %d KPIs",
            run_id, len(insight_records), len(kpi_records),
        )

    except Exception as exc:
        logger.exception("Pipeline failed for run %s: %s", run_id, exc)
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                run.agent_logs = json.dumps([{
                    "agent": "pipeline",
                    "status": "failed",
                    "started_at": datetime.utcnow().isoformat(),
                    "duration_ms": 0,
                    "error": str(exc),
                    "details": {},
                }])
                db.commit()
        except Exception:
            logger.exception("Could not update run %s to failed status", run_id)
    finally:
        db.close()


