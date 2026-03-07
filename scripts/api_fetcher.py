import requests
import sqlite3
import os
import time

API_KEY = os.getenv("MLIT_API_KEY")
DB_PATH = "/app/brain/04_Output/real_estate.db"
BASE_URL = "https://www.reinfolib.mlit.go.jp/api/v1/property/price"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            region TEXT,
            municipality TEXT,
            district TEXT,
            trade_price INTEGER,
            price_per_unit INTEGER,
            area REAL,
            floor_plan TEXT,
            building_year TEXT,
            structure TEXT,
            trade_period TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def fetch_and_save(year, quarter, pref_code):
    if not API_KEY:
        print("❌ MLIT_API_KEY is not set in environment.")
        return

    headers = {"Ocp-Apim-Subscription-Key": API_KEY}
    params = {
        "year": year,
        "quarter": quarter,
        "prefCode": pref_code
    }

    try:
        response = requests.get(BASE_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        conn = init_db()
        cursor = conn.cursor()
        
        count = 0
        for item in data.get("data", []):
            trade_id = item.get('id') or f"{item.get('municipalityCode')}_{item.get('tradePeriod')}_{count}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO transactions (
                    id, region, municipality, district, trade_price, 
                    price_per_unit, area, floor_plan, building_year, structure, trade_period
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                item.get('prefName'),
                item.get('municipalityName'),
                item.get('districtName'),
                item.get('tradePrice'),
                item.get('pricePerUnit'),
                item.get('area'),
                item.get('floorPlan'),
                item.get('buildingYear'),
                item.get('structure'),
                item.get('tradePeriod')
            ))
            count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Successfully fetched and saved {count} records for {year} Q{quarter}.")
        
    except Exception as e:
        print(f"❌ Error during API fetch: {e}")

if __name__ == "__main__":
    # Example: Tokyo (prefCode: 13), 2023 Q4
    import sys
    year = sys.argv[1] if len(sys.argv) > 1 else "2023"
    quarter = sys.argv[2] if len(sys.argv) > 2 else "4"
    pref = sys.argv[3] if len(sys.argv) > 3 else "13"
    fetch_and_save(year, quarter, pref)
