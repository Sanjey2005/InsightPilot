"""
Full pipeline simulation against the v3 dataset to trace exactly where anomalies get dropped.
"""
import sys
sys.path.append(r'c:\Users\acer\Desktop\InsightPilot\backend')

import pandas as pd
from agents.schema_agent import _heuristic_classify_columns, _build_hypotheses
from agents.insight_agent import _detect_anomalies, _zscore, _MIN_ANOMALY_POINTS

df = pd.read_csv(r'c:\Users\acer\Desktop\InsightPilot\insightpilot_demo_v3.csv')
print(f"CSV loaded: {len(df)} rows, columns: {list(df.columns)}")

# Step 1: Schema
schema = _heuristic_classify_columns(df)
print(f"\nSchema:")
print(f"  Date col: {schema['date_column']}")
print(f"  Metrics:  {schema['metric_columns']}")
print(f"  Dims:     {schema['dimension_columns']}")

# Step 2: Hypotheses
hyps = _build_hypotheses(schema, 'test')
print(f"\nHypotheses ({len(hyps)}):")
for h in hyps:
    print(f"  {h['type']:22} kpi={h['kpi_column']}  dim={h.get('dimension_column')}")

# Step 3: Simulate what SQL anomaly query returns
# The SQL: SELECT date, revenue FROM table WHERE revenue IS NOT NULL AND date IS NOT NULL ORDER BY date
print("\n--- Anomaly trace ---")
anomaly_hyps = [h for h in hyps if h['type'] == 'anomaly']
for ah in anomaly_hyps:
    kpi_col = ah['kpi_column']
    date_col = ah['date_column']
    # SQL groups by date already for MoM, but the anomaly SQL returns raw rows
    data = df[[date_col, kpi_col]].dropna().rename(columns={kpi_col: kpi_col}).to_dict('records')
    data = [{date_col: str(r[date_col]), kpi_col: r[kpi_col]} for r in data]
    print(f"\nHypothesis: anomaly/{kpi_col} — {len(data)} rows")
    print(f"  Min required: {_MIN_ANOMALY_POINTS}")
    if len(data) < _MIN_ANOMALY_POINTS:
        print(f"  SKIP: too few rows")
        continue
    anomalies = _detect_anomalies(data, kpi_col)
    print(f"  Anomalies detected: {len(anomalies)}")
    for a in anomalies:
        print(f"    {a[date_col]}: {a[kpi_col]:,} (z={a['__zscore']})")
