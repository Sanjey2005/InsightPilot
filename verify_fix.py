import sys
sys.path.append(r'c:\Users\acer\Desktop\InsightPilot\backend')

import pandas as pd
from agents.schema_agent import _heuristic_classify_columns, _build_hypotheses

df = pd.read_csv(r'c:\Users\acer\Desktop\InsightPilot\insightpilot_demo_dataset_v2.csv')
schema = _heuristic_classify_columns(df)
hyps = _build_hypotheses(schema, 'test')

print(f"Total rows in CSV: {len(df)}")
print(f"Date column: {schema['date_column']}")
print(f"Metric columns: {schema['metric_columns']}")
print(f"Dimension columns: {schema['dimension_columns']}")
print(f"\nHypotheses ({len(hyps)} total):")
counts = {}
for h in hyps:
    t = h['type']
    counts[t] = counts.get(t, 0) + 1
    print(f"  {h['id']}: {t:22s} kpi={h['kpi_column']}  dim={h.get('dimension_column')}")

print(f"\nType breakdown: {counts}")

expected = {'mom_trend', 'segment_breakdown', 'anomaly', 'wow_trend'}
found = set(counts.keys())
missing = expected - found
if missing:
    print(f"\nWARNING: Missing types: {missing}")
else:
    print(f"\nAll 4 insight types represented in hypotheses!")
