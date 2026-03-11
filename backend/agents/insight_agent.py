"""
Insight Discovery Agent.

Fixed playbook (executed against SQL agent results):
  1. MoM trends    — month-over-month delta for each metric column.
  2. WoW trends    — week-over-week delta for each metric column.
  3. Segment       — top-3 dimension breakdowns per metric column.
  4. Anomaly       — z-score > 2 detection on metric time-series.
                     Requires >= 10 data points; z-score 1.5-2 uses hedged language.

Each insight gets a narrative from Gemini 1.5 Flash referencing only actual result numbers.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from agents.utils import Timer, call_gemini, make_log
from core.config import settings

logger = logging.getLogger(__name__)

# Minimum data-points in a time series before anomaly detection runs
_MIN_ANOMALY_POINTS = 6

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_NARRATIVE_PROMPT = """\
You are a concise business analyst. Write a 2–3 sentence insight narrative.

Insight type : {insight_type}
Description  : {description}
Data summary :
{data_summary}

Rules:
- Reference specific numbers from the data summary.
- Use plain business language (no SQL, no technical jargon).
- For anomalies with |z-score| between 1.5 and 2.0: use hedged language \
("appears to show", "may indicate").
- For anomalies with |z-score| > 2.0: use confident language.
- Maximum 3 sentences. No headers, no bullet points.
- Do NOT add any disclaimer — one will be appended automatically."""


# ---------------------------------------------------------------------------
# Z-score helpers (no scipy dependency)
# ---------------------------------------------------------------------------

def _zscore(values: List[float]) -> List[float]:
    arr = np.array(values, dtype=float)
    mean = np.nanmean(arr)
    std = np.nanstd(arr)
    if std == 0:
        return [0.0] * len(arr)
    return ((arr - mean) / std).tolist()


def _detect_anomalies(data: List[Dict], kpi_col: str, threshold: float = 2.0) -> List[Dict]:
    """Return rows whose kpi_col value has |z-score| > threshold, annotated with __zscore."""
    if not data or kpi_col not in data[0]:
        return []
    values = []
    for row in data:
        try:
            values.append(float(row[kpi_col]))
        except (TypeError, ValueError):
            values.append(float("nan"))

    scores = _zscore(values)
    return [
        {**row, "__zscore": round(z, 3)}
        for row, z in zip(data, scores)
        if abs(z) > threshold
    ]


def _severity(z_abs: float) -> str:
    if z_abs >= 3.0:
        return "high"
    if z_abs >= 2.0:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Data summary helpers
# ---------------------------------------------------------------------------

def _df_summary(df: pd.DataFrame, max_rows: int = 12) -> str:
    return df.head(max_rows).to_string(index=False)


def _trend_summary(data: List[Dict], kpi_col: str) -> str:
    df = pd.DataFrame(data)
    if df.empty:
        return "No data."
    txt = _df_summary(df)
    if kpi_col in df.columns and len(df) >= 2:
        vals = pd.to_numeric(df[kpi_col], errors="coerce").dropna().tolist()
        if len(vals) >= 2:
            delta = vals[-1] - vals[-2]
            pct = delta / vals[-2] * 100 if vals[-2] else 0
            txt += f"\nLatest period delta: {delta:+.2f} ({pct:+.1f}%)"
    return txt


def _segment_summary(data: List[Dict]) -> str:
    df = pd.DataFrame(data).head(5)
    return _df_summary(df)


def _anomaly_summary(anomalies: List[Dict], kpi_col: str) -> str:
    if not anomalies:
        return "No anomalies detected."
    df = pd.DataFrame(anomalies).head(5)
    max_z = max(abs(a["__zscore"]) for a in anomalies)
    return f"Found {len(anomalies)} anomalous point(s). Max |z-score|={max_z:.2f}.\n" + _df_summary(df)


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------

def _generate_narrative(insight_type: str, description: str, data_summary: str) -> str:
    return call_gemini(
        _NARRATIVE_PROMPT.format(
            insight_type=insight_type,
            description=description,
            data_summary=data_summary,
        ),
        max_tokens=300,
    ).strip()


# ---------------------------------------------------------------------------
# MoM / WoW delta severity
# ---------------------------------------------------------------------------

def _trend_severity(data: List[Dict], kpi_col: str) -> str:
    df = pd.DataFrame(data)
    if kpi_col not in df.columns or len(df) < 2:
        return "low"
    vals = pd.to_numeric(df[kpi_col], errors="coerce").dropna().tolist()
    if len(vals) < 2 or vals[-2] == 0:
        return "low"
    pct = abs((vals[-1] - vals[-2]) / vals[-2] * 100)
    return "high" if pct > 20 else ("medium" if pct > 5 else "low")


_TYPE_MAP = {
    "mom_trend": "trend",
    "wow_trend": "trend",
    "segment_breakdown": "segment",
    "anomaly": "anomaly",
}

_LABEL_MAP = {
    "mom_trend": "MoM Trend",
    "wow_trend": "WoW Trend",
    "segment_breakdown": "Segment",
    "anomaly": "Anomaly",
}


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_insight_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    sql_results: List[Dict] = state.get("sql_results", [])
    insights: List[Dict] = []

    with Timer() as t:
        for result in sql_results:
            data: List[Dict] = result.get("data", [])
            hyp: Dict = result.get("hypothesis", {})
            sql: str = result.get("sql", "")
            hyp_type: str = hyp.get("type", "")
            kpi_col: str = hyp.get("kpi_column", "")

            if not data:
                continue

            # ── Anomaly detection ──────────────────────────────────────
            if hyp_type == "anomaly":
                if len(data) < _MIN_ANOMALY_POINTS:
                    continue  # too few points — skip per PRD guidance
                anomalies = _detect_anomalies(data, kpi_col)
                if not anomalies:
                    continue  # no anomalies found — nothing to surface
                max_z = max(abs(a["__zscore"]) for a in anomalies)
                severity = _severity(max_z)
                data_for_insight = anomalies
                summary = _anomaly_summary(anomalies, kpi_col)

            # ── Trend insights ─────────────────────────────────────────
            elif hyp_type in ("mom_trend", "wow_trend"):
                severity = _trend_severity(data, kpi_col)
                data_for_insight = data
                summary = _trend_summary(data, kpi_col)

            # ── Segment breakdown ──────────────────────────────────────
            elif hyp_type == "segment_breakdown":
                severity = "medium"
                data_for_insight = data[:10]
                summary = _segment_summary(data)

            else:
                continue

            # ── Narrative ──────────────────────────────────────────────
            try:
                narrative = _generate_narrative(
                    _TYPE_MAP.get(hyp_type, "trend"), hyp["description"], summary
                )
            except Exception as exc:
                logger.warning("Narrative failed for %s: %s", hyp.get("id"), exc)
                narrative = f"Analysis of {kpi_col}: {summary[:300]}"

            title = f"{_LABEL_MAP.get(hyp_type, 'Insight')}: {hyp['description']}"

            insights.append({
                "id": str(uuid.uuid4()),
                "type": _TYPE_MAP.get(hyp_type, "trend"),
                "title": title,
                "narrative": narrative,
                "sql_used": sql,
                "data": data_for_insight[:50],   # cap stored rows
                "kpi_column": kpi_col,
                "severity": severity,
                "chart_config": None,            # filled by viz_agent
            })

    log = make_log(
        "insight_agent", "completed", t.elapsed_ms,
        details={"insights_generated": len(insights)},
    )
    # Hard-cap at 8 insights to cover all types with good variety
    return {
        "insights": insights[:8],
        "agent_logs": [log],
        "errors": [],
    }
