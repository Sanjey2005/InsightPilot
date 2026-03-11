"""Full pipeline trace with the fixed deterministic SQL builder"""
import sys
sys.path.append(r'c:\Users\acer\Desktop\InsightPilot\backend')

import pandas as pd
from sqlalchemy import create_engine, text
from agents.schema_agent import _heuristic_classify_columns, _build_hypotheses
from agents.sql_agent import _build_deterministic_sql
from agents.insight_agent import _detect_anomalies, _MIN_ANOMALY_POINTS

CSV = r'c:\Users\acer\Desktop\InsightPilot\insightpilot_demo_v3.csv'
DB  = r'c:\Users\acer\Desktop\InsightPilot\backend\insightpilot.db'

df = pd.read_csv(CSV)
schema = _heuristic_classify_columns(df)
hyps = _build_hypotheses(schema, 'test')

print(f"Testing deterministic SQL for each hypothesis type:")
for h in hyps:
    sql = _build_deterministic_sql(h, schema, 'test_table')
    print(f"\n  {h['type']:22} → {sql[:90]}...")

print("\n\n--- Anomaly simulation with monthly aggregation ---")
anomaly_hyps = [h for h in hyps if h['type'] == 'anomaly']
for ah in anomaly_hyps:
    kpi_col = ah['kpi_column']
    date_col = ah['date_column']
    # Simulate the aggregated monthly data the new SQL returns
    monthly = df.groupby('date')[kpi_col].sum().reset_index()
    monthly.columns = ['period', kpi_col]
    data = monthly.to_dict('records')
    print(f"\nAnomaly/{kpi_col}: {len(data)} monthly aggregated points")
    anomalies = _detect_anomalies(data, kpi_col)
    print(f"  Anomalies (z>2): {len(anomalies)}")
    for a in anomalies:
        print(f"    period={a['period']}  {kpi_col}={a[kpi_col]:,}  z={a['__zscore']}")
