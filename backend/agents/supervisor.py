"""
LangGraph supervisor: defines PipelineState and wires the 5-agent DAG.

Flow: schema_agent → sql_agent → insight_agent → viz_agent → END
"""
import operator
from typing import Annotated, Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from agents.schema_agent import run_schema_agent
from agents.sql_agent import run_sql_agent
from agents.insight_agent import run_insight_agent
from agents.viz_agent import run_viz_agent


# ---------------------------------------------------------------------------
# Shared pipeline state
# ---------------------------------------------------------------------------

class PipelineState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────────────
    run_id: str
    dataset_id: str
    user_id: str
    table_name: str

    # ── Schema Agent outputs ──────────────────────────────────────────────
    # Raw LLM classification: {classifications, date_column, metric_columns,
    #                           dimension_columns, kpi_candidates}
    schema_info: Dict[str, Any]
    # Playbook hypotheses built from schema_info
    hypotheses: List[Dict[str, Any]]
    # [{name, column, aggregation}, ...]
    kpi_candidates: List[Dict[str, Any]]

    # ── SQL Agent outputs ─────────────────────────────────────────────────
    # [{hypothesis_id, hypothesis, sql, data, error}, ...]
    sql_results: List[Dict[str, Any]]

    # ── Insight + Viz Agent outputs ───────────────────────────────────────
    # [{id, type, title, narrative, sql_used, data, kpi_column,
    #   severity, chart_config}, ...]
    insights: List[Dict[str, Any]]

    # ── Accumulating fields (operator.add merges lists across nodes) ──────
    agent_logs: Annotated[List[Dict[str, Any]], operator.add]
    errors: Annotated[List[str], operator.add]


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_pipeline() -> Any:
    """Compile and return the LangGraph pipeline. Call once at import time."""
    graph = StateGraph(PipelineState)

    graph.add_node("schema_agent", run_schema_agent)
    graph.add_node("sql_agent", run_sql_agent)
    graph.add_node("insight_agent", run_insight_agent)
    graph.add_node("viz_agent", run_viz_agent)

    graph.set_entry_point("schema_agent")
    graph.add_edge("schema_agent", "sql_agent")
    graph.add_edge("sql_agent", "insight_agent")
    graph.add_edge("insight_agent", "viz_agent")
    graph.add_edge("viz_agent", END)

    return graph.compile()


# Module-level singleton — compiled once on first import
pipeline = build_pipeline()
