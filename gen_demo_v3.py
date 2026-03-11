"""
Generate a crystal-clear demo dataset that will provoke ALL insight types:
- MoM/WoW Trends: steady upward slope in revenue
- Anomaly: Feb 2024 revenue collapses to ~15% of normal (z-score >> 2)
- Segment: Enterprise revenue is 4x higher than SMB consistently
- KPIs: revenue, orders, avg_order_value are computable
"""
import csv

rows = []
# 24 monthly rows – one row per channel × month
months = [
    "2023-01-01","2023-02-01","2023-03-01","2023-04-01",
    "2023-05-01","2023-06-01","2023-07-01","2023-08-01",
    "2023-09-01","2023-10-01","2023-11-01","2023-12-01",
    "2024-01-01","2024-02-01","2024-03-01","2024-04-01",
    "2024-05-01","2024-06-01","2024-07-01","2024-08-01",
    "2024-09-01","2024-10-01","2024-11-01","2024-12-01",
]

base_enterprise = 90000
base_smb = 22000
# Enterprise grows 2% per month, SMB grows 1%
for idx, month in enumerate(months):
    # ── ANOMALY: Feb 2024 (index 13) revenue crashes ──
    anomaly = (idx == 13)

    e_rev = int(base_enterprise * (1.02 ** idx))
    s_rev = int(base_smb * (1.01 ** idx))

    if anomaly:
        e_rev = int(e_rev * 0.14)   # 86% drop → z-score >> 3
        s_rev = int(s_rev * 0.18)

    e_orders = max(1, int(e_rev / 1800))
    s_orders = max(1, int(s_rev / 900))

    rows.append({
        "date": month,
        "channel": "Enterprise",
        "revenue": e_rev,
        "orders": e_orders,
        "avg_order_value": round(e_rev / e_orders, 2) if e_orders else 0,
        "churn_rate": round(0.02 + idx * 0.0005 + (0.12 if anomaly else 0), 4),
    })
    rows.append({
        "date": month,
        "channel": "SMB",
        "revenue": s_rev,
        "orders": s_orders,
        "avg_order_value": round(s_rev / s_orders, 2) if s_orders else 0,
        "churn_rate": round(0.05 + idx * 0.0003 + (0.06 if anomaly else 0), 4),
    })

out = r"c:\Users\acer\Desktop\InsightPilot\insightpilot_demo_v3.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["date","channel","revenue","orders","avg_order_value","churn_rate"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Written {len(rows)} rows to {out}")
print("Date range: Jan 2023 – Dec 2024 (24 months × 2 channels = 48 rows)")
print("Anomaly: Feb 2024 revenue crashes ~85%")
print("Segment: Enterprise revenue ~4x SMB throughout")

# Quick sanity – verify z-score of Feb 2024 enterprise revenue
import numpy as np
ent_revs = [r["revenue"] for r in rows if r["channel"] == "Enterprise"]
mean = np.mean(ent_revs)
std  = np.std(ent_revs)
feb_rev = [r["revenue"] for r in rows if r["channel"] == "Enterprise" and r["date"] == "2024-02-01"][0]
z = (feb_rev - mean) / std
print(f"\nEnterprise Feb 2024 revenue: {feb_rev:,}  (mean={mean:,.0f}, std={std:,.0f})")
print(f"Z-score: {z:.2f}  → {'ANOMALY DETECTED' if abs(z) > 2 else 'not anomalous'}")
