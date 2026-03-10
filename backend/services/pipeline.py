"""
Pipeline orchestrator.

execute_pipeline() is called as a FastAPI BackgroundTask. It:
  1. Updates the Run row to status="running".
  2. Invokes the LangGraph pipeline.
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

from agents.supervisor import PipelineState, pipeline
from core.database import SessionLocal
from models.insight import Insight
from models.kpi import KPI
from models.run import Run

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# KPI derivation
# ---------------------------------------------------------------------------

def _derive_kpis(state: PipelineState, run_id: str) -> List[KPI]:
    """
    Build KPI records from the schema agent's kpi_candidates and matching
    SQL results.  Caps at 5 KPIs per the PRD spec.
    """
    kpi_candidates: List[Dict] = state.get("kpi_candidates", [])
    sql_results: List[Dict] = state.get("sql_results", [])
    kpis: List[KPI] = []
    seen: set = set()

    for candidate in kpi_candidates:
        col  = candidate.get("column", "")
        name = candidate.get("name", col)
        if name in seen:
            continue
        seen.add(name)

        value: float | None = None
        delta_pct: float | None = None
        period_label = "all time"

        # Find any aggregated SQL result that covers this column
        for result in sql_results:
            hyp = result.get("hypothesis", {})
            if hyp.get("kpi_column") != col:
                continue
            data = result.get("data", [])
            if not data:
                continue

            # Last row = most recent period value
            last_row = data[-1]
            for v in last_row.values():
                try:
                    value = float(v)
                    break
                except (TypeError, ValueError):
                    pass

            # Delta vs the previous period
            if len(data) >= 2:
                prev_row = data[-2]
                prev_val: float | None = None
                for v in prev_row.values():
                    try:
                        prev_val = float(v)
                        break
                    except (TypeError, ValueError):
                        pass
                if prev_val and prev_val != 0 and value is not None:
                    delta_pct = round((value - prev_val) / prev_val * 100, 2)

            # Use the period column name as label if available
            period_key = list(last_row.keys())[0]
            period_label = str(last_row.get(period_key, "all time"))
            break

        kpis.append(KPI(
            id=str(uuid.uuid4()),
            run_id=run_id,
            name=name,
            value=value,
            delta_pct=delta_pct,
            period_label=period_label,
            created_at=datetime.utcnow(),
        ))

    return kpis[:5]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def execute_pipeline(run_id: str, dataset_id: str, user_id: str, table_name: str) -> None:
    """Run the full LangGraph pipeline and persist results."""
    db: Session = SessionLocal()
    try:
        # ── Mark as running ────────────────────────────────────────────
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            logger.error("execute_pipeline: run %s not found", run_id)
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        # ── Invoke LangGraph ───────────────────────────────────────────
        initial_state: PipelineState = {
            "run_id": run_id,
            "dataset_id": dataset_id,
            "user_id": user_id,
            "table_name": table_name,
            "schema_info": {},
            "hypotheses": [],
            "kpi_candidates": [],
            "sql_results": [],
            "insights": [],
            "agent_logs": [],
            "errors": [],
        }
        final_state: PipelineState = pipeline.invoke(initial_state)

        # ── Persist insights ───────────────────────────────────────────
        insight_records: List[Insight] = []
        for ins in final_state.get("insights", []):
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
        kpi_records = _derive_kpis(final_state, run_id)
        db.add_all(kpi_records)

        # ── Finalise run ───────────────────────────────────────────────
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.insights_count = len(insight_records)
        run.agent_logs = json.dumps(final_state.get("agent_logs", []))
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
