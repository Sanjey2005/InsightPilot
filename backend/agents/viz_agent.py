"""
Visualization Agent.

Selects a Recharts-compatible chart type and axis configuration for each
insight using a deterministic heuristic. No LLM call is made here —
this saves free-tier quota (previously 1 Groq call per insight).
"""
import logging
from typing import Any, Dict, List

from agents.utils import Timer, make_log

logger = logging.getLogger(__name__)

# Brand colours (matches frontend theme)
_CYAN   = "#06b6d4"
_PURPLE = "#a855f7"


# ---------------------------------------------------------------------------
# Heuristic chart config — covers all insight types without LLM
# ---------------------------------------------------------------------------

def _heuristic_config(insight_type: str, data: List[Dict], kpi_col: str) -> Dict:
    if not data:
        return {
            "chart_type": "bar", "x_key": "label", "y_key": kpi_col or "value",
            "x_label": "Category", "y_label": kpi_col or "Value",
            "color": _CYAN, "title": "Chart",
        }

    keys = list(data[0].keys())
    # Drop internal annotation keys (e.g. __zscore from anomaly detection)
    keys = [k for k in keys if not k.startswith("__")]

    x_key = keys[0] if keys else "label"
    y_key = kpi_col if kpi_col in data[0] else (keys[1] if len(keys) > 1 else x_key)

    type_map = {
        "trend": "line", "segment": "bar", "anomaly": "scatter", "kpi": "bar",
    }
    chart_type = type_map.get(insight_type, "bar")
    color = _PURPLE if insight_type == "anomaly" else _CYAN

    return {
        "chart_type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "x_label": x_key.replace("_", " ").title(),
        "y_label": y_key.replace("_", " ").title(),
        "color": color,
        "title": f"{y_key.replace('_', ' ').title()} by {x_key.replace('_', ' ').title()}",
    }


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------

def run_viz_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    insights: List[Dict] = state.get("insights", [])
    enriched: List[Dict] = []

    with Timer() as t:
        for ins in insights:
            data: List[Dict] = ins.get("data", [])
            kpi_col: str = ins.get("kpi_column", "")
            insight_type: str = ins.get("type", "trend")

            # Pure heuristic — no LLM call, saves free-tier quota
            chart_config = _heuristic_config(insight_type, data, kpi_col)
            enriched.append({**ins, "chart_config": chart_config})

    log = make_log(
        "viz_agent", "completed", t.elapsed_ms,
        details={"charts_generated": len(enriched), "method": "heuristic"},
    )
    return {
        "insights": enriched,
        "agent_logs": [log],
        "errors": [],
    }
