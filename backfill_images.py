#!/usr/bin/env python3
"""
Unsplash画像バックフィルスクリプト
既存記事にUnsplash画像を追加し、完了後に自動ビルド&デプロイ

使い方:
    python3 backfill_images.py [--limit N] [--dry-run] [--no-deploy]

オプション:
    --limit N      処理する記事数（デフォルト: 全件）
    --dry-run      実際にファイルを更新せずテストのみ
    --no-deploy    ビルド&デプロイをスキップ
"""

import os
import re
import sys
import json
import time
import logging
import argparse
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CONTENT_DIR = ROOT / "site" / "content" / "post"
SITE_DIR = ROOT / "site"
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# Unsplash free tier: 50 requests/hour
RATE_LIMIT_DELAY = 1.5  # seconds between requests


def fetch_unsplash_image(query: str, fallback_queries: list[str]) -> dict | None:
    """Unsplashから画像を取得"""
    if not UNSPLASH_KEY:
        log.error("UNSPLASH_ACCESS_KEY が設定されていません")
        return None

    for q in [query] + fallback_queries:
        try:
            params = urllib.parse.urlencode({
                "query": q,
                "per_page": 3,
                "orientation": "landscape",
            })
            req = urllib.request.Request(
                f"https://api.unsplash.com/search/photos?{params}",
                headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                results = data.get("results", [])
                if results:
                    photo = results[0]
                    # Unsplash利用規約: ダウンロードトリガー必須
                    try:
                        dl_req = urllib.request.Request(
                            photo["links"]["download_location"],
                            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"},
                        )
                        urllib.request.urlopen(dl_req, timeout=10).close()
                    except Exception:
                        pass
                    return {
                        "url": photo["urls"]["regular"],
                        "photographer": photo["user"]["name"],
                        "photographer_url": photo["user"]["links"]["html"],
                    }
        except urllib.error.HTTPError as e:
            if e.code == 403:
                log.error("Unsplash APIレート制限 (403). 終了します。")
                sys.exit(1)
            log.warning(f"Unsplash HTTPError {e.code} for '{q}'")
        except Exception as e:
            log.warning(f"Unsplash fetch failed for '{q}': {e}")
        time.sleep(0.5)

    return None


def build_queries(front_matter: dict) -> tuple[str, list[str]]:
    """記事メタデータから検索クエリを構築"""
    article_type = front_matter.get("article_type", "area")
    pref = front_matter.get("prefecture", "")
    prop_type = front_matter.get("property_type", "")

    pref_en_map = {
        "東京都": "Tokyo", "神奈川県": "Yokohama", "大阪府": "Osaka",
        "京都府": "Kyoto", "北海道": "Hokkaido", "福岡県": "Fukuoka",
        "愛知県": "Nagoya", "宮城県": "Sendai", "広島県": "Hiroshima",
        "沖縄県": "Okinawa", "兵庫県": "Kobe", "埼玉県": "Saitama",
        "千葉県": "Chiba", "静岡県": "Shizuoka", "新潟県": "Niigata",
        "長野県": "Nagano", "石川県": "Kanazawa", "岡山県": "Okayama",
        "熊本県": "Kumamoto", "鹿児島県": "Kagoshima",
    }
    pref_en = pref_en_map.get(pref, "Japan")

    if article_type in ("satei", "timed_sell"):
        primary = f"{pref_en} Japan real estate"
        fallbacks = ["Japan property sale", "Japan city architecture", "Japan urban skyline"]
    elif article_type == "chiho_sell":
        primary = f"{pref_en} Japan rural house"
        fallbacks = ["Japan countryside house", "Japan akiya vacant house", "Japan suburban"]
    elif prop_type == "一戸建て":
        primary = f"{pref_en} Japan suburban house"
        fallbacks = ["Japan neighborhood house", "Japan residential street", "Japan house exterior"]
    else:
        primary = f"{pref_en} Japan city apartment"
        fallbacks = ["Japan apartment building", "Japan urban skyline", "Japan city view"]

    return primary, fallbacks


def parse_front_matter(content: str) -> dict:
    """フロントマターをパース"""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm = {}
    for line in content[3:end].strip().split("\n"):
        m = re.match(r'^(\w+):\s*"?([^"]+)"?\s*$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def inject_image_into_front_matter(raw_content: str, image: dict) -> str:
    """フロントマターに画像フィールドを追加（既存フィールドは絶対に変更しない）"""
    if not raw_content.startswith("---"):
        return raw_content

    end_idx = raw_content.find("\n---", 3)
    if end_idx == -1:
        return raw_content

    # 既にimageフィールドがある場合は何もしない（安全装置）
    fm_block = raw_content[:end_idx]
    if "image:" in fm_block:
        return raw_content

    image_lines = (
        f'\nimage: "{image["url"]}"'
        f'\nimage_credit_name: "{image["photographer"]}"'
        f'\nimage_credit_url: "{image["photographer_url"]}"'
    )

    if "draft: false" in fm_block:
        fm_block = fm_block.replace("draft: false", f"draft: false{image_lines}", 1)
    else:
        fm_block += image_lines

    return fm_block + raw_content[end_idx:]


def build_and_deploy(updated_count: int):
    """hugo ビルド → git commit → git push"""
    log.info(f"=== ビルド&デプロイ開始 ({updated_count}件の記事を更新) ===")

    # hugo --minify (--environment production で livereload artifacts を防ぐ)
    result = subprocess.run(
        ["hugo", "--minify", "--environment", "production", "--destination", "../docs"],
        cwd=SITE_DIR,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error(f"hugo build 失敗:\n{result.stderr}")
        return False
    log.info("hugo build 完了")

    # git add
    subprocess.run(["git", "add", "docs/", "site/content/post/"], cwd=ROOT, check=True)

    # 変更があるか確認
    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=ROOT
    )
    if status.returncode == 0:
        log.info("変更なし。デプロイスキップ。")
        return True

    # git commit
    msg = f"feat: add Unsplash images to {updated_count} articles (backfill)"
    subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)

    # git push
    result = subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        # rebaseして再試行
        log.warning("push失敗。rebase後に再試行します。")
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)

    log.info("✅ デプロイ完了")
    return True


