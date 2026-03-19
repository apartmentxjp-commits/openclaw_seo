"""
Wikipedia API を使って記事のfront matterにサムネイルURLを一括追加するスクリプト。
APIキー不要・完全無料。
"""
import os
import re
import time
import json
import urllib.request
import urllib.parse
from pathlib import Path

CONTENT_DIR = Path(__file__).parent.parent / "site" / "content" / "post"
UA = "OpenClaw-RealEstate/1.0 (realestate.tacky-consulting.com)"

# 「全国」などWikipediaにない場合のフォールバック検索ワード
FALLBACK_QUERIES = {
    "全国": "日本",
    "": "日本の不動産",
}

# 都市名 → より良い検索ワードへのマッピング
CITY_ALIAS = {
    "東京都": "東京都",
    "大阪府": "大阪府",
    "横浜市": "横浜市",
    "名古屋市": "名古屋市",
    "札幌市": "札幌市",
    "福岡市": "福岡市",
}


def get_wikipedia_thumbnail(query: str) -> str | None:
    """Wikipedia REST APIからサムネイルURLを取得する。"""
    if not query:
        return None
    # フォールバック適用
    query = FALLBACK_QUERIES.get(query, query)

    url = f"https://ja.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            thumb = data.get("thumbnail", {}).get("source")
            if thumb:
                # 解像度を上げる（330px → 640px）
                thumb = re.sub(r"/\d+px-", "/640px-", thumb)
            return thumb
    except Exception as e:
        print(f"  Wikipedia fetch failed for '{query}': {e}")
        return None


def parse_front_matter(text: str) -> tuple[dict, str]:
    """YAMLフロントマターをパース。(front_matter_lines, body) を返す。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    body = text[end + 4:]
    fm = {}
    for line in fm_raw.split("\n"):
        m = re.match(r'^(\w+):\s*"?(.+?)"?\s*$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip('"')
    return fm, fm_raw, body


def add_thumbnail_to_file(md_path: Path) -> bool:
    """1ファイルにthumbnailを追加。追加した場合True。"""
    text = md_path.read_text(encoding="utf-8")

    # すでにthumbnailがあればスキップ
    if "thumbnail:" in text:
        return False

    # front matterを取得
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    fm_block = text[3:end]
    rest = text[end:]  # "\n---\n..." から始まる残り

    # area / prefecture / thumbnail_keyword を取得
    area_m = re.search(r'^area:\s*"?([^"\n]+)"?', fm_block, re.MULTILINE)
    pref_m = re.search(r'^prefecture:\s*"?([^"\n]+)"?', fm_block, re.MULTILINE)
    kw_m   = re.search(r'^thumbnail_keyword:\s*"?([^"\n]+)"?', fm_block, re.MULTILINE)
    area   = area_m.group(1).strip() if area_m else ""
    pref   = pref_m.group(1).strip() if pref_m else ""
    kw     = kw_m.group(1).strip()   if kw_m   else ""

    # 検索順：thumbnail_keyword → area → prefecture → fallback
    thumb = None
    for query in filter(None, [kw, area, pref]):
        thumb = get_wikipedia_thumbnail(query)
        if thumb:
            break

    if not thumb:
        print(f"  No thumbnail found: {md_path.name} (keyword={kw}, area={area}, pref={pref})")
        return False

    # thumbnail フィールドを front matter末尾に挿入
    new_fm_block = fm_block.rstrip() + f'\nthumbnail: "{thumb}"'
    new_text = "---" + new_fm_block + rest
    md_path.write_text(new_text, encoding="utf-8")
    print(f"  ✅ {md_path.name[:60]}  →  {thumb[:60]}...")
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

        # Wikipedia APIへの負荷を避けるため少し待つ
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(md_files)}] sleeping 1s...")
            time.sleep(1)

    print(f"\nDone: added={added}, skipped={skipped}, failed={failed}")


if __name__ == "__main__":
    main()
