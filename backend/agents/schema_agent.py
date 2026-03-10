"""
Schema Discovery Agent.

Responsibilities:
  1. Read a sample of the uploaded SQLite table.
  2. Call Gemini 1.5 Flash to classify each column and propose KPI candidates.
  3. Build the fixed playbook hypotheses that the SQL agent will execute.
"""
import json
import logging
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import create_engine

from agents.utils import Timer, call_gemini, extract_json, make_log
from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CLASSIFY_PROMPT = """\
You are a senior data analyst. Given the schema and a sample of a business dataset, \
classify each column and identify analysis candidates.

Table: {table_name}
Columns with sample data:
{columns_json}

Classify each column as exactly one of:
- "metric"     : numeric quantity to measure (revenue, amount, price, count, quantity, rate…)
- "dimension"  : categorical value used for grouping (category, region, product, status, segment…)
- "date"       : date or datetime
- "id"         : identifier / primary key (not useful for analysis)
- "other"      : everything else

Also identify:
- The single best date column for time-series analysis (null if none)
- Up to 3 metric columns best suited for KPI tracking
- Up to 3 dimension columns best suited for segment analysis
- Up to 5 KPI candidates with a human-readable name and aggregation function

Respond ONLY with a valid JSON object matching this exact schema (no extra keys):
{{
  "classifications": {{ "<col>": "<type>", ... }},
  "date_column": "<col_or_null>",
  "metric_columns": ["<col>", ...],
  "dimension_columns": ["<col>", ...],
  "kpi_candidates": [
    {{"name": "<human label>", "column": "<col>", "aggregation": "SUM|AVG|COUNT|MAX|MIN"}}
  ]
}}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarise_columns(df: pd.DataFrame) -> List[Dict]:
    n = len(df)
    summary = []
    for col in df.columns:
        s = df[col]
        summary.append({
            "name": col,
            "pandas_dtype": str(s.dtype),
            "null_pct": round(s.isna().sum() / n * 100, 1) if n else 0,
            "unique_count": int(s.nunique()),
            "samples": [str(v) for v in s.dropna().head(3).tolist()],
        })
    return summary


def _build_hypotheses(schema_info: Dict, table_name: str) -> List[Dict]:
    """
    Convert schema classifications into the fixed insight-playbook hypotheses:
      - MoM trend     per metric column (if date col exists)
      - WoW trend     per metric column (if date col exists)
      - Segment       per (dimension × metric) pair (top 3 × top 2)
      - Anomaly       per metric column over time (if date col exists)
    """
    date_col = schema_info.get("date_column")
    metric_cols: List[str] = schema_info.get("metric_columns", [])[:3]
    dimension_cols: List[str] = schema_info.get("dimension_columns", [])[:3]

    hypotheses: List[Dict] = []
    h = 0

    if date_col:
        for metric in metric_cols:
            hypotheses.append({
                "id": f"h{h}", "type": "mom_trend",
                "description": f"Month-over-month trend for {metric}",
                "kpi_column": metric, "date_column": date_col, "dimension_column": None,
            }); h += 1
            hypotheses.append({
                "id": f"h{h}", "type": "wow_trend",
                "description": f"Week-over-week trend for {metric}",
                "kpi_column": metric, "date_column": date_col, "dimension_column": None,
            }); h += 1

    for dim in dimension_cols:
        for metric in metric_cols[:2]:
            hypotheses.append({
                "id": f"h{h}", "type": "segment_breakdown",
                "description": f"Top segments of {metric} by {dim}",
                "kpi_column": metric, "date_column": date_col, "dimension_column": dim,
            }); h += 1

    if date_col:
        for metric in metric_cols:
            hypotheses.append({
                "id": f"h{h}", "type": "anomaly",
                "description": f"Anomaly detection for {metric} over time",
                "kpi_column": metric, "date_column": date_col, "dimension_column": None,
            }); h += 1

    return hypotheses


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_schema_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    table_name: str = state["table_name"]

    with Timer() as t:
        try:
            engine = create_engine(
                settings.database_url, connect_args={"check_same_thread": False}
            )
            with engine.connect() as conn:
                df = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 200', conn)

            col_summary = _summarise_columns(df)

            schema_info = extract_json(call_gemini(
                _CLASSIFY_PROMPT.format(
                    table_name=table_name,
                    columns_json=json.dumps(col_summary, indent=2),
                ),
                max_tokens=1_500,
            ))
            hypotheses = _build_hypotheses(schema_info, table_name)

            log = make_log(
                "schema_agent", "completed", t.elapsed_ms,
                details={"columns": len(df.columns), "hypotheses": len(hypotheses)},
            )
            return {
                "schema_info": schema_info,
                "hypotheses": hypotheses,
                "kpi_candidates": schema_info.get("kpi_candidates", []),
                "agent_logs": [log],
                "errors": [],
            }

        except Exception as exc:
            logger.exception("schema_agent failed")
            log = make_log("schema_agent", "failed", t.elapsed_ms, error=str(exc))
            return {
                "schema_info": {},
                "hypotheses": [],
                "kpi_candidates": [],
                "agent_logs": [log],
                "errors": [f"schema_agent: {exc}"],
            }
