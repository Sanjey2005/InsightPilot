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


# ── KEY INSIGHT: heuristic classifier when LLM is unavailable ──────────────

_METRIC_KEYWORDS    = {"revenue", "amount", "price", "total", "sales", "cost",
                       "profit", "quantity", "qty", "count", "sum", "value",
                       "rate", "score", "income", "spend", "budget", "margin"}
_DIMENSION_KEYWORDS = {"category", "segment", "region", "status", "type",
                       "channel", "method", "name", "product", "team",
                       "department", "country", "city", "group", "tier"}
_DATE_KEYWORDS      = {"date", "time", "timestamp", "at", "created", "updated",
                       "month", "year", "week", "day", "period"}
_ID_KEYWORDS        = {"id", "key", "uuid", "code", "no", "num", "ref"}


def _heuristic_classify_columns(df: pd.DataFrame) -> Dict:
    """
    Classify columns using pandas dtypes and column-name keyword matching.
    Used as a fallback when the Gemini API is unavailable.
    """
    classifications: Dict[str, str] = {}
    date_col: str | None = None
    metric_cols: List[str] = []
    dimension_cols: List[str] = []
    kpi_candidates: List[Dict] = []

    for col in df.columns:
        col_lower = col.lower()
        dtype = str(df[col].dtype)

        # Detect ID columns first
        if any(kw in col_lower for kw in _ID_KEYWORDS):
            classifications[col] = "id"
            continue

        # Detect date columns by dtype or name
        if dtype in ("datetime64[ns]", "object") and (
            any(kw in col_lower for kw in _DATE_KEYWORDS)
            or df[col].astype(str).str.match(r"\d{4}-\d{2}-\d{2}").mean() > 0.5
        ):
            classifications[col] = "date"
            if date_col is None:
                date_col = col
            continue

        # Detect metrics by dtype
        if dtype in ("int64", "float64") or dtype.startswith("int") or dtype.startswith("float"):
            if any(kw in col_lower for kw in _METRIC_KEYWORDS):
                classifications[col] = "metric"
                metric_cols.append(col)
            else:
                # Numeric but not a known metric keyword — default metric
                classifications[col] = "metric"
                metric_cols.append(col)
            continue

        # Detect dimensions
        if (
            any(kw in col_lower for kw in _DIMENSION_KEYWORDS)
            or df[col].nunique() < max(10, len(df) * 0.2)
        ):
            classifications[col] = "dimension"
            dimension_cols.append(col)
            continue

        classifications[col] = "other"

    # Trim to top candidates
    metric_cols   = metric_cols[:3]
    dimension_cols = dimension_cols[:3]

    # Build KPI candidates from metric columns
    for col in metric_cols:
        col_lower = col.lower()
        agg = "SUM"
        if any(kw in col_lower for kw in {"price", "rate", "score", "avg", "average", "ratio"}):
            agg = "AVG"
        elif any(kw in col_lower for kw in {"count", "qty", "quantity", "num", "orders"}):
            agg = "COUNT"
        kpi_candidates.append({"name": col.replace("_", " ").title(), "column": col, "aggregation": agg})

    return {
        "classifications": classifications,
        "date_column": date_col,
        "metric_columns": metric_cols,
        "dimension_columns": dimension_cols,
        "kpi_candidates": kpi_candidates,
    }



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

    return hypotheses[:6]  # Hard-cap: limits downstream SQL + narrative API calls


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
                df = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 50', conn)

            col_summary = _summarise_columns(df)

            try:
                # PRIMARY: LLM-based column classification
                schema_info = extract_json(call_gemini(
                    _CLASSIFY_PROMPT.format(
                        table_name=table_name,
                        columns_json=json.dumps(col_summary, indent=2),
                    ),
                    max_tokens=1_500,
                ))
                logger.info("schema_agent: Gemini classification succeeded")
            except Exception as llm_exc:
                # FALLBACK: heuristic classification so pipeline can still run
                logger.warning(
                    "schema_agent: Gemini unavailable (%s) — using heuristic fallback",
                    llm_exc,
                )
                schema_info = _heuristic_classify_columns(df)

            hypotheses = _build_hypotheses(schema_info, table_name)

            log = make_log(
                "schema_agent", "completed", t.elapsed_ms,
                details={
                    "columns": len(df.columns),
                    "hypotheses": len(hypotheses),
                    "llm_used": "heuristic" not in str(schema_info.get("classifications", {})),
                    "date_column": schema_info.get("date_column"),
                    "metric_columns": schema_info.get("metric_columns", []),
                },
            )
            return {
                "schema_info": schema_info,
                "hypotheses": hypotheses,
                "kpi_candidates": schema_info.get("kpi_candidates", [])[:3],  # cap to 3
                "agent_logs": state.get("agent_logs", []) + [log],
                "errors": state.get("errors", []),
            }

        except Exception as exc:
            logger.exception("schema_agent failed")
            log = make_log("schema_agent", "failed", t.elapsed_ms, error=str(exc))
            return {
                "schema_info": {},
                "hypotheses": [],
                "kpi_candidates": [],
                "agent_logs": state.get("agent_logs", []) + [log],
                "errors": state.get("errors", []) + [f"schema_agent: {exc}"],
            }
