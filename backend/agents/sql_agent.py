"""
SQL Generation Agent.

Responsibilities:
  1. For each hypothesis from the schema agent, call Gemini 1.5 Flash to generate SQL.
  2. Validate that every generated query is SELECT-only (reject any mutation keyword).
  3. Execute the validated SQL and return the result rows.
  4. Retry up to MAX_RETRIES times on execution failure.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, text

from agents.utils import Timer, call_gemini, make_log
from core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# SQL safety validation
# ---------------------------------------------------------------------------

# Any SQL containing these tokens (as whole words) is rejected outright.
_MUTATION_TOKENS = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "REPLACE", "UPSERT", "MERGE",
    "ATTACH", "DETACH", "EXEC", "EXECUTE",
    "GRANT", "REVOKE", "PRAGMA",
})


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Return (is_valid, rejection_reason).
    A query is valid only if:
      - It contains no mutation keywords (whole-word match, case-insensitive).
      - It starts with SELECT or WITH (after stripping comments).
    """
    # Strip SQL comments before tokenising
    no_comments = re.sub(r"--[^\n]*", " ", sql)
    no_comments = re.sub(r"/\*.*?\*/", " ", no_comments, flags=re.DOTALL)

    tokens = {m.upper() for m in re.findall(r"\b[A-Za-z_]\w*\b", no_comments)}
    bad = tokens & _MUTATION_TOKENS
    if bad:
        return False, f"SQL contains forbidden keyword(s): {sorted(bad)}"

    first_word = no_comments.strip().upper().split()[0] if no_comments.strip() else ""
    if first_word not in ("SELECT", "WITH"):
        return False, f"SQL must begin with SELECT or WITH, got '{first_word}'"

    return True, ""


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SQL_PROMPT = """\
You are a SQLite expert. Write a single SQL SELECT query for the task described below.

Table: {table_name}
Available columns: {columns}
Column classifications: {classifications}

Task description : {description}
Query type       : {hyp_type}
KPI column       : {kpi_col}
Date column      : {date_col}
Dimension column : {dim_col}

Guidelines per query type:
- mom_trend       : SELECT strftime('%Y-%m', {date_col}) AS period, \
{agg}("{kpi_col}") AS value FROM "{table_name}" \
WHERE "{date_col}" IS NOT NULL GROUP BY period ORDER BY period
- wow_trend       : SELECT strftime('%Y-%W', {date_col}) AS period, \
{agg}("{kpi_col}") AS value FROM "{table_name}" \
WHERE "{date_col}" IS NOT NULL GROUP BY period ORDER BY period
- segment_breakdown: SELECT "{dim_col}", {agg}("{kpi_col}") AS value \
FROM "{table_name}" WHERE "{kpi_col}" IS NOT NULL \
GROUP BY "{dim_col}" ORDER BY value DESC LIMIT 10
- anomaly         : SELECT "{date_col}", "{kpi_col}" \
FROM "{table_name}" WHERE "{kpi_col}" IS NOT NULL AND "{date_col}" IS NOT NULL \
ORDER BY "{date_col}" LIMIT 1000

Rules:
- Output ONLY the raw SQL query — no explanation, no markdown, no code fences.
- Never use INSERT, UPDATE, DELETE, DROP, or any mutation keyword.
- Use double-quotes around column names that may contain spaces or hyphens."""


def _pick_agg(kpi_col: str, classifications: Dict[str, str]) -> str:
    """Guess an appropriate aggregation function from the column name."""
    col_type = classifications.get(kpi_col, "metric")
    name_lower = kpi_col.lower()
    if any(w in name_lower for w in ("rate", "pct", "percent", "ratio", "avg", "average")):
        return "AVG"
    if any(w in name_lower for w in ("count", "num", "number", "qty", "quantity")):
        return "SUM"
    if col_type == "metric":
        return "SUM"
    return "COUNT"


def _generate_sql(hyp: Dict, schema_info: Dict, table_name: str) -> str:
    """Call Gemini 1.5 Flash to generate SQL for one hypothesis."""
    classifications = schema_info.get("classifications", {})
    columns = list(classifications.keys()) or ["*"]
    kpi_col = hyp.get("kpi_column", "")
    date_col = hyp.get("date_column") or "date"
    dim_col = hyp.get("dimension_column") or "category"
    agg = _pick_agg(kpi_col, classifications)

    prompt = _SQL_PROMPT.format(
        table_name=table_name,
        columns=", ".join(columns),
        classifications=str(classifications),
        description=hyp["description"],
        hyp_type=hyp["type"],
        kpi_col=kpi_col,
        date_col=date_col,
        dim_col=dim_col,
        agg=agg,
    )

    raw = call_gemini(prompt, max_tokens=400).strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```(?:sql)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _execute_sql(sql: str, engine) -> Tuple[List[Dict], Optional[str]]:
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(r._mapping) for r in result.fetchall()]
        return rows, None
    except Exception as exc:
        return [], str(exc)


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_sql_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    hypotheses: List[Dict] = state.get("hypotheses", [])
    schema_info: Dict = state.get("schema_info", {})
    table_name: str = state["table_name"]

    engine = create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )

    sql_results: List[Dict] = []
    n_ok = 0

    with Timer() as total_timer:
        for hyp in hypotheses:
            last_error: Optional[str] = None
            succeeded = False

            for attempt in range(MAX_RETRIES + 1):
                try:
                    sql = _generate_sql(hyp, schema_info, table_name)

                    valid, reason = validate_sql(sql)
                    if not valid:
                        logger.warning("SQL rejected [%s] %s: %s", hyp["id"], hyp["type"], reason)
                        sql_results.append({
                            "hypothesis_id": hyp["id"], "hypothesis": hyp,
                            "sql": sql, "data": [], "error": reason,
                        })
                        break  # no point retrying a rejected query

                    rows, exec_err = _execute_sql(sql, engine)
                    if exec_err and attempt < MAX_RETRIES:
                        last_error = exec_err
                        logger.warning("SQL exec error (attempt %d): %s", attempt + 1, exec_err)
                        continue

                    sql_results.append({
                        "hypothesis_id": hyp["id"], "hypothesis": hyp,
                        "sql": sql, "data": rows, "error": exec_err,
                    })
                    if not exec_err:
                        n_ok += 1
                    succeeded = True
                    break

                except Exception as exc:
                    last_error = str(exc)
                    if attempt < MAX_RETRIES:
                        continue
                    sql_results.append({
                        "hypothesis_id": hyp["id"], "hypothesis": hyp,
                        "sql": "", "data": [], "error": last_error,
                    })

    log = make_log(
        "sql_agent",
        "completed" if n_ok == len(hypotheses) else "partial",
        total_timer.elapsed_ms,
        details={"total": len(hypotheses), "succeeded": n_ok, "failed": len(hypotheses) - n_ok},
    )
    return {
        "sql_results": sql_results,
        "agent_logs": [log],
        "errors": [],
    }
