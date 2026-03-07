import csv
import sqlite3
import os
import sys

DB_PATH = "/app/brain/04_Output/real_estate.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            import_batch_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def import_csv(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    conn = init_db()
    cursor = conn.cursor()

    # Record batch
    cursor.execute("INSERT INTO import_batches (filename) VALUES (?)", (os.path.basename(file_path),))
    batch_id = cursor.lastrowid

    print(f"ingesting {file_path}...")
    
    # MLIT CSV is usually CP932 (Shift-JIS)
    try:
        with open(file_path, newline='', encoding='cp932') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0
            for row in reader:
                # Column names from MLIT CSV (Adjust based on actual header)
                # Typical headers: 「種類」「地域」「市区町村コード」「都道府県名」「市区町村名」「地区名」...「取引価格（総額）」
                try:
                    cursor.execute("""
                        INSERT INTO transactions (
                            region, municipality, district, trade_price, price_per_unit, 
                            area, floor_plan, building_year, structure, trade_period, import_batch_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('都道府県名'),
                        row.get('市区町村名'),
                        row.get('地区名'),
                        row.get('取引価格（総額）'),
                        row.get('坪単価'),
                        row.get('面積（㎡）'),
                        row.get('間取り'),
                        row.get('建築年'),
                        row.get('構造'),
                        row.get('取引時点'),
                        batch_id
                    ))
                    count += 1
                except Exception as e:
                    print(f"⚠️ Skip row due to error: {e}")
            
            conn.commit()
            print(f"✅ Imported {count} rows.")
    except UnicodeDecodeError:
        print("❌ Encoding error. Please ensure the CSV is Shift-JIS.")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 data_importer.py <path_to_csv>")
    else:
        import_csv(sys.argv[1])
