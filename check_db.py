import sqlite3, json
conn = sqlite3.connect(r'c:\Users\acer\Desktop\InsightPilot\backend\insightpilot.db')
c = conn.cursor()

c.execute('SELECT id FROM runs ORDER BY created_at DESC LIMIT 1')
run_id = c.fetchone()[0]

# ALL insights
c.execute('SELECT type, title, severity FROM insights WHERE run_id=?', (run_id,))
rows = c.fetchall()
print(f"ALL insights for latest run ({len(rows)}):")
type_counts = {}
for r in rows:
    t = r[0]
    type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  type={t:10s}  severity={r[2]:6s}  title={r[1]}")
print(f"\nType breakdown: {type_counts}")

# ALL KPIs
c.execute('SELECT name, value, delta_pct, period_label FROM kpis WHERE run_id=?', (run_id,))
kpis = c.fetchall()
print(f"\nALL KPIs ({len(kpis)}):")
for k in kpis:
    print(f"  name={k[0]:25s}  value={k[1]}  delta={k[2]}  period={k[3]}")

# Check the API response format
print("\n--- Checking what the API returns ---")
import requests
res = requests.get(f'http://localhost:8000/runs/{run_id}', headers={'Authorization': 'Bearer dev'})
data = res.json()
print(f"API status: {res.status_code}")
print(f"API kpis count: {len(data.get('kpis', []))}")
print(f"API insights count: {len(data.get('insights', []))}")
for i in data.get('insights', []):
    print(f"  [{i['type']:10s}] {i['title'][:60]}")
for k in data.get('kpis', []):
    print(f"  KPI: {k['name']:25s} = {k['value']}")
