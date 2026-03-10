"""
Visualization Agent.

For each insight from the insight agent, selects a Recharts-compatible chart
type and generates an axis / series configuration. Falls back to a deterministic
heuristic if the LLM call fails.
"""
import json
import logging
from typing import Any, Dict, List

from agents.utils import Timer, call_gemini, extract_json, make_log
from core.config import settings

logger = logging.getLogger(__name__)

# Brand colours (matches frontend theme)
_CYAN   = "#06b6d4"
_PURPLE = "#a855f7"

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_VIZ_PROMPT = """\
You are a data-visualization expert. Given one business insight, produce a \
Recharts-compatible chart configuration.

Insight type : {insight_type}
Insight title: {title}
KPI column   : {kpi_col}
Data sample  :
{data_sample}

Choose ONE chart_type from: line | bar | area | scatter

Guidelines:
- trend / mom_trend / wow_trend  → line or area  (x = time period)
- segment_breakdown              → bar            (x = dimension value)
- anomaly                        → scatter        (x = time column, highlight outliers)

Respond ONLY with a valid JSON object, no explanation:
{{
  "chart_type"  : "line|bar|area|scatter",
  "x_key"       : "<column name for x-axis>",
  "y_key"       : "<column name for y-axis>",
  "x_label"     : "<human-readable x-axis label>",
  "y_label"     : "<human-readable y-axis label>",
  "color"       : "{color_hint}",
  "title"       : "<short chart title (max 8 words)>"
}}"""


# ---------------------------------------------------------------------------
# Heuristic fallback
# ---------------------------------------------------------------------------

def _heuristic_config(insight_type: str, data: List[Dict], kpi_col: str) -> Dict:
    if not data:
        return {
            "chart_type": "bar", "x_key": "label", "y_key": kpi_col or "value",
            "x_label": "Category", "y_label": kpi_col or "Value",
            "color": _CYAN, "title": "Chart",
        }

    keys = list(data[0].keys())
    # Drop internal annotation keys
    keys = [k for k in keys if not k.startswith("__")]

    x_key = keys[0] if keys else "label"
    y_key = kpi_col if kpi_col in data[0] else (keys[1] if len(keys) > 1 else x_key)

    type_map = {
        "trend": "line", "segment": "bar", "anomaly": "scatter", "kpi": "bar",
    }
    return {
        "chart_type": type_map.get(insight_type, "bar"),
        "x_key": x_key,
        "y_key": y_key,
        "x_label": x_key.replace("_", " ").title(),
        "y_label": y_key.replace("_", " ").title(),
        "color": _PURPLE if insight_type == "anomaly" else _CYAN,
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
            # Remove internal keys before sending to LLM
            clean_data = [{k: v for k, v in row.items() if not k.startswith("__")}
                          for row in data[:5]]
            kpi_col: str = ins.get("kpi_column", "")
            insight_type: str = ins.get("type", "trend")
            color_hint = _PURPLE if insight_type == "anomaly" else _CYAN

            try:
                prompt = _VIZ_PROMPT.format(
                    insight_type=insight_type,
                    title=ins["title"],
                    kpi_col=kpi_col,
                    data_sample=json.dumps(clean_data, default=str, indent=2),
                    color_hint=color_hint,
                )
                chart_config = extract_json(call_gemini(prompt, max_tokens=400))
            except Exception as exc:
                logger.warning("viz_agent LLM failed for '%s': %s", ins["title"], exc)
                chart_config = _heuristic_config(insight_type, data, kpi_col)

            enriched.append({**ins, "chart_config": chart_config})

    log = make_log(
        "viz_agent", "completed", t.elapsed_ms,
        details={"charts_generated": len(enriched)},
    )
    return {
        "insights": enriched,
        "agent_logs": [log],
        "errors": [],
    }