def main():
    parser = argparse.ArgumentParser(description="Unsplash画像バックフィル")
    parser.add_argument("--limit", type=int, default=0, help="処理上限（0=全件）")
    parser.add_argument("--dry-run", action="store_true", help="ファイル更新なし")
    parser.add_argument("--no-deploy", action="store_true", help="ビルド&デプロイしない")
    args = parser.parse_args()

    if not UNSPLASH_KEY:
        log.error("UNSPLASH_ACCESS_KEY 環境変数を設定してください")
        sys.exit(1)

    # 画像のない記事を収集
    md_files = sorted(CONTENT_DIR.glob("*.md"))
    no_image = [f for f in md_files if "image:" not in f.read_text(encoding="utf-8")]

    log.info(f"画像なし記事: {len(no_image)}件")

    if not no_image:
        log.info("全記事に画像あり。処理不要。")
        return

    if args.limit:
        no_image = no_image[:args.limit]
        log.info(f"処理上限: {args.limit}件")

    success = 0
    fail = 0

    for i, md_path in enumerate(no_image, 1):
        content = md_path.read_text(encoding="utf-8")
        fm = parse_front_matter(content)

        primary, fallbacks = build_queries(fm)
        log.info(f"[{i}/{len(no_image)}] {md_path.name} → {primary}")

        if args.dry_run:
            log.info("  [dry-run] スキップ")
            success += 1
            continue

        image = fetch_unsplash_image(primary, fallbacks)
        time.sleep(RATE_LIMIT_DELAY)

        if image:
            new_content = inject_image_into_front_matter(content, image)
            md_path.write_text(new_content, encoding="utf-8")
            log.info(f"  ✅ {image['photographer']}")
            success += 1
        else:
            log.warning(f"  ❌ 画像取得失敗")
            fail += 1

    log.info(f"\n完了: 成功 {success}件, 失敗 {fail}件")

    # 更新があればビルド&デプロイ
    if success > 0 and not args.dry_run and not args.no_deploy:
        build_and_deploy(success)


if __name__ == "__main__":
    main()
