"""
画像再取得 & Supabase Storage アップロードスクリプト

akiya-athome.jp の詳細ページから外観写真をダウンロードし、
Supabase Storage に保存して property の images フィールドを更新する。

- 間取り図・ロゴ入り画像は除外
- 成約・交渉中は除外（タイトルに含まれる場合）
- 既に images が設定済みの物件はスキップ
"""
import os, re, json, time, random, hashlib, requests
from supabase import create_client
from bs4 import BeautifulSoup

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://aqvpxzyyvliqamwbpwbt.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "property-images"

SKIP_IMG_KEYWORDS = [
    '間取り', '図面', 'madori', 'floor', 'plan',
    '地図', 'map', '路線', '周辺', '案内図', '位置図',
    '地形', '航空', 'satellite', '仕様', 'spec',
    '詳細図', '設計', '配置図', '現況図',
]
PREFER_KEYWORDS = ['外観', '建物', '正面', '全景', '外', '庭', '駐車', '玄関外']
SKIP_TITLE_KEYWORDS = ['成約', '交渉中', '申込', '売約', '商談中', '契約済', '取引中']


def make_session(referer: str = "https://www.akiya-athome.jp/") -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
        "Referer": referer,
    })
    return s


def fetch_and_upload_image(sb, prop: dict) -> str | None:
    """詳細ページから画像を取得してStorageにアップロード、URLを返す"""
    detail_url = prop.get("source", "")
    prop_id = prop.get("id", "")

    if not detail_url or "akiya-athome.jp" not in detail_url:
        return None

    session = make_session()

    try:
        # 詳細ページ取得
        session.headers["Referer"] = "https://www.akiya-athome.jp/"
        resp = session.get(detail_url, timeout=20)
        resp.raise_for_status()
        html = resp.text

        img_url = None

        # image_tile_carousel_image_s から画像URLを抽出
        script_match = re.search(r"image_tile_carousel_image_s\s*=\s*(\[.*?\]);", html, re.DOTALL)
        if script_match:
            img_data = json.loads(script_match.group(1))
            candidates = []
            for img in img_data:
                full = img.get("image_url_fullsize", "") or img.get("image_url_thumbnail", "")
                if not full:
                    continue
                if full.startswith("//"):
                    full = "https:" + full
                comment = str(img.get("comment", "") or img.get("title", "") or "").lower()
                # 除外キーワードが含まれる場合はスキップ
                if any(kw in comment for kw in SKIP_IMG_KEYWORDS):
                    continue
                if any(kw in full.lower() for kw in ['madori', 'floor', 'plan', 'map']):
                    continue
                is_exterior = any(kw in comment for kw in PREFER_KEYWORDS)
                candidates.append((full, is_exterior))

            # 外観写真優先、なければ最初の候補
            for url, is_ext in candidates:
                if is_ext:
                    img_url = url
                    break
            if not img_url and candidates:
                img_url = candidates[0][0]

        # OGPはスペック表・地図が混入しやすいので使わない
        if not img_url:
            return None

        # 画像ダウンロード（同一セッション & Refererを詳細ページに設定）
        session.headers["Referer"] = detail_url
        img_resp = session.get(img_url, timeout=20)
        img_resp.raise_for_status()

        content_type = img_resp.headers.get("Content-Type", "image/jpeg")
        if not content_type.startswith("image/"):
            return None

        img_bytes = img_resp.content
        if len(img_bytes) < 5000:  # 5KB未満は無効な画像
            return None

        # ファイル名を生成してStorageにアップロード
        ext = "jpg" if "jpeg" in content_type else content_type.split("/")[-1].split(";")[0]
        filename = f"{hashlib.md5(detail_url.encode()).hexdigest()[:12]}.{ext}"
        path = f"akiya/{filename}"

        sb.storage.from_(BUCKET).upload(
            path=path,
            file=img_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )

        # 公開URLを生成
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
        return public_url

    except Exception as e:
        print(f"  ⚠ エラー: {e}")
        return None


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    # バケット確認/作成
    try:
        sb.storage.create_bucket(BUCKET, options={"public": True})
        print(f"Bucket '{BUCKET}' created")
    except Exception:
        pass  # 既に存在

    # images が空の approved 物件を取得
    page_size = 100
    offset = 0
    to_update = []

    print("対象物件を取得中...")
    while True:
        r = sb.table("properties") \
            .select("id,source,title,images") \
            .eq("status", "approved") \
            .range(offset, offset + page_size - 1) \
            .execute()
        if not r.data:
            break
        for p in r.data:
            imgs = p.get("images") or []
            src = p.get("source", "") or ""
            title = p.get("title", "") or ""
            if (len(imgs) == 0
                    and "akiya-athome.jp" in src
                    and "/bukken/detail/buy/" in src
                    and not any(kw in title for kw in SKIP_TITLE_KEYWORDS)):
                to_update.append(p)
        offset += page_size
        if len(r.data) < page_size:
            break

    print(f"画像なし物件: {len(to_update)} 件")
    if not to_update:
        print("更新対象なし")
        return

    updated = 0
    failed = 0
    for i, prop in enumerate(to_update):
        print(f"[{i+1}/{len(to_update)}] {prop['title'][:40]}")
        public_url = fetch_and_upload_image(sb, prop)
        if public_url:
            sb.table("properties").update({"images": [public_url]}).eq("id", prop["id"]).execute()
            print(f"  ✓ {public_url}")
            updated += 1
        else:
            print(f"  ✗ 画像なし")
            failed += 1

        # 礼儀正しい遅延（2〜4秒）
        time.sleep(random.uniform(2, 4))

        if (i + 1) % 10 == 0:
            print(f"\n--- 進捗: {updated}件更新, {failed}件失敗 ({i+1}/{len(to_update)}) ---\n")

    print(f"\n完了: {updated}件更新, {failed}件失敗")


if __name__ == "__main__":
    main()
