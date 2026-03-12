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
    from sqlalchemy import text
    from core.database import engine

    kpi_candidates: List[Dict] = state.get("kpi_candidates", [])
    table_name: str = state.get("table_name", "")
    schema_info: Dict = state.get("schema_info", {})
    date_column = schema_info.get("date_column")

    if not table_name:
        logger.warning("_derive_kpis: no table_name in state — returning empty")
        return []

    # ── Build a lookup of actual column names in the table (for case-
    #    insensitive matching — LLM may return "Revenue" while the real
    #    column is "revenue"). ─────────────────────────────────────────
    actual_columns: Dict[str, str] = {}  # lower-cased → real name
    try:
        with engine.connect() as conn:
            pragma_rows = conn.execute(
                text(f'PRAGMA table_info("{table_name}")')
            ).fetchall()
        for row in pragma_rows:
            real_name = str(row[1])
            actual_columns[real_name.lower()] = real_name
        logger.info(
            "_derive_kpis: table %s has columns: %s",
            table_name, list(actual_columns.values()),
        )
    except Exception as exc:
        logger.error("_derive_kpis: PRAGMA table_info failed for %s: %s", table_name, exc)

    def _resolve_col(col: str) -> str:
        """Resolve a column name to its exact casing in the table."""
        if col in actual_columns.values():
            return col
        return actual_columns.get(col.lower(), col)

    logger.info(
        "_derive_kpis: received %d kpi_candidates from schema_agent",
        len(kpi_candidates),
    )

    # ── If schema_agent produced no candidates, discover numeric columns
    # directly from the SQLite table so KPIs are always generated. ─────────
    if not kpi_candidates:
        logger.warning("_derive_kpis: no kpi_candidates — running PRAGMA fallback")
        _NUMERIC_AFFINITY = {"INTEGER", "REAL", "NUMERIC", "INT", "FLOAT", "DOUBLE"}
        for real_name in actual_columns.values():
            col_lower = real_name.lower()
            # Skip ID-like columns
            if col_lower == "id" or col_lower.endswith("_id"):
                continue
            # Look up the type from the pragma rows we already fetched
            col_type = ""
            for row in pragma_rows:
                if str(row[1]) == real_name:
                    col_type = (str(row[2]) or "").upper().split("(")[0].strip()
                    break
            if any(t in col_type for t in _NUMERIC_AFFINITY):
                if any(kw in col_lower for kw in {"price", "rate", "score", "avg", "average", "ratio"}):
                    agg = "AVG"
                else:
                    agg = "SUM"
                kpi_candidates.append({
                    "name": real_name.replace("_", " ").title(),
                    "column": real_name,
                    "aggregation": agg,
                })
                if len(kpi_candidates) >= 3:
                    break
        logger.info("_derive_kpis: PRAGMA fallback found %d numeric columns", len(kpi_candidates))

    # ── If schema_info has no date_column, try to detect one via columns ──
    if not date_column:
        _DATE_HINTS = {"date", "time", "month", "year", "week", "day", "period", "created", "updated"}
        for real_name in actual_columns.values():
            if any(kw in real_name.lower() for kw in _DATE_HINTS):
                date_column = real_name
                logger.info("_derive_kpis: auto-detected date_column=%s", date_column)
                break
    else:
        # Resolve casing for the date column too
        date_column = _resolve_col(date_column)

    kpis: List[KPI] = []
    seen: set = set()

    for candidate in kpi_candidates:
        col  = _resolve_col(candidate.get("column", ""))
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
            sql_agg = f'SELECT {agg_fn}("{col}") AS kpi_val FROM "{table_name}"'
            with engine.connect() as conn:
                row = conn.execute(text(sql_agg)).fetchone()
            if row and row[0] is not None:
                value = round(float(row[0]), 2)
            else:
                logger.warning(
                    "KPI query returned NULL for %s (col=%s, agg=%s)",
                    name, col, agg_fn,
                )
        except Exception as exc:
            logger.error("KPI query failed for %s (col=%s): %s", name, col, exc)

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

        logger.info(
            "KPI derived: name=%s, col=%s, value=%s, delta=%s",
            name, col, value, delta_pct,
        )
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


