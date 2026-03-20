"""
Wikipedia API を使って記事のfront matterにサムネイルを一括追加するスクリプト。
画像はローカルに保存（site/static/images/thumbnails/）し、ローカルパスを使用。
Wikimediaのホットリンクブロックを回避するため外部URLは使わない。
"""
import os
import re
import time
import json
import urllib.request
import urllib.parse
from pathlib import Path

CONTENT_DIR = Path(__file__).parent.parent / "site" / "content" / "post"
THUMB_DIR   = Path(__file__).parent.parent / "site" / "static" / "images" / "thumbnails"
UA = "OpenClaw-RealEstate/1.0 (realestate.tacky-consulting.com; noc@wikimedia.org)"

THUMB_DIR.mkdir(parents=True, exist_ok=True)

# 「全国」などWikipediaにない場合のフォールバック検索ワード
FALLBACK_QUERIES = {
    "全国": "日本",
    "": "日本の不動産",
}


def sanitize_filename(url: str) -> str:
    """URLからファイル名を抽出し、特殊文字を除去してサニタイズする。"""
    filename = url.split("/")[-1]
    filename = urllib.parse.unquote(filename)   # %XX → 文字にデコード
    filename = re.sub(r'[^\w\-_\.]', '_', filename)  # 英数字・ハイフン・アンダースコア・ドット以外を_に
    filename = re.sub(r'_+', '_', filename)     # 連続する_を1つに
    return filename


def download_image(img_url: str) -> str | None:
    """画像をローカルに保存し、サイトルート相対パスを返す。すでにあればDLスキップ。"""
    filename = sanitize_filename(img_url)
    dest = THUMB_DIR / filename
    if not dest.exists():
        try:
            req = urllib.request.Request(img_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10) as r:
                dest.write_bytes(r.read())
            print(f"    📥 Downloaded: {filename}")
        except Exception as e:
            print(f"    ⚠️  Download failed for {filename}: {e}")
            return None
    return f"/images/thumbnails/{filename}"


def get_wikipedia_thumbnail(query: str) -> str | None:
    """Wikipedia REST APIからサムネイルURLを取得する。"""
    if not query:
        return None
    query = FALLBACK_QUERIES.get(query, query)

    url = f"https://ja.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            thumb = data.get("thumbnail", {}).get("source")
            if thumb:
                thumb = re.sub(r"/\d+px-", "/640px-", thumb)
            return thumb
    except Exception as e:
        print(f"  Wikipedia fetch failed for '{query}': {e}")
        return None


def add_thumbnail_to_file(md_path: Path) -> bool:
    """1ファイルにthumbnailを追加。追加した場合True。"""
    text = md_path.read_text(encoding="utf-8")

    # すでにthumbnailがあればスキップ
    if "thumbnail:" in text:
        return False

    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    fm_block = text[3:end]
    rest = text[end:]

    # area / prefecture / thumbnail_keyword を取得
    area_m = re.search(r'^area:\s*"?([^"\n]+)"?', fm_block, re.MULTILINE)
    pref_m = re.search(r'^prefecture:\s*"?([^"\n]+)"?', fm_block, re.MULTILINE)
    kw_m   = re.search(r'^thumbnail_keyword:\s*"?([^"\n]+)"?', fm_block, re.MULTILINE)
    area   = area_m.group(1).strip() if area_m else ""
    pref   = pref_m.group(1).strip() if pref_m else ""
    kw     = kw_m.group(1).strip()   if kw_m   else ""

    # 検索順：thumbnail_keyword → area → prefecture
    img_url = None
    for query in filter(None, [kw, area, pref]):
        img_url = get_wikipedia_thumbnail(query)
        if img_url:
            break

    if not img_url:
        print(f"  No thumbnail found: {md_path.name} (kw={kw}, area={area}, pref={pref})")
        return False

    # 画像をローカルに保存してパスを取得
    local_path = download_image(img_url)
    if not local_path:
        return False

    # thumbnail フィールドを front matter末尾に挿入
    new_fm_block = fm_block.rstrip() + f'\nthumbnail: "{local_path}"'
    new_text = "---" + new_fm_block + rest
    md_path.write_text(new_text, encoding="utf-8")
    print(f"  ✅ {md_path.name[:55]}  →  {local_path}")
    return True


def main():
    md_files = sorted(CONTENT_DIR.glob("*.md"))
    print(f"Found {len(md_files)} markdown files in {CONTENT_DIR}")

    added = 0
    skipped = 0
    failed = 0

    for i, f in enumerate(md_files):
        if f.name in ("index.md", "_index.md"):
            continue
        result = add_thumbnail_to_file(f)
        if result:
            added += 1
        else:
            if "thumbnail:" in f.read_text(encoding="utf-8"):
                skipped += 1
            else:
                failed += 1

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(md_files)}] sleeping 1s...")
            time.sleep(1)

    print(f"\nDone: added={added}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    main()
