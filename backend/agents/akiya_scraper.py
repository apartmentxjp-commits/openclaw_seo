"""
Akiya Scraper Agent — アットホーム空き家バンク自動収集エージェント

ローリング方式で毎週3都道府県ずつスクレイプ:
  1. pref_state.json から未処理の都道府県を3件選択
  2. https://www.akiya-athome.jp/buy/{pref_code}/ を取得（最大100件/ページ）
  3. 各物件の詳細ページを取得 → 写真・フル住所・設備を抽出
  4. 英語に翻訳して akiya_portal の Supabase に挿入
  5. pref_state.json の status を 'done' に更新

リスク対策:
  - User-Agent をブラウザに偽装
  - リクエスト間に2〜5秒のランダムスリープ
  - 1都道府県あたり最大50件まで
  - エラー時は status='error' に更新して継続
"""

import os
import re
import json
import time
import random
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
PREF_STATE_FILE = DATA_DIR / "pref_state.json"
MAX_PROPERTIES_PER_PREF = 50
REQUEST_DELAY = (2, 5)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
    "Referer": "https://www.akiya-athome.jp/",
}

BASE_URL = "https://www.akiya-athome.jp"

# 都道府県コード → 名前マッピング
PREFECTURES = {
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


# ─────────────────────────────────────────────────────────────────────────────
# pref_state.json — 都道府県ごとの処理状態管理
# ─────────────────────────────────────────────────────────────────────────────
def _load_pref_state() -> dict:
    """都道府県処理状態を読み込む。ファイルがなければ初期化"""
    if PREF_STATE_FILE.exists():
        with open(PREF_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # 初期化
    state = {code: {"name": name, "status": "pending", "updated_at": None}
             for code, name in PREFECTURES.items()}
    _save_pref_state(state)
    return state


def _save_pref_state(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PREF_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _get_next_pref_batch(state: dict, size: int = 3) -> list[str]:
    """処理待ちの都道府県コードを最大 size 件返す"""
    pending = [code for code, v in state.items() if v["status"] == "pending"]
    return pending[:size]


# ─────────────────────────────────────────────────────────────────────────────
# HTTP フェッチ
# ─────────────────────────────────────────────────────────────────────────────
def _fetch(url: str, timeout: int = 20) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:
        print(f"[Scraper] フェッチ失敗: {url} — {e}", flush=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 一覧ページのパース
# ─────────────────────────────────────────────────────────────────────────────
def _parse_listing_page(html: str, pref_code: str) -> list[dict]:
    """
    https://www.akiya-athome.jp/buy/{pref_code}/?display_num=100
    から物件の概要リストを返す
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # 各物件は <section> または detail リンクを含む要素で構成される
    # detail リンク: href="https://{city}-{type}{code}.akiya-athome.jp/bukken/detail/buy/{id}"
    detail_links = soup.find_all("a", href=re.compile(r"akiya-athome\.jp/bukken/detail/buy/\d+"))

    seen_urls = set()
    for a in detail_links:
        url = a.get("href", "")
        if not url or url in seen_urls:
            continue
        if url.startswith("//"):
            url = "https:" + url
        seen_urls.add(url)

        # 親要素から概要データを抽出
        container = a.find_parent("section") or a.find_parent("article") or a.parent

        title = a.get_text(strip=True) or ""

        # 価格: 数字 + 万円 パターン
        price = None
        price_tag = container.find(string=re.compile(r"\d+万円")) if container else None
        if price_tag:
            m = re.search(r"([\d,]+)万円", price_tag)
            if m:
                price = int(m.group(1).replace(",", ""))

        # 所在地
        address = ""
        for tag in (container.find_all(string=re.compile(r"北海道|青森|岩手|宮城|秋田|山形|福島|茨城|栃木|群馬|埼玉|千葉|東京|神奈川|新潟|富山|石川|福井|山梨|長野|岐阜|静岡|愛知|三重|滋賀|京都|大阪|兵庫|奈良|和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|大分|宮崎|鹿児島|沖縄")) if container else []):
            address = tag.strip()
            break

        results.append({
            "detail_url": url,
            "title": title,
            "price": price,
            "address_raw": address,
            "prefecture": PREFECTURES.get(pref_code, ""),
        })

    return results[:MAX_PROPERTIES_PER_PREF]


# ─────────────────────────────────────────────────────────────────────────────
# 詳細ページのパース
# ─────────────────────────────────────────────────────────────────────────────
def _parse_detail_page(html: str, base: dict) -> dict:
    """
    詳細ページから写真・フル住所・詳細スペックを抽出して base に追記
    """
    soup = BeautifulSoup(html, "html.parser")

    # ── タイトル（詳細ページから取得） ──
    title = base.get("title", "")
    if not title:
        for sel in ["h1", ".bk-name", ".bukken-name", ".property-name"]:
            el = soup.select_one(sel)
            if el:
                candidate = el.get_text(strip=True)
                if candidate:
                    title = candidate
                    break
    if not title:
        # <title>タグから抽出: "登録番号４ - 物件詳細 - ..." → 先頭部分
        page_title = soup.find("title")
        if page_title:
            title = page_title.get_text(strip=True).split(" - ")[0].strip()

    # ── 価格（詳細ページから取得） ──
    price = base.get("price")
    if price is None:
        for tag in soup.find_all(string=re.compile(r"[\d,]+万円")):
            m = re.search(r"([\d,]+)万円", tag)
            if m:
                price = int(m.group(1).replace(",", ""))
                break

    # ── 画像 ──
    images = []
    # JS変数 image_tile_carousel_image_s からURLを抽出
    script_match = re.search(r"image_tile_carousel_image_s\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if script_match:
        try:
            img_data = json.loads(script_match.group(1))
            for img in img_data:
                full = img.get("image_url_fullsize", "") or img.get("image_url_thumbnail", "")
                if full:
                    if full.startswith("//"):
                        full = "https:" + full
                    images.append(full)
        except Exception:
            pass

    # ── テーブルデータ ──
    def _cell(label: str) -> str:
        """テーブルから label に対応するセル値を取得"""
        for th in soup.find_all(["th", "td", "dt", "div"], string=re.compile(label)):
            sibling = th.find_next_sibling() or th.find_next(["td", "dd"])
            if sibling:
                return sibling.get_text(strip=True)
        return ""

    # 所在地（フル住所）
    address = ""
    for tag in soup.find_all(string=re.compile(r"所在地")):
        parent = tag.parent
        nxt = parent.find_next(["td", "dd", "span", "div"])
        if nxt:
            candidate = nxt.get_text(strip=True)
            if len(candidate) > 5:
                address = candidate
                break

    # 都道府県・市区町村の分離
    prefecture = base.get("prefecture", "")
    city = ""
    if address:
        # 例: "北海道函館市湯浜町 6-10" → prefecture=北海道 city=函館市
        m = re.match(r"(北海道|.+?[都道府県])(.+?[市区町村郡])(.+)?", address)
        if m:
            prefecture = m.group(1)
            city = m.group(2)

    # 建物面積・土地面積
    building_area = None
    land_area = None
    for tag in soup.find_all(string=re.compile(r"\d+\.?\d*㎡")):
        txt = tag.strip()
        label_el = tag.find_previous(string=re.compile(r"建物面積|土地面積"))
        if label_el:
            m = re.search(r"([\d.]+)㎡", txt)
            if m:
                val = float(m.group(1))
                if "建物" in label_el:
                    building_area = val
                elif "土地" in label_el:
                    land_area = val

    # より確実なパース: テーブル行を走査
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True)
            val = cells[1].get_text(strip=True)
            m = re.search(r"([\d.]+)㎡", val)
            if m:
                num = float(m.group(1))
                if "建物" in key:
                    building_area = num
                elif "土地" in key:
                    land_area = num

    # 築年月
    year_built = None
    for tag in soup.find_all(string=re.compile(r"\d{4}年\d+月")):
        m = re.search(r"(\d{4})年", tag)
        if m:
            year_built = int(m.group(1))
            break

    # 間取り
    floor_plan = ""
    for tag in soup.find_all(string=re.compile(r"\d[SLDK]+$")):
        floor_plan = tag.strip()
        break

    # 説明文
    description = ""
    for cls in ["description", "detail-comment", "comment", "bk-comment"]:
        el = soup.find(class_=re.compile(cls, re.I))
        if el:
            description = el.get_text(strip=True)
            break

    # 物件種別
    property_type = "house"
    type_map = {
        "古民家": "kominka", "民家": "kominka",
        "農家": "farmhouse", "農地": "farmhouse",
        "町家": "machiya", "別荘": "villa",
        "土地": "land", "宅地": "land",
    }
    title_for_type = title or base.get("title", "")
    for jp, en in type_map.items():
        if jp in title_for_type or jp in description:
            property_type = en
            break

    return {
        **base,
        "title": title,
        "price": price,
        "images": images,
        "address": address,
        "prefecture": prefecture,
        "city": city,
        "building_area": building_area,
        "land_area": land_area,
        "year_built": year_built,
        "floor_plan": floor_plan,
        "description": description,
        "property_type": property_type,
        "source_url": base.get("detail_url", ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 英語翻訳
# ─────────────────────────────────────────────────────────────────────────────
TRANSLATE_PROMPT = """Translate this Japanese real estate listing to English for international buyers.
Keep Japanese cultural terms (kominka, machiya, satoyama, noka) when appropriate.
Title: {title}
Description: {description}
Respond with JSON only: {{"title_en": "...", "description_en": "..."}}"""


def _translate(title: str, description: str) -> tuple[str, str]:
    groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
    try:
        resp = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": TRANSLATE_PROMPT.format(
                title=title[:300], description=(description or "")[:600]
            )}],
            max_tokens=512,
            temperature=0.3,
        )
        text = resp.choices[0].message.content or "{}"
        if "```" in text:
            text = text.split("```")[1].split("```")[0]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        return result.get("title_en", title), result.get("description_en", description or "")
    except Exception:
        return title, description or ""


# ─────────────────────────────────────────────────────────────────────────────
# Supabase
# ─────────────────────────────────────────────────────────────────────────────
def _get_supabase():
    from supabase import create_client
    url = os.getenv("AKIYA_SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("AKIYA_SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("AKIYA_SUPABASE_URL / AKIYA_SUPABASE_SERVICE_ROLE_KEY が未設定")
    return create_client(url, key)


# 成約・交渉中などの物件を除外するキーワード
SKIP_KEYWORDS = ['成約', '交渉中', '申込', '売約', '商談中', '契約済', '取引中']

def _insert_property(supabase, prop: dict) -> bool:
    source_url = prop.get("source_url", "")
    title = prop.get("title", "")
    if not title:
        return False

    # 成約・交渉中物件をスキップ
    if any(kw in title for kw in SKIP_KEYWORDS):
        print(f"[Scraper]   スキップ（{next(kw for kw in SKIP_KEYWORDS if kw in title)}）: {title[:40]}", flush=True)
        return False

    # 重複チェック
    if source_url:
        existing = supabase.table("properties").select("id").eq("source", source_url).limit(1).execute()
        if existing.data:
            return False

    title_en, desc_en = _translate(prop.get("title", ""), prop.get("description", ""))
    slug = hashlib.md5(source_url.encode() or prop.get("title", "").encode()).hexdigest()[:12]

    record = {
        "title":          prop.get("title", ""),
        "title_en":       title_en,
        "description":    prop.get("description", ""),
        "description_en": desc_en,
        "price":          prop.get("price"),
        "prefecture":     prop.get("prefecture", ""),
        "city":           prop.get("city", ""),
        "address":        prop.get("address", ""),
        "building_area":  prop.get("building_area"),
        "land_area":      prop.get("land_area"),
        "year_built":     prop.get("year_built"),
        "property_type":  prop.get("property_type", "house"),
        "images":         prop.get("images", []),
        "slug":           slug,
        "source":         source_url,
        "status":         os.getenv("AKIYA_SCRAPER_STATUS", "pending"),
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
# 都道府県スクレイプ
# ─────────────────────────────────────────────────────────────────────────────
def scrape_prefecture(pref_code: str) -> dict:
    """
    1都道府県の akiya-athome.jp 一覧をスクレイプして物件を登録。
    """
    pref_name = PREFECTURES.get(pref_code, pref_code)
    listing_url = f"{BASE_URL}/buy/{pref_code}/?display_num=100&proc_search="
    print(f"[Scraper] {pref_name}({pref_code}) 開始: {listing_url}", flush=True)

    html = _fetch(listing_url)
    if not html:
        return {"prefecture": pref_name, "scraped": 0, "inserted": 0, "status": "error"}

    listings = _parse_listing_page(html, pref_code)
    print(f"[Scraper] {pref_name}: {len(listings)}件の詳細URLを検出", flush=True)

    if not listings:
        return {"prefecture": pref_name, "scraped": 0, "inserted": 0, "status": "ok_empty"}

    try:
        supabase = _get_supabase()
    except RuntimeError as e:
        print(f"[Scraper] Supabase 接続失敗: {e}", flush=True)
        return {"prefecture": pref_name, "scraped": len(listings), "inserted": 0, "status": "error"}

    inserted = 0
    for listing in listings:
        time.sleep(random.uniform(*REQUEST_DELAY))

        detail_url = listing.get("detail_url", "")
        detail_html = _fetch(detail_url)
        if not detail_html:
            continue

        prop = _parse_detail_page(detail_html, listing)
        if _insert_property(supabase, prop):
            inserted += 1
            print(f"[Scraper]   ✓ {prop.get('title', '')[:40]} ({len(prop.get('images', []))}枚)", flush=True)

    print(f"[Scraper] {pref_name}: {inserted}/{len(listings)}件登録完了", flush=True)
    return {"prefecture": pref_name, "scraped": len(listings), "inserted": inserted, "status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# 週次バッチ実行（scheduler から呼び出す）
# ─────────────────────────────────────────────────────────────────────────────
def run_weekly_akiya_scrape() -> list[dict]:
    """
    週次で次の3都道府県をスクレイプする。
    全県完了後は pending にリセットして再サイクル。
    """
    state = _load_pref_state()
    batch = _get_next_pref_batch(state, size=3)

    if not batch:
        print("[Scraper] 全都道府県完了。再サイクルのため status をリセット", flush=True)
        for code in state:
            state[code]["status"] = "pending"
        _save_pref_state(state)
        batch = _get_next_pref_batch(state, size=3)

    results = []
    for pref_code in batch:
        result = scrape_prefecture(pref_code)
        results.append(result)

        # 状態を更新
        state[pref_code]["status"] = "done" if result["status"] in ("ok", "ok_empty") else "error"
        state[pref_code]["updated_at"] = datetime.utcnow().isoformat()
        _save_pref_state(state)

        time.sleep(random.uniform(5, 10))  # 都道府県間インターバル

    total_inserted = sum(r["inserted"] for r in results)
    print(f"[Scraper] 週次バッチ完了: {len(results)}県, 合計{total_inserted}件登録", flush=True)
    return results
