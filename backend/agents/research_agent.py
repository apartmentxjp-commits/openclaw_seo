"""
Research Agent: 外部データ → knowledge_base テーブル
  - 日銀政策金利（日銀 XML/JSON API）
  - e-Stat 人口動態（都道府県別人口）
  - 国土交通省 地価公示（land_prices DBから集計）
  週1回スケジュール（scheduler.py から呼び出し）
"""

import os
import json
import urllib.request
import urllib.error
import psycopg2
from datetime import datetime, date
from typing import Any

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _get_pg_conn():
    """同期 psycopg2 接続を返す"""
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")
    return psycopg2.connect(url)


# ─────────────────────────────────────────────
# 1. 日銀政策金利
# ─────────────────────────────────────────────

BOJ_RATE_URL = (
    "https://www.stat-search.boj.or.jp/ssi/mtsearch/directhit.do"
    "?seriesdcode=IR01'MADR'M&storeType=json"
)

# 日銀JSONが取得できない環境用 fallback（最終既知値 2024-03: 0.1%）
BOJ_FALLBACK_RATE = 0.1
BOJ_FALLBACK_DATE = "2024-03"


def fetch_boj_rate() -> dict:
    """
    日銀政策金利を取得する。
    公開JSONが取得できない場合はフォールバック値を使用。
    Returns: {"rate": float, "period": str, "source": str}
    """
    try:
        req = urllib.request.Request(
            BOJ_RATE_URL,
            headers={"User-Agent": "OpenClaw-ResearchAgent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # BOJ JSON 構造: {"result":{"series":[{"obs":[{"period":"2025-03","value":"0.50"},...]}]}}
            obs_list = data["result"]["series"][0]["obs"]
            latest = obs_list[-1]
            rate = float(latest["value"])
            period = latest["period"]
            print(f"[Research] 日銀政策金利取得成功: {period} → {rate}%", flush=True)
            return {"rate": rate, "period": period, "source": "日銀 統計時系列データ"}
    except Exception as e:
        print(f"[Research] 日銀金利取得失敗({e}), フォールバック使用", flush=True)
        return {"rate": BOJ_FALLBACK_RATE, "period": BOJ_FALLBACK_DATE, "source": "日銀（フォールバック）"}


# ─────────────────────────────────────────────
# 2. e-Stat 人口（都道府県別）
# ─────────────────────────────────────────────

ESTAT_APP_ID = os.getenv("ESTAT_APP_ID", "")  # 未設定ならハードコードデータを使用

# 都道府県コード → 名前マッピング（e-Stat 用）
PREF_CODE_MAP = {
    "01": "北海道", "02": "青森県", "03": "岩手県", "04": "宮城県",
    "05": "秋田県", "06": "山形県", "07": "福島県", "08": "茨城県",
    "09": "栃木県", "10": "群馬県", "11": "埼玉県", "12": "千葉県",
    "13": "東京都", "14": "神奈川県", "15": "新潟県", "16": "富山県",
    "17": "石川県", "18": "福井県", "19": "山梨県", "20": "長野県",
    "21": "岐阜県", "22": "静岡県", "23": "愛知県", "24": "三重県",
    "25": "滋賀県", "26": "京都府", "27": "大阪府", "28": "兵庫県",
    "29": "奈良県", "30": "和歌山県", "31": "鳥取県", "32": "島根県",
    "33": "岡山県", "34": "広島県", "35": "山口県", "36": "徳島県",
    "37": "香川県", "38": "愛媛県", "39": "高知県", "40": "福岡県",
    "41": "佐賀県", "42": "長崎県", "43": "熊本県", "44": "大分県",
    "45": "宮崎県", "46": "鹿児島県", "47": "沖縄県",
}

# e-Stat が取得できない場合のフォールバック（2023年推計人口 万人）
PREF_POPULATION_FALLBACK = {
    "北海道": 516, "青森県": 118, "岩手県": 116, "宮城県": 228,
    "秋田県": 92,  "山形県": 102, "福島県": 179, "茨城県": 285,
    "栃木県": 191, "群馬県": 192, "埼玉県": 735, "千葉県": 629,
    "東京都": 1404, "神奈川県": 924, "新潟県": 216, "富山県": 101,
    "石川県": 112, "福井県": 76,  "山梨県": 80,  "長野県": 202,
    "岐阜県": 196, "静岡県": 359, "愛知県": 755, "三重県": 173,
    "滋賀県": 141, "京都府": 255, "大阪府": 879, "兵庫県": 541,
    "奈良県": 131, "和歌山県": 91, "鳥取県": 55, "島根県": 66,
    "岡山県": 188, "広島県": 277, "山口県": 131, "徳島県": 71,
    "香川県": 95,  "愛媛県": 131, "高知県": 68,  "福岡県": 513,
    "佐賀県": 80,  "長崎県": 126, "熊本県": 172, "大分県": 112,
    "宮崎県": 105, "鹿児島県": 158, "沖縄県": 146,
}


def fetch_estat_population() -> dict[str, int]:
    """
    e-Stat API から都道府県別人口を取得する。
    取得失敗時はフォールバック値を返す。
    Returns: {prefecture_name: population_万人}
    """
    if not ESTAT_APP_ID:
        print("[Research] ESTAT_APP_ID 未設定 → フォールバック人口データ使用", flush=True)
        return PREF_POPULATION_FALLBACK.copy()

    # 国勢調査 都道府県別人口 statsDataId
    STATS_DATA_ID = "0003448237"
    url = (
        f"https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
        f"?appId={ESTAT_APP_ID}&statsDataId={STATS_DATA_ID}&metaGetFlg=N&cntGetFlg=N"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-ResearchAgent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
            pop_map = {}
            for item in values:
                area_code = item.get("@area", "")
                pref_code = area_code[:2]
                pref_name = PREF_CODE_MAP.get(pref_code)
                if pref_name:
                    try:
                        pop = int(str(item["$"]).replace(",", "")) // 10000
                        if pref_name not in pop_map:
                            pop_map[pref_name] = pop
                    except (ValueError, KeyError):
                        pass
            print(f"[Research] e-Stat 人口データ取得: {len(pop_map)}都道府県", flush=True)
            return pop_map if pop_map else PREF_POPULATION_FALLBACK.copy()
    except Exception as e:
        print(f"[Research] e-Stat 取得失敗({e}) → フォールバック使用", flush=True)
        return PREF_POPULATION_FALLBACK.copy()


# ─────────────────────────────────────────────
# 3. land_prices DB から都道府県別地価集計
# ─────────────────────────────────────────────

def fetch_land_price_summary() -> list[dict]:
    """
    land_prices テーブルから都道府県別 住宅地価 集計を取得。
    Returns: [{"prefecture": str, "avg": float, "max": float, "count": int}, ...]
    """
    try:
        conn = _get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                prefecture,
                ROUND(AVG(avg_price_per_sqm)::numeric, 0)  AS avg_price,
                ROUND(MAX(max_price_per_sqm)::numeric, 0)  AS max_price,
                SUM(sample_count)                          AS cnt
            FROM land_prices
            WHERE land_use = '住宅'
              AND avg_price_per_sqm IS NOT NULL
            GROUP BY prefecture
            ORDER BY avg_price DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        result = [
            {"prefecture": r[0], "avg": float(r[1]), "max": float(r[2]), "count": int(r[3])}
            for r in rows
        ]
        print(f"[Research] land_prices集計: {len(result)}都道府県", flush=True)
        return result
    except Exception as e:
        print(f"[Research] land_prices集計失敗: {e}", flush=True)
        return []


# ─────────────────────────────────────────────
# 4. knowledge_base への書き込み
# ─────────────────────────────────────────────

def _upsert_knowledge(conn, category: str, subcategory: str, scope: str,
                       prefecture: str, title: str, summary: str,
                       data: Any, source: str, source_url: str = ""):
    """knowledge_base テーブルに INSERT OR UPDATE（タイトル+スコープでユニーク）"""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO knowledge_base
            (category, subcategory, scope, prefecture, title, summary, data,
             source, source_url, is_active, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,1,NOW(),NOW())
        ON CONFLICT (title, scope)
        DO UPDATE SET
            summary    = EXCLUDED.summary,
            data       = EXCLUDED.data,
            source     = EXCLUDED.source,
            source_url = EXCLUDED.source_url,
            is_active  = 1,
            updated_at = NOW()
    """, (
        category, subcategory, scope, prefecture,
        title, summary, json.dumps(data, ensure_ascii=False),
        source, source_url
    ))
    conn.commit()
    cur.close()


# ─────────────────────────────────────────────
# 5. メイン実行
# ─────────────────────────────────────────────

def run_research() -> int:
    """
    すべてのデータソースを収集し knowledge_base に保存する。
    Returns: 更新レコード数
    """
    print("[Research] Research Agent 開始", flush=True)
    updated = 0

    try:
        conn = _get_pg_conn()
    except Exception as e:
        print(f"[Research] DB接続失敗: {e}", flush=True)
        return 0

    # --- 1. 日銀政策金利 ---
    try:
        boj = fetch_boj_rate()
        _upsert_knowledge(
            conn,
            category="financial",
            subcategory="interest_rate",
            scope="national",
            prefecture="",
            title="日銀政策金利（最新）",
            summary=(
                f"日本銀行の政策金利は {boj['period']} 時点で {boj['rate']}% です。"
                "住宅ローン金利の参考指標となります。"
            ),
            data=boj,
            source=boj["source"],
            source_url="https://www.boj.or.jp/statistics/",
        )
        updated += 1
        print(f"[Research] 日銀金利 knowledge_base 保存完了: {boj['rate']}%", flush=True)
    except Exception as e:
        print(f"[Research] 日銀金利保存エラー: {e}", flush=True)

    # --- 2. e-Stat 都道府県別人口 ---
    try:
        pop_map = fetch_estat_population()
        # 全国まとめ
        total = sum(pop_map.values())
        _upsert_knowledge(
            conn,
            category="demographics",
            subcategory="population",
            scope="national",
            prefecture="",
            title="都道府県別人口（最新推計）",
            summary=f"全国47都道府県の人口データ。総計約{total}万人。",
            data=pop_map,
            source="総務省 e-Stat",
            source_url="https://www.e-stat.go.jp/",
        )
        updated += 1

        # 都道府県別個別レコード
        for pref, pop in pop_map.items():
            _upsert_knowledge(
                conn,
                category="demographics",
                subcategory="population",
                scope="prefecture",
                prefecture=pref,
                title=f"{pref}の人口（推計）",
                summary=f"{pref}の推計人口は約{pop}万人です。",
                data={"prefecture": pref, "population_man": pop, "unit": "万人"},
                source="総務省 e-Stat",
                source_url="https://www.e-stat.go.jp/",
            )
            updated += 1

        print(f"[Research] 人口データ knowledge_base 保存完了: {len(pop_map)+1}件", flush=True)
    except Exception as e:
        print(f"[Research] 人口データ保存エラー: {e}", flush=True)

    # --- 3. 地価サマリー（都道府県別） ---
    try:
        land_summaries = fetch_land_price_summary()
        for item in land_summaries:
            pref = item["prefecture"]
            _upsert_knowledge(
                conn,
                category="real_estate",
                subcategory="land_price",
                scope="prefecture",
                prefecture=pref,
                title=f"{pref}の住宅地価サマリー（2024年）",
                summary=(
                    f"{pref}の住宅地平均地価は{item['avg']:,.0f}円/㎡、"
                    f"最高値{item['max']:,.0f}円/㎡（{item['count']}地点）。"
                    "（出所: 国土交通省 地価公示 2024年）"
                ),
                data=item,
                source="国土交通省 地価公示（2024年）",
                source_url="https://www.land.mlit.go.jp/landPrice/AriaServlet",
            )
            updated += 1

        print(f"[Research] 地価サマリー knowledge_base 保存完了: {len(land_summaries)}件", flush=True)
    except Exception as e:
        print(f"[Research] 地価サマリー保存エラー: {e}", flush=True)

    conn.close()
    print(f"[Research] Research Agent 完了: {updated}件保存", flush=True)
    return updated


if __name__ == "__main__":
    run_research()
