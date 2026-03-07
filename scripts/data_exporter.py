import sqlite3
import json
import os

DB_PATH = "/app/brain/04_Output/real_estate.db"
OUTPUT_BASE = "/app/brain/04_Output/Export"

def export_to_json():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get unique municipalities
    cursor.execute("SELECT DISTINCT region, municipality FROM transactions")
    areas = cursor.fetchall()

    for area in areas:
        region = area['region']
        muni = area['municipality']
        
        # Aggregate data for AI
        cursor.execute("""
            SELECT 
                AVG(trade_price) as avg_price,
                AVG(price_per_unit) as avg_tsubo,
                COUNT(*) as transactions
            FROM transactions 
            WHERE municipality = ?
        """, (muni,))
        stats = cursor.fetchone()

        export_data = {
            "region": region,
            "municipality": muni,
            "statistics": {
                "average_price": round(stats['avg_price'] or 0),
                "tsubo_price": round(stats['avg_tsubo'] or 0),
                "transaction_count": stats['transactions'],
                "last_updated": json.dumps(str(os.popen('date').read().strip()))
            },
            "market_trend": "Stable" # Placeholder for analysis logic
        }

        # Save to JSON
        dir_path = os.path.join(OUTPUT_BASE, region, muni)
        os.makedirs(dir_path, exist_ok=True)
        with open(os.path.join(dir_path, "market_data.json"), "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    conn.close()
    print(f"✅ Data exported for {len(areas)} municipalities.")

if __name__ == "__main__":
    export_to_json()
