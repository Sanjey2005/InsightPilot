import requests
import time

base_url = "http://localhost:8000"
file_path = "c:/Users/acer/Desktop/InsightPilot/sample_ecommerce.csv"

print("Uploading...")
res = requests.post(f"{base_url}/datasets/upload", files={"file": open(file_path, "rb")})
dataset_id = res.json()["id"]
print("Dataset ID:", dataset_id)

print("Running...")
res = requests.post(f"{base_url}/runs", json={"dataset_id": dataset_id})
run_id = res.json()["id"]

while True:
    time.sleep(2)
    res = requests.get(f"{base_url}/runs/{run_id}")
    status = res.json()["status"]
    print("Status:", status)
    if status in ["completed", "failed"]:
        break

res = requests.get(f"{base_url}/runs/{run_id}/insights")
insights = res.json()
print("Insights count:", len(insights))
if len(insights) > 0:
    for i in insights:
        print("Insight:", i)

res = requests.get(f"{base_url}/runs/{run_id}/kpis")
kpis = res.json()
print("KPIs count:", len(kpis))
if len(kpis) > 0:
    print("First KPI:", kpis[0])
