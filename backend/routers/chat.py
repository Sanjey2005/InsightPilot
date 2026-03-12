"""
Copilot Chat router — Phase 3.

  POST /chat/query          NLQ → SQL → narrative answer + chart config
  GET  /chat/suggestions    3 pre-generated starter questions for a dataset's schema
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from agents.sql_agent import validate_sql
from agents.utils import call_gemini, extract_json
from core.auth import get_current_user
from core.database import get_db
from models.dataset import Dataset
from models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Schema conversion helper
# ---------------------------------------------------------------------------

# Maps the inferred_type values from SchemaPreview → sql_agent classification format
_TYPE_TO_CLASS = {
    "integer": "metric",
    "float":   "metric",
    "datetime":"date",
    "boolean": "dimension",
    "string":  "dimension",
}


def _schema_preview_to_info(schema_json: str) -> Dict[str, Any]:
    """
    Convert the stored SchemaPreview JSON (from CSV upload) into the schema_info
    dict format expected by SQL generation prompts.

    Returns: { classifications, date_column, metric_columns, dimension_columns,
                columns_with_types (for prompts) }
    """
    data = json.loads(schema_json)
    classifications: Dict[str, str] = {}
    date_col: Optional[str] = None
    metric_cols: List[str] = []
    dimension_cols: List[str] = []
    columns_desc: List[str] = []

    for col in data.get("columns", []):
        name = col["name"]
        inferred = col.get("inferred_type", "string")
        cls = _TYPE_TO_CLASS.get(inferred, "dimension")
        classifications[name] = cls
        columns_desc.append(f"{name} ({inferred})")

        if cls == "date" and date_col is None:
            date_col = name
        elif cls == "metric":
            metric_cols.append(name)
        elif cls == "dimension":
            dimension_cols.append(name)

    return {
        "classifications": classifications,
        "date_column": date_col,
        "metric_columns": metric_cols[:5],
        "dimension_columns": dimension_cols[:5],
        "columns_with_types": ", ".join(columns_desc),
    }


def _sample_rows_text(schema_json: str, max_cols: int = 6) -> str:
    """Return a compact sample-values string to include in prompts."""
    data = json.loads(schema_json)
    lines: List[str] = []
    for col in data.get("columns", [])[:max_cols]:
        samples = ", ".join(str(v) for v in col.get("sample_values", []))
        lines.append(f"  {col['name']}: [{samples}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_NLQ_SQL_PROMPT = """\
You are a SQLite expert. Convert the business question below into a single SQL SELECT query.

Table   : {table_name}
Columns : {columns_with_types}
Samples :
{sample_rows}

Question: {question}

Rules:
- Output ONLY the raw SQL query — no explanation, no markdown, no code fences.
- Use SELECT only — never INSERT, UPDATE, DELETE, DROP, or any mutation keyword.
- LIMIT raw row results to 200; aggregation queries do not need a LIMIT.
- If the question asks for a trend over time, GROUP BY a date period using strftime().
- If the question asks for top/best/worst N, use ORDER BY … DESC LIMIT 10.
- Use double-quotes around column names that contain spaces or hyphens."""

_NLQ_NARRATIVE_PROMPT = """\
You are a concise business analyst answering a data question.

Question : {question}
SQL used : {sql}
Result   :
{result_summary}

Write a direct 2–3 sentence answer to the question.
Rules:
- Reference specific numbers from the result.
- Use plain business language — no SQL, no technical jargon.
- Maximum 3 sentences. No headers, no bullet points.
- Do NOT add any disclaimer — one will be appended automatically."""

_SUGGESTIONS_PROMPT = """\
You are a business analyst. Given a dataset schema, suggest exactly 3 natural language \
questions a non-technical user might want to ask about this data.

Table   : {table_name}
Columns : {columns_with_types}
Samples :
{sample_rows}

Rules:
- Each question must be answerable with a single SQL query on this table.
- Questions should cover different insight types: one trend/time-series, one segment/top-N, \
one summary/KPI.
- Phrase questions in plain business English (no SQL, no column names).
- Return ONLY a JSON array of exactly 3 question strings. No explanation.

Example format: ["Question one?", "Question two?", "Question three?"]"""

_NLQ_VIZ_PROMPT = """\
You are a data-visualization expert. Given a query result, produce a Recharts chart config.

Question: {question}
Result columns: {columns}
Sample data:
{sample_data}

Choose ONE chart_type: line | bar | area | scatter

Guidelines:
- Time-series / trend data → line or area (x = date/period column)
- Category / segment data  → bar  (x = category column)
- Scatter / correlation    → scatter

Respond ONLY with a valid JSON object:
{{
  "chart_type" : "line|bar|area|scatter",
  "x_key"      : "<column name>",
  "y_key"      : "<column name>",
  "x_label"    : "<human label>",
  "y_label"    : "<human label>",
  "color"      : "#06b6d4",
  "title"      : "<short title>"
}}"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _execute_sql(sql: str) -> tuple[List[Dict], Optional[str]]:
    from core.database import engine
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(r._mapping) for r in result.fetchall()]
        return rows, None
    except Exception as exc:
        return [], str(exc)


def _result_summary(rows: List[Dict], max_rows: int = 10) -> str:
    if not rows:
        return "No rows returned."
    import pandas as pd
    return pd.DataFrame(rows).head(max_rows).to_string(index=False)


