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

from agents.utils import Timer, call_gemini, extract_json, make_log

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
    Uses pd.to_datetime(errors='coerce') for robust date detection that works
    with ISO, slash-separated, and mixed date formats.
    Used as a fallback when the Groq API is unavailable.
    """
    classifications: Dict[str, str] = {}
    date_col: str | None = None
    metric_cols: List[str] = []
    dimension_cols: List[str] = []
    kpi_candidates: List[Dict] = []

    for col in df.columns:
        col_lower = col.lower()
        dtype = str(df[col].dtype)

        # Detect ID columns first (only exact / suffix matches, not substrings)
        if col_lower == "id" or col_lower.endswith("_id") or col_lower.endswith("id"):
            if not any(kw in col_lower for kw in _DATE_KEYWORDS | _METRIC_KEYWORDS):
                classifications[col] = "id"
                continue

        # Detect datetime dtype columns
        if dtype.startswith("datetime"):
            classifications[col] = "date"
            if date_col is None:
                date_col = col
            continue

        # Detect date columns by name keyword match
        if any(kw in col_lower for kw in _DATE_KEYWORDS):
            # Try to parse to confirm it holds date-like values
            parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            if parsed.notna().mean() > 0.5:
                classifications[col] = "date"
                if date_col is None:
                    date_col = col
                continue

        # Detect date columns by content (object columns that parse as dates)
        if dtype == "object":
            parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            if parsed.notna().mean() > 0.7:  # >70% parseable → it's a date
                classifications[col] = "date"
                if date_col is None:
                    date_col = col
                continue

        # Detect metrics by dtype
        if dtype in ("int64", "float64") or dtype.startswith("int") or dtype.startswith("float"):
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
    Build a BALANCED set of hypotheses so all insight types are represented.

    Allocation (cap = 8):
      - 1 MoM trend        (primary metric)
      - up to 2 segments   (each dimension × primary metric)
      - up to 2 anomalies  (top 2 metrics)
      - up to 3 WoW trends (filling remaining slots)
    """
    date_col = schema_info.get("date_column")
    metric_cols: List[str] = schema_info.get("metric_columns", [])[:3]
    dimension_cols: List[str] = schema_info.get("dimension_columns", [])[:3]

    hypotheses: List[Dict] = []
    h = 0

    # ── 1. One MoM trend for the primary metric ──────────────────────────
    if date_col and metric_cols:
        primary_metric = metric_cols[0]
        hypotheses.append({
            "id": f"h{h}", "type": "mom_trend",
            "description": f"Month-over-month trend for {primary_metric}",
            "kpi_column": primary_metric, "date_column": date_col, "dimension_column": None,
        }); h += 1

    # ── 2. Segment breakdowns (up to 2) ──────────────────────────────────
    for dim in dimension_cols[:2]:
        if metric_cols:
            hypotheses.append({
                "id": f"h{h}", "type": "segment_breakdown",
                "description": f"Top segments of {metric_cols[0]} by {dim}",
                "kpi_column": metric_cols[0], "date_column": date_col, "dimension_column": dim,
            }); h += 1

    # ── 3. Anomaly detection (up to 2 metrics) ───────────────────────────
    if date_col:
        for metric in metric_cols[:2]:
            hypotheses.append({
                "id": f"h{h}", "type": "anomaly",
                "description": f"Anomaly detection for {metric} over time",
                "kpi_column": metric, "date_column": date_col, "dimension_column": None,
            }); h += 1

    # ── 4. WoW trends for remaining metrics (fill up to cap of 8) ────────
    if date_col:
        for metric in metric_cols:
            if len(hypotheses) >= 8:
                break
            hypotheses.append({
                "id": f"h{h}", "type": "wow_trend",
                "description": f"Week-over-week trend for {metric}",
                "kpi_column": metric, "date_column": date_col, "dimension_column": None,
            }); h += 1

    return hypotheses[:8]  # Hard-cap at 8 to limit downstream API calls


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_schema_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    table_name: str = state["table_name"]

    with Timer() as t:
        try:
            from core.database import engine
            with engine.connect() as conn:
                df = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 50', conn)

            col_summary = _summarise_columns(df)

            # Always run heuristic as a reliable baseline
            heuristic_info = _heuristic_classify_columns(df)

            try:
                # PRIMARY: LLM-based column classification
                llm_info = extract_json(call_gemini(
                    _CLASSIFY_PROMPT.format(
                        table_name=table_name,
                        columns_json=json.dumps(col_summary, indent=2),
                    ),
                    max_tokens=1_500,
                ))
                # Merge: use LLM results, fall back to heuristic for any missing/empty fields
                schema_info = {
                    "classifications":  llm_info.get("classifications")   or heuristic_info["classifications"],
                    "date_column":      llm_info.get("date_column")       or heuristic_info.get("date_column"),
                    "metric_columns":   llm_info.get("metric_columns")    or heuristic_info["metric_columns"],
                    "dimension_columns": llm_info.get("dimension_columns") or heuristic_info["dimension_columns"],
                    "kpi_candidates":   llm_info.get("kpi_candidates")    or heuristic_info["kpi_candidates"],
                }

                # ── Normalise LLM column references to match actual DataFrame
                # column names (case-insensitive). The LLM may return "Revenue"
                # but the real sanitised column is "revenue". ──────────────────
                col_lookup = {c.lower(): c for c in df.columns}

                def _fix_col(name: str) -> str:
                    return col_lookup.get(name.lower(), name) if name else name

                schema_info["date_column"] = _fix_col(schema_info.get("date_column") or "")
                schema_info["metric_columns"] = [
                    _fix_col(c) for c in schema_info.get("metric_columns", [])
                ]
                schema_info["dimension_columns"] = [
                    _fix_col(c) for c in schema_info.get("dimension_columns", [])
                ]
                for kc in schema_info.get("kpi_candidates", []):
                    kc["column"] = _fix_col(kc.get("column", ""))
                logger.info(
                    "schema_agent: LLM classification succeeded; kpi_candidates=%d",
                    len(schema_info["kpi_candidates"]),
                )
            except Exception as llm_exc:
                # FALLBACK: heuristic only
                logger.warning(
                    "schema_agent: LLM unavailable (%s) — using heuristic fallback",
                    llm_exc,
                )
                schema_info = heuristic_info

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
