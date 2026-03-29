"""
国土数値情報 L01（地価公示）データを取得・集計してPostgreSQLに保存するスクリプト
APIキー不要 / 無料 / 国交省公式データ (2024年度版)
"""
import os, sys, json, zipfile, io, re
from collections import defaultdict
from urllib.request import urlopen
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

L01_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/L01/L01-24/L01-24_GML.zip"
GEOJSON_NAME = "L01-24_GML/L01-24.geojson"
CACHE_PATH = "/app/data/land_prices_cache.json"

# 都道府県コード → 都道府県名
PREF_MAP = {
    "01":"北海道","02":"青森県","03":"岩手県","04":"宮城県","05":"秋田県",
    "06":"山形県","07":"福島県","08":"茨城県","09":"栃木県","10":"群馬県",
    "11":"埼玉県","12":"千葉県","13":"東京都","14":"神奈川県","15":"新潟県",
    "16":"富山県","17":"石川県","18":"福井県","19":"山梨県","20":"長野県",
    "21":"岐阜県","22":"静岡県","23":"愛知県","24":"三重県","25":"滋賀県",
    "26":"京都府","27":"大阪府","28":"兵庫県","29":"奈良県","30":"和歌山県",
    "31":"鳥取県","32":"島根県","33":"岡山県","34":"広島県","35":"山口県",
    "36":"徳島県","37":"香川県","38":"愛媛県","39":"高知県","40":"福岡県",
    "41":"佐賀県","42":"長崎県","43":"熊本県","44":"大分県","45":"宮崎県",
    "46":"鹿児島県","47":"沖縄県",
}

def extract_city(address: str) -> str:
    """住所文字列から市区町村名を抽出"""
    parts = address.strip().split("\u3000")  # 全角スペース
    remainder = parts[-1] if len(parts) >= 2 else address
    m = re.match(r'([^\d\s]+?(?:市|区|郡|町|村)(?:[^\d\s]+?(?:市|区|町|村))?)', remainder)
    return m.group(1) if m else remainder[:6]

def process_geojson(zip_data: bytes) -> dict:
    """GeoJSONを処理して市区町村別集計を返す"""
    print("GeoJSONを解析中...", flush=True)

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        with zf.open(GEOJSON_NAME) as f:
            data = json.loads(f.read().decode("utf-8"))

    agg = defaultdict(lambda: {"prices": [], "rates": [], "samples": []})

    for feat in data.get("features", []):
        p = feat.get("properties", {})
        city_code  = str(p.get("L01_001", ""))[:5]
        pref_code  = city_code[:2]
        prefecture = PREF_MAP.get(pref_code, "")
        address    = p.get("L01_025", "")
        city_name  = extract_city(address)
        land_use   = p.get("L01_028", "住宅")
        price      = p.get("L01_008")
        rate       = p.get("L01_009")
        env_desc   = p.get("L01_047", "")
        nearest_st = p.get("L01_048", "")
        st_dist    = p.get("L01_050")

        if not prefecture or not price:
            continue

        key = (pref_code, prefecture, city_name, land_use)
        agg[key]["prices"].append(price)
        if rate is not None:
            agg[key]["rates"].append(rate)
        if env_desc:
            agg[key]["samples"].append({
                "env": env_desc, "station": nearest_st, "dist_m": st_dist
            })

    result = {}
    for (pref_code, prefecture, city_name, land_use), vals in agg.items():
        prices = vals["prices"]
        rates  = vals["rates"]
        key = f"{prefecture}:{city_name}"
        if key not in result:
            result[key] = {
                "prefecture": prefecture,
                "pref_code": pref_code,
                "city": city_name,
                "by_use": {}
            }
        result[key]["by_use"][land_use] = {
            "avg_price": round(sum(prices) / len(prices)),
            "max_price": max(prices),
            "min_price": min(prices),
            "count":     len(prices),
            "avg_rate":  round(sum(rates) / len(rates), 1) if rates else None,
            "samples":   vals["samples"][:3],
        }

    print(f"集計完了: {len(result)} 市区町村", flush=True)
    return result

def get_city_stats(prefecture: str, city: str, land_use: str = "住宅") -> dict | None:
    """キャッシュからエリアの地価統計を取得（writer_agentから呼び出し用）"""
    if not os.path.exists(CACHE_PATH):
        return None
    with open(CACHE_PATH, encoding="utf-8") as f:
        cache = json.load(f)
    # 部分一致検索
    for key, loc in cache.items():
        if prefecture in loc["prefecture"] and city in loc["city"]:
            return loc["by_use"].get(land_use) or next(iter(loc["by_use"].values()), None)
    return None

async def save_to_db(summary: dict, database_url: str):
    """PostgreSQLに地価データを保存"""
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS land_prices (
            id SERIAL PRIMARY KEY,
            prefecture TEXT NOT NULL,
            pref_code TEXT,
            city TEXT NOT NULL,
            land_use TEXT NOT NULL,
            avg_price_per_sqm INTEGER,
            max_price_per_sqm INTEGER,
            min_price_per_sqm INTEGER,
            sample_count INTEGER,
            avg_change_rate FLOAT,
            sample_features JSONB,
            data_year INTEGER DEFAULT 2024,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(prefecture, city, land_use)
        );
    """)

    inserted = 0
    for key, loc in summary.items():
        for land_use, stats in loc["by_use"].items():
            await conn.execute("""
                INSERT INTO land_prices
                  (prefecture, pref_code, city, land_use,
                   avg_price_per_sqm, max_price_per_sqm, min_price_per_sqm,
                   sample_count, avg_change_rate, sample_features, data_year)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT (prefecture, city, land_use)
                DO UPDATE SET
                  avg_price_per_sqm = EXCLUDED.avg_price_per_sqm,
                  avg_change_rate   = EXCLUDED.avg_change_rate,
                  sample_features   = EXCLUDED.sample_features,
                  updated_at        = NOW();
            """,
            loc["prefecture"], loc["pref_code"], loc["city"], land_use,
            stats["avg_price"], stats["max_price"], stats["min_price"],
            stats["count"], stats["avg_rate"],
            json.dumps(stats["samples"], ensure_ascii=False),
            2024)
            inserted += 1

    await conn.close()
    print(f"DB保存完了: {inserted} レコード", flush=True)

async def main():
    print("=== 国土数値情報 L01 地価公示データ取得開始 ===", flush=True)
    print(f"URL: {L01_URL}", flush=True)

    print("ダウンロード中 (~21MB)...", flush=True)
    with urlopen(L01_URL, timeout=180) as resp:
        zip_data = resp.read()
    print(f"ダウンロード完了: {len(zip_data):,} bytes", flush=True)

    summary = process_geojson(zip_data)

    # JSONキャッシュ保存
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"JSONキャッシュ保存: {CACHE_PATH}", flush=True)

    # DB保存
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        try:
            await save_to_db(summary, db_url)
        except Exception as e:
            print(f"DB保存スキップ（{e}）、JSONキャッシュのみ使用", flush=True)

    print("=== 完了 ===", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
