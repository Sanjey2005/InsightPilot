"""End-to-end test: upload v3 CSV, trigger a run, poll until complete, show results."""
import requests, time, json

BASE = "http://localhost:8000"
HDR  = {"Authorization": "Bearer dev"}
CSV  = r"c:\Users\acer\Desktop\InsightPilot\insightpilot_demo_v3.csv"

# 1. Upload
print("Uploading CSV...")
with open(CSV, "rb") as f:
    r = requests.post(f"{BASE}/datasets/upload", files={"file": ("demo_v3.csv", f, "text/csv")}, headers=HDR)
print(f"  Upload: {r.status_code}")
if r.status_code not in (200, 201):
    print(r.text)
    exit(1)
ds = r.json()
dataset_id = ds["id"]
print(f"  Dataset ID: {dataset_id}")
print(f"  Table: {ds.get('table_name')}")

# 2. Trigger run
print("\nTriggering run...")
r = requests.post(f"{BASE}/runs/", json={"dataset_id": dataset_id}, headers={**HDR, "Content-Type": "application/json"})
print(f"  Trigger: {r.status_code}")
if r.status_code not in (200, 202):
    print(r.text)
    exit(1)
run = r.json()
run_id = run["id"]
print(f"  Run ID: {run_id}")

# 3. Poll
print("\nPolling...")
for attempt in range(60):
    time.sleep(3)
    r = requests.get(f"{BASE}/runs/{run_id}", headers=HDR)
    data = r.json()
    status = data["status"]
    logs = data.get("agent_logs", [])
    agents_done = [l["agent"] for l in logs]
    print(f"  [{attempt*3}s] status={status}  agents_done={agents_done}")
    if status in ("completed", "failed"):
        break

# 4. Results
print(f"\n{'='*60}")
print(f"Run status: {data['status']}")
print(f"Insights: {len(data.get('insights', []))}")
print(f"KPIs: {len(data.get('kpis', []))}")

type_counts = {}
for i in data.get("insights", []):
    t = i["type"]
    type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  [{t:10s}] {i['title'][:70]}")
print(f"\nType breakdown: {type_counts}")

for k in data.get("kpis", []):
    print(f"  KPI: {k['name']:25s} = {k['value']}  delta={k.get('delta_pct')}")

# Check for errors
for l in data.get("agent_logs", []):
    if l.get("error"):
        print(f"\n  ERROR in {l['agent']}: {l['error']}")
