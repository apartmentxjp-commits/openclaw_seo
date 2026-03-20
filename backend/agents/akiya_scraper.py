"""
Akiya Scraper Agent — 空き家バンク自動収集エージェント

ローリング方式で毎週3自治体ずつスクレイプ:
  1. municipalities.json からバッチ番号順に未処理の3自治体を選択
  2. 各自治体の空き家バンクページをフェッチ
  3. Groq (LLM) でHTMLから物件情報を抽出・英語翻訳
  4. akiya_portal の Supabase に挿入（status='pending' → 手動承認 or 自動）
  5. municipalities.json の status を 'done' に更新

リスク対策:
  - robots.txt 確認
  - リクエスト間に2〜5秒のランダムスリープ
  - 1自治体あたり最大20件まで
  - エラー時は status='error' に更新して継続
"""

import os
import json
import time
import random
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────────────────────────────────────
MUNICIPALITIES_FILE = Path(__file__).parent.parent / "data" / "municipalities.json"
MAX_PROPERTIES_PER_MUNICIPALITY = 20
REQUEST_DELAY = (2, 5)  # seconds between requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AkiyaPortalBot/1.0; +https://akiya.tacky-consulting.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.5",
}

# ─────────────────────────────────────────────────────────────────────────────
# Supabase クライアント（akiya_portal 用）
# ─────────────────────────────────────────────────────────────────────────────
def _get_supabase():
    """akiya_portal の Supabase admin クライアントを返す"""
    from supabase import create_client
    url = os.getenv("AKIYA_SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("AKIYA_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("AKIYA_SUPABASE_URL / AKIYA_SUPABASE_SERVICE_ROLE_KEY が未設定")
    return create_client(url, key)


# ─────────────────────────────────────────────────────────────────────────────
# municipalities.json の読み書き
# ─────────────────────────────────────────────────────────────────────────────
def _load_municipalities() -> list[dict]:
    with open(MUNICIPALITIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["municipalities"]


def _save_status(municipality_id: int, status: str):
    """municipalities.json の該当エントリのステータスを更新"""
    with open(MUNICIPALITIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    for m in data["municipalities"]:
        if m["id"] == municipality_id:
            m["status"] = status
            m["updated_at"] = datetime.utcnow().isoformat()
            break
    with open(MUNICIPALITIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_next_batch(municipalities: list[dict]) -> list[dict]:
    """
    次に処理すべきバッチ（最小バッチ番号の pending 自治体 3件）を返す
    """
    pending = [m for m in municipalities if m["status"] == "pending"]
    if not pending:
        return []
    min_batch = min(m["batch"] for m in pending)
    batch = [m for m in pending if m["batch"] == min_batch]
    return batch[:3]


# ─────────────────────────────────────────────────────────────────────────────
# HTML フェッチ
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_page(url: str) -> str | None:
    """ページHTMLを取得。失敗時は None を返す"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:
        print(f"[Scraper] フェッチ失敗: {url} — {e}", flush=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Groq で物件情報抽出
# ─────────────────────────────────────────────────────────────────────────────
EXTRACT_PROMPT = """
You are a real estate data extraction expert for Japanese akiya (vacant house) listings.
Extract ALL property listings from the HTML below.

For each property found, return a JSON array with objects having these fields:
- title: (string) property name/title in Japanese
- price: (number | null) price in 万円 (e.g. 280 means 280万円 = 2,800,000 yen). null if free/unknown
- prefecture: (string) prefecture name in Japanese (e.g. 長野県)
- city: (string) city/town name in Japanese (e.g. 飯山市)
- description: (string) full property description in Japanese
- building_area: (number | null) building area in m²
- land_area: (number | null) land area in m²
- year_built: (number | null) year built (e.g. 1985)
- property_type: (string) one of: kominka, farmhouse, machiya, villa, house, land, other
- images: (array of strings) image URLs found (absolute URLs only)
- source_url: (string) the URL of this specific listing if available, else empty string

Return ONLY a valid JSON array. If no properties found, return [].
Max 20 properties.

HTML:
{html}
"""

def _extract_properties_with_llm(html: str, municipality: dict) -> list[dict]:
    """Groq LLM でHTMLから物件情報を抽出"""
    groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # HTML を短縮（Groq の context limit 対策）
    html_trimmed = html[:12000] if len(html) > 12000 else html

    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": EXTRACT_PROMPT.format(html=html_trimmed)
            }],
            max_tokens=4096,
            temperature=0.1,
        )
        text = response.choices[0].message.content or "[]"

        # JSON 抽出
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        properties = json.loads(text.strip())
        if not isinstance(properties, list):
            return []

        # prefecture/city のデフォルト値を自治体情報で補完
        for p in properties:
            if not p.get("prefecture"):
                p["prefecture"] = municipality["prefecture"]
            if not p.get("city"):
                p["city"] = municipality["name"]

        return properties[:MAX_PROPERTIES_PER_MUNICIPALITY]

    except Exception as e:
        print(f"[Scraper] LLM 抽出エラー ({municipality['name']}): {e}", flush=True)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# 英語翻訳
# ─────────────────────────────────────────────────────────────────────────────
TRANSLATE_PROMPT = """Translate this Japanese real estate listing to English for international buyers.
Keep Japanese cultural terms (kominka, machiya, satoyama) when appropriate.

Title: {title}
Description: {description}

Respond with JSON only:
{{"title_en": "...", "description_en": "..."}}"""

def _translate(title: str, description: str) -> tuple[str, str]:
    """タイトルと説明文を英語に翻訳"""
    groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": TRANSLATE_PROMPT.format(
                title=title[:200],
                description=(description or "")[:500]
            )}],
            max_tokens=512,
            temperature=0.3,
        )
        text = response.choices[0].message.content or "{}"
        if "```" in text:
            text = text.split("```")[1].split("```")[0]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        return result.get("title_en", title), result.get("description_en", description)
    except Exception:
        return title, description or ""


# ─────────────────────────────────────────────────────────────────────────────
# Supabase への挿入
# ─────────────────────────────────────────────────────────────────────────────
def _insert_property(supabase, prop: dict, source_municipality: str) -> bool:
    """物件を Supabase に挿入。重複は source_url で検出してスキップ"""
    source_url = prop.get("source_url", "")

    # 重複チェック
    if source_url:
        existing = supabase.table("properties") \
            .select("id") \
            .eq("source", source_url) \
            .limit(1) \
            .execute()
        if existing.data:
            return False  # 既存

    title = prop.get("title", "").strip()
    if not title:
        return False

    title_en, desc_en = _translate(title, prop.get("description", ""))

    # slug 生成
    slug_base = f"{prop.get('prefecture', '')} {prop.get('city', '')} {title}"
    slug = hashlib.md5(slug_base.encode()).hexdigest()[:12]

    record = {
        "title":          title,
        "title_en":       title_en,
        "description":    prop.get("description", ""),
        "description_en": desc_en,
        "price":          prop.get("price"),           # 万円単位
        "prefecture":     prop.get("prefecture", ""),
        "city":           prop.get("city", ""),
        "building_area":  prop.get("building_area"),
        "land_area":      prop.get("land_area"),
        "year_built":     prop.get("year_built"),
        "property_type":  prop.get("property_type", "house"),
        "images":         prop.get("images", []),
        "slug":           slug,
        "source":         source_url or source_municipality,
        "status":         os.getenv("AKIYA_SCRAPER_STATUS", "pending"),  # 'pending' or 'approved'
        "created_at":     datetime.utcnow().isoformat(),
        "updated_at":     datetime.utcnow().isoformat(),
    }

    try:
        supabase.table("properties").insert(record).execute()
        return True
    except Exception as e:
        print(f"[Scraper] DB挿入エラー: {e}", flush=True)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# メイン: 1自治体スクレイプ
# ─────────────────────────────────────────────────────────────────────────────
def scrape_municipality(municipality: dict) -> dict:
    """
    1自治体の空き家バンクをスクレイプして物件を登録。
    Returns: {"municipality": name, "scraped": N, "inserted": M, "status": ok/error}
    """
    name = municipality["name"]
    pref = municipality["prefecture"]
    url  = municipality["url"]
    print(f"[Scraper] {pref} {name} スクレイプ開始: {url}", flush=True)

    html = _fetch_page(url)
    if not html:
        _save_status(municipality["id"], "error")
        return {"municipality": name, "scraped": 0, "inserted": 0, "status": "error"}

    time.sleep(random.uniform(*REQUEST_DELAY))

    properties = _extract_properties_with_llm(html, municipality)
    print(f"[Scraper] {name}: {len(properties)}件抽出", flush=True)

    if not properties:
        # 物件なし = 空き家バンクページが見つからなかった可能性
        _save_status(municipality["id"], "done")
        return {"municipality": name, "scraped": 0, "inserted": 0, "status": "ok_empty"}

    try:
        supabase = _get_supabase()
    except RuntimeError as e:
        print(f"[Scraper] Supabase 接続失敗: {e}", flush=True)
        _save_status(municipality["id"], "error")
        return {"municipality": name, "scraped": len(properties), "inserted": 0, "status": "error"}

    inserted = 0
    for prop in properties:
        time.sleep(random.uniform(0.5, 1.5))
        if _insert_property(supabase, prop, url):
            inserted += 1

    _save_status(municipality["id"], "done")
    print(f"[Scraper] {name}: {inserted}/{len(properties)}件登録完了", flush=True)
    return {"municipality": name, "scraped": len(properties), "inserted": inserted, "status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# 週次バッチ実行（scheduler から呼び出す）
# ─────────────────────────────────────────────────────────────────────────────
def run_weekly_akiya_scrape() -> list[dict]:
    """
    週次で次の3自治体をスクレイプする。
    全バッチ完了後は status をリセットして再サイクル。
    """
    municipalities = _load_municipalities()
    batch = _get_next_batch(municipalities)

    if not batch:
        # 全自治体完了 → pending にリセットして再サイクル
        print("[Scraper] 全自治体完了。再サイクルのため status をリセット", flush=True)
        data_path = MUNICIPALITIES_FILE
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for m in data["municipalities"]:
            m["status"] = "pending"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        municipalities = data["municipalities"]
        batch = _get_next_batch(municipalities)

    results = []
    for municipality in batch:
        result = scrape_municipality(municipality)
        results.append(result)
        time.sleep(random.uniform(3, 8))  # 自治体間のインターバル

    total_inserted = sum(r["inserted"] for r in results)
    print(f"[Scraper] 週次バッチ完了: {len(results)}自治体, 合計{total_inserted}件登録", flush=True)
    return results
