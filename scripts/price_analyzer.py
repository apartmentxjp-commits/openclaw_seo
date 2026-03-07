import sqlite3
import os
import json

DB_PATH = "/app/brain/04_Output/real_estate.db"

def analyze_trends(municipality, district=None):
    if not os.path.exists(DB_PATH):
        return {"error": "Database not found. Please import data first."}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM transactions WHERE municipality = ?"
    params = [municipality]
    if district:
        query += " AND district = ?"
        params.append(district)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if not rows:
        return {"message": f"No data found for {municipality} {district or ''}"}

    # Group by trade_period
    periods = {}
    for row in rows:
        p = row['trade_period']
        if p not in periods:
            periods[p] = []
        try:
            price = int(row['trade_price'])
            periods[p].append(price)
        except:
            continue

    # Calculate average per period
    stats = []
    for p, prices in periods.items():
        avg = sum(prices) / len(prices)
        stats.append({
            "period": p,
            "avg_price": avg,
            "count": len(prices)
        })

    # Sort by period (Simple sort, might need better period parsing for accurate chronology)
    stats.sort(key=lambda x: x['period'], reverse=True)

    analysis = {
        "location": {"municipality": municipality, "district": district},
        "trends": stats,
    }

    if len(stats) >= 2:
        latest = stats[0]['avg_price']
        previous = stats[1]['avg_price']
        diff = ((latest - previous) / previous) * 100
        analysis["summary"] = {
            "comparison": f"{stats[0]['period']} vs {stats[1]['period']}",
            "change_percent": round(diff, 2),
            "trend": "上昇" if diff > 0 else "下落" if diff < 0 else "横ばい",
            "latest_price": round(latest),
            "previous_price": round(previous)
        }
    elif len(stats) == 1:
        analysis["summary"] = {
            "comparison": f"{stats[0]['period']}のみ",
            "change_percent": 0.0,
            "trend": "データ1件のみ",
            "latest_price": round(stats[0]['avg_price']),
            "previous_price": None
        }

    return analysis

if __name__ == "__main__":
    import sys
    mun = sys.argv[1] if len(sys.argv) > 1 else "世田谷区"
    dist = sys.argv[2] if len(sys.argv) > 2 else None
    result = analyze_trends(mun, dist)
    print(json.dumps(result, indent=2, ensure_ascii=False))