def _heuristic_chart(rows: List[Dict], question: str) -> Dict[str, Any]:
    """Fast deterministic fallback chart config."""
    if not rows:
        return {"chart_type": "bar", "x_key": "label", "y_key": "value",
                "x_label": "Category", "y_label": "Value", "color": "#06b6d4", "title": ""}
    keys = [k for k in rows[0].keys()]
    x_key = keys[0] if keys else "label"
    y_key = keys[1] if len(keys) > 1 else x_key
    q_lower = question.lower()
    chart_type = "line" if any(w in q_lower for w in ("trend", "over time", "month", "week", "year")) else "bar"
    return {
        "chart_type": chart_type,
        "x_key": x_key, "y_key": y_key,
        "x_label": x_key.replace("_", " ").title(),
        "y_label": y_key.replace("_", " ").title(),
        "color": "#06b6d4",
        "title": question[:50],
    }


def _generate_chart_config(rows: List[Dict], question: str) -> Dict[str, Any]:
    """Try LLM chart config; fall back to heuristic on failure."""
    if not rows:
        return _heuristic_chart(rows, question)
    import pandas as pd
    sample = json.dumps(rows[:5], default=str, indent=2)
    columns = ", ".join(rows[0].keys())
    try:
        raw = call_gemini(
            _NLQ_VIZ_PROMPT.format(question=question, columns=columns, sample_data=sample),
            max_tokens=300,
        )
        return extract_json(raw)
    except Exception as exc:
        logger.debug("chat viz LLM failed, using heuristic: %s", exc)
        return _heuristic_chart(rows, question)


def _get_owned_dataset(dataset_id: str, user_id: str, db: Session) -> Dataset:
    ds = db.query(Dataset).filter(
        Dataset.id == dataset_id, Dataset.user_id == user_id
    ).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if not ds.table_name or not ds.schema_json:
        raise HTTPException(status_code=400, detail="Dataset has not been fully processed yet.")
    return ds


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ChatQueryRequest(BaseModel):
    question: str
    dataset_id: str


class ChatQueryResponse(BaseModel):
    question: str
    answer: str
    sql_used: str
    chart_config: Dict[str, Any]
    row_count: int
    disclaimer: str = "⚠️ AI-generated. Verify before acting."


class SuggestionsResponse(BaseModel):
    dataset_id: str
    suggestions: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=ChatQueryResponse,
    summary="Natural language question → SQL → narrative answer + chart config.",
)
def chat_query(
    body: ChatQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatQueryResponse:
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    ds = _get_owned_dataset(body.dataset_id, current_user.id, db)
    schema_info = _schema_preview_to_info(ds.schema_json)
    sample_rows = _sample_rows_text(ds.schema_json)

    # ── 1. Generate SQL ────────────────────────────────────────────────
    sql_prompt = _NLQ_SQL_PROMPT.format(
        table_name=ds.table_name,
        columns_with_types=schema_info["columns_with_types"],
        sample_rows=sample_rows,
        question=body.question,
    )

    try:
        raw_sql = call_gemini(sql_prompt, max_tokens=400).strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM unavailable: {exc}")

    # Strip accidental markdown fences
    raw_sql = re.sub(r"^```(?:sql)?\s*", "", raw_sql, flags=re.IGNORECASE)
    raw_sql = re.sub(r"\s*```$", "", raw_sql).strip()

    # ── 2. Validate SQL ────────────────────────────────────────────────
    valid, reason = validate_sql(raw_sql)
    if not valid:
        raise HTTPException(
            status_code=400,
            detail=f"Generated SQL failed safety validation: {reason}",
        )

    # ── 3. Execute ─────────────────────────────────────────────────────
    rows, exec_error = _execute_sql(raw_sql)
    if exec_error:
        raise HTTPException(
            status_code=422,
            detail=f"SQL executed but returned an error: {exec_error}",
        )

    # ── 4. Generate narrative ──────────────────────────────────────────
    summary = _result_summary(rows)
    narrative_prompt = _NLQ_NARRATIVE_PROMPT.format(
        question=body.question,
        sql=raw_sql,
        result_summary=summary,
    )
    try:
        answer = call_gemini(narrative_prompt, max_tokens=300).strip()
    except Exception as exc:
        logger.warning("Narrative LLM call failed: %s", exc)
        answer = f"Query returned {len(rows)} row(s). {summary[:300]}"

    # ── 5. Chart config ────────────────────────────────────────────────
    chart_config = _generate_chart_config(rows, body.question)

    return ChatQueryResponse(
        question=body.question,
        answer=answer,
        sql_used=raw_sql,
        chart_config=chart_config,
        row_count=len(rows),
    )


@router.get(
    "/suggestions",
    response_model=SuggestionsResponse,
    summary="Return 3 pre-generated starter questions based on the dataset schema.",
)
def get_suggestions(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuggestionsResponse:
    ds = _get_owned_dataset(dataset_id, current_user.id, db)
    schema_info = _schema_preview_to_info(ds.schema_json)
    sample_rows = _sample_rows_text(ds.schema_json)

    try:
        raw = call_gemini(
            _SUGGESTIONS_PROMPT.format(
                table_name=ds.table_name,
                columns_with_types=schema_info["columns_with_types"],
                sample_rows=sample_rows,
            ),
            max_tokens=300,
        )
        # Gemini may wrap it in prose — extract the JSON array
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            raise ValueError("No JSON array in response")
        suggestions: List[str] = json.loads(raw[start : end + 1])
        if not isinstance(suggestions, list):
            raise ValueError("Parsed value is not a list")
        suggestions = [str(s) for s in suggestions[:3]]
    except Exception as exc:
        logger.warning("Suggestions LLM call failed: %s", exc)
        # Deterministic fallback based on schema
        cols = schema_info["metric_columns"]
        dims = schema_info["dimension_columns"]
        m = cols[0] if cols else "revenue"
        d = dims[0] if dims else "category"
        suggestions = [
            f"What is the total {m} over time?",
            f"Which {d} has the highest {m}?",
            f"Show me the top 10 rows by {m}.",
        ]

    return SuggestionsResponse(dataset_id=dataset_id, suggestions=suggestions)
