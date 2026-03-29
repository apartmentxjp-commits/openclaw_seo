#!/usr/bin/env python3
"""
OpenClaw 不動産記事 自動生成スクリプト（Mac Native / OpenRouter使用）
Usage:
  python3 openclaw_gen.py           # 未カバーエリアから1記事自動生成
  python3 openclaw_gen.py --count 2 # 2記事生成
  python3 openclaw_gen.py --dry-run # 確認のみ

API: OpenRouter (無料) - Groq と競合しない
"""
import os
import sys
import json
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

SITE_DIR = Path(__file__).parent / "site"
CONTENT_DIR = SITE_DIR / "content" / "post"
LOG_FILE = Path(__file__).parent / "openclaw_gen.log"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2", "")
GROQ_KEYS = [k for k in [GROQ_API_KEY, GROQ_API_KEY_2] if k]  # 有効なキーのリスト
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# 無料モデル優先順（フォールバックあり） ※ 2026-03-29 更新
FREE_MODELS = [
    "google/gemma-3n-e4b-it:free",                   # 動作確認済み（最優先）
    "google/gemma-3-27b-it:free",                     # Google Gemma 27B
    "meta-llama/llama-3.3-70b-instruct:free",         # Llama 3.3
    "nousresearch/hermes-3-llama-3.1-405b:free",      # Hermes 405B
]
# Groq フォールバックモデル（無料枠あり）
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "gemma2-9b-it",
]

# ──────────────────────────────────────────────
# 対象エリア一覧（都道府県 × 主要都市）
# 未カバーエリアをここから自動選出
# ──────────────────────────────────────────────
TARGET_AREAS = [
    # 首都圏
    {"pref": "東京都", "city": "渋谷区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "新宿区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "港区",      "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "文京区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "台東区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "墨田区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "江東区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "品川区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "目黒区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "大田区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "世田谷区",  "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "中野区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "杉並区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "豊島区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "北区",      "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "板橋区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "練馬区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "足立区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "葛飾区",    "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "東京都", "city": "江戸川区",  "pref_en": "tokyo",   "type": "マンション"},
    {"pref": "神奈川県","city": "横浜市青葉区","pref_en": "kanagawa","type": "マンション"},
    {"pref": "神奈川県","city": "横浜市中区", "pref_en": "kanagawa","type": "マンション"},
    {"pref": "神奈川県","city": "川崎市幸区", "pref_en": "kanagawa","type": "マンション"},
    {"pref": "神奈川県","city": "藤沢市",    "pref_en": "kanagawa","type": "一戸建て"},
    {"pref": "神奈川県","city": "鎌倉市",    "pref_en": "kanagawa","type": "一戸建て"},
    {"pref": "埼玉県", "city": "さいたま市浦和区","pref_en": "saitama","type": "マンション"},
    {"pref": "埼玉県", "city": "川口市",    "pref_en": "saitama", "type": "マンション"},
    {"pref": "千葉県", "city": "千葉市中央区","pref_en": "chiba",  "type": "マンション"},
    {"pref": "千葉県", "city": "船橋市",    "pref_en": "chiba",   "type": "マンション"},
    # 関西
    {"pref": "大阪府", "city": "北区",      "pref_en": "osaka",   "type": "マンション"},
    {"pref": "大阪府", "city": "中央区",    "pref_en": "osaka",   "type": "マンション"},
    {"pref": "大阪府", "city": "天王寺区",  "pref_en": "osaka",   "type": "マンション"},
    {"pref": "大阪府", "city": "浪速区",    "pref_en": "osaka",   "type": "マンション"},
    {"pref": "大阪府", "city": "西区",      "pref_en": "osaka",   "type": "マンション"},
    {"pref": "京都府", "city": "中京区",    "pref_en": "kyoto",   "type": "マンション"},
    {"pref": "京都府", "city": "上京区",    "pref_en": "kyoto",   "type": "マンション"},
    {"pref": "兵庫県", "city": "神戸市中央区","pref_en": "hyogo",  "type": "マンション"},
    {"pref": "兵庫県", "city": "西宮市",    "pref_en": "hyogo",   "type": "一戸建て"},
    # 中部
    {"pref": "愛知県", "city": "名古屋市西区","pref_en": "aichi",  "type": "マンション"},
    {"pref": "愛知県", "city": "名古屋市守山区","pref_en": "aichi", "type": "一戸建て"},
    {"pref": "静岡県", "city": "静岡市葵区", "pref_en": "shizuoka","type": "マンション"},
    {"pref": "静岡県", "city": "浜松市中区", "pref_en": "shizuoka","type": "マンション"},
    # 九州
    {"pref": "福岡県", "city": "福岡市中央区","pref_en": "fukuoka","type": "マンション"},
    {"pref": "福岡県", "city": "福岡市早良区","pref_en": "fukuoka","type": "マンション"},
    {"pref": "福岡県", "city": "北九州市小倉北区","pref_en": "fukuoka","type": "マンション"},
    {"pref": "熊本県", "city": "熊本市中央区","pref_en": "kumamoto","type": "マンション"},
    # 東北
    {"pref": "宮城県", "city": "仙台市青葉区","pref_en": "miyagi", "type": "マンション"},
    {"pref": "宮城県", "city": "仙台市泉区",  "pref_en": "miyagi", "type": "一戸建て"},
    # 北陸
    {"pref": "石川県", "city": "金沢市",     "pref_en": "ishikawa","type": "マンション"},
    {"pref": "富山県", "city": "富山市",     "pref_en": "toyama",  "type": "一戸建て"},
    # ガイド記事
    {"pref": "全国",   "city": "住宅ローン減税2024",  "pref_en": "guide", "type": "guide",
     "article_type": "guide", "theme": "住宅ローン減税の最新ルールと賢い使い方"},
    {"pref": "全国",   "city": "マンション管理費の相場", "pref_en": "guide","type": "guide",
     "article_type": "guide", "theme": "マンション管理費・修繕積立金の全国平均と選び方"},
    {"pref": "全国",   "city": "不動産投資利回り計算", "pref_en": "guide", "type": "guide",
     "article_type": "guide", "theme": "不動産投資の利回り計算と失敗しない物件選び"},
    {"pref": "全国",   "city": "固定資産税の計算方法", "pref_en": "guide", "type": "guide",
     "article_type": "guide", "theme": "固定資産税の仕組みと節税テクニック2026年版"},
]


def slugify(text: str) -> str:
    """簡易スラッグ生成"""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_]+', '-', text)
    return text[:40].strip('-')


def get_covered_slugs() -> set:
    """既存記事のタイトル部分（エリア）を収集"""
    slugs = set()
    for f in CONTENT_DIR.glob("*.md"):
        # ファイル名からタイムスタンプ部分を除去して比較
        name = f.stem
        slugs.add(name)
    return slugs


def pick_uncovered_areas(count: int = 1) -> list:
    """まだ記事がないエリアを選択"""
    covered = get_covered_slugs()
    picks = []
    for area in TARGET_AREAS:
        # 既存ファイル名に area の pref+city が含まれるか確認
        pref_slug = slugify(area["pref"].replace("都", "").replace("府", "").replace("県", ""))
        city_slug = slugify(area["city"])
        already_covered = any(
            (pref_slug in s and city_slug in s) for s in covered
        )
        if not already_covered:
            picks.append(area)
            if len(picks) >= count:
                break
    return picks


def call_openrouter(prompt: str, model_idx: int = 0, _retry: int = 0) -> str:
    """OpenRouter API呼び出し（無料モデル・429時はウェイト→リトライ・フォールバックあり）"""
    import urllib.request
    import urllib.error
    import time

    model = FREE_MODELS[model_idx % len(FREE_MODELS)]
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2500,
    }).encode()

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://realestate.tacky-consulting.com",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            log.info(f"OpenRouter success: {model}")
            return content
    except urllib.error.HTTPError as e:
        log.warning(f"OpenRouter model {model} failed (HTTP {e.code}): {e}")
        if model_idx + 1 < len(FREE_MODELS):
            log.info(f"Falling back to next OpenRouter model...")
            if e.code == 429:
                time.sleep(3)
            return call_openrouter(prompt, model_idx + 1, 0)
        # OpenRouter全滅 → Groqへ
        log.info("All OpenRouter models failed, trying Groq...")
        return call_groq(prompt)
    except Exception as e:
        log.warning(f"OpenRouter model {model} error: {e}")
        if model_idx + 1 < len(FREE_MODELS):
            log.info(f"Falling back to next OpenRouter model...")
            return call_openrouter(prompt, model_idx + 1, 0)
        log.info("All OpenRouter models failed, trying Groq...")
        return call_groq(prompt)


def call_groq(prompt: str, model_idx: int = 0, key_idx: int = 0) -> str:
    """Groq API呼び出し（複数キーローテーション・全モデルフォールバックあり）"""
    import urllib.request
    import urllib.error
    import time

    if not GROQ_KEYS:
        raise RuntimeError("GROQ_API_KEY not set")

    model = GROQ_MODELS[model_idx % len(GROQ_MODELS)]
    api_key = GROQ_KEYS[key_idx % len(GROQ_KEYS)]
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2500,
    }).encode()

    req = urllib.request.Request(
        GROQ_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            log.info(f"Groq success: {model} (key#{key_idx+1})")
            return content
    except urllib.error.HTTPError as e:
        log.warning(f"Groq model {model} key#{key_idx+1} failed (HTTP {e.code}): {e}")
        if e.code == 429:
            # 別キーへ切り替え
            next_key = key_idx + 1
            if next_key < len(GROQ_KEYS):
                log.info(f"Switching to Groq key#{next_key+1}...")
                time.sleep(2)
                return call_groq(prompt, model_idx, next_key)
            # キー全滅 → 次モデルへ
            if model_idx + 1 < len(GROQ_MODELS):
                log.info(f"All keys exhausted for {model}, trying next model...")
                time.sleep(5)
                return call_groq(prompt, model_idx + 1, 0)
        elif model_idx + 1 < len(GROQ_MODELS):
            return call_groq(prompt, model_idx + 1, 0)
        raise
    except Exception as e:
        log.warning(f"Groq model {model} error: {e}")
        if model_idx + 1 < len(GROQ_MODELS):
            return call_groq(prompt, model_idx + 1, 0)
        raise


def fetch_unsplash_image(area: dict) -> dict | None:
    """Unsplashからエリアに合う画像を取得"""
    import urllib.request
    import urllib.parse

    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        return None

    pref_en = area.get("pref_en", "japan")
    article_type = area.get("article_type", "area")

    # 検索クエリ: エリア記事は都市名、ガイド記事は不動産テーマ
    if article_type == "guide":
        queries = ["Japan real estate", "Japan property", "Japan city"]
    else:
        city = area.get("city", "")
        prop_type = area.get("type", "")
        # 物件タイプ別クエリ
        if prop_type == "一戸建て":
            queries = [f"{pref_en} Japan house", "Japan suburban house", "Japan neighborhood"]
        else:
            queries = [f"{pref_en} Japan city", "Japan apartment building", "Japan urban"]

    for query in queries:
        try:
            params = urllib.parse.urlencode({
                "query": query,
                "per_page": 3,
                "orientation": "landscape",
            })
            req = urllib.request.Request(
                f"https://api.unsplash.com/search/photos?{params}",
                headers={"Authorization": f"Client-ID {access_key}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                results = data.get("results", [])
                if results:
                    photo = results[0]
                    # Unsplash利用規約: ダウンロードトリガー
                    dl_req = urllib.request.Request(
                        photo["links"]["download_location"],
                        headers={"Authorization": f"Client-ID {access_key}"},
                    )
                    urllib.request.urlopen(dl_req, timeout=10).close()
                    return {
                        "url": photo["urls"]["regular"],
                        "photographer": photo["user"]["name"],
                        "photographer_url": photo["user"]["links"]["html"],
                    }
        except Exception as e:
            log.warning(f"Unsplash fetch failed for '{query}': {e}")

    return None


def generate_article(area: dict) -> str:
    """OpenRouterでMarkdown記事を生成"""
    pref = area["pref"]
    city = area["city"]
    prop_type = area["type"]
    theme = area.get("theme", f"{pref}{city}の{prop_type}相場")
    article_type = area.get("article_type", "area")

    if article_type == "guide":
        prompt = f"""あなたは日本の不動産専門メディア「OpenClaw（不動産価格調査センター）」のライターです。

次のテーマでSEO最適化された解説記事をMarkdown形式で書いてください：
テーマ：{theme}

【記事の条件】
- 文字数：1500〜2000字
- 構成：H2見出し4〜5個、各セクション2〜4段落
- 数字・データを積極的に使う（例：全国平均〇〇円/月）
- 「だから何？」「読者にとってのメリット」を常に意識
- 最後に「まとめ」セクションと「シミュレーターで計算する」CTAを入れる
- Front matterは不要（本文のみ）

【禁止事項】
- 「〇〇です」の羅列（読み飽きる）
- 根拠なしの断定
- 業者目線のセールス文章

記事の冒頭はH1見出しから始めること（# タイトル）"""
    else:
        prompt = f"""あなたは日本の不動産専門メディア「OpenClaw（不動産価格調査センター）」のライターです。

{pref}{city}の{prop_type}相場に関するSEO記事をMarkdown形式で書いてください。

【記事構成】
# {pref}{city}の{prop_type}相場2026年版｜最新価格と将来予測

## エリア概要
- アクセス・生活利便性

## 最新{prop_type}相場（2024〜2026年）
- 坪単価・㎡単価の目安（推定値でOK、出典：国土交通省不動産価格指数を参考）
- 築年数別の価格帯（新築・10年・20年）

## 価格推移と将来予測
- 直近3年のトレンド
- 今後の見通し（再開発・人口動態を踏まえて）

## 投資・購入時のポイント
- 注意点2〜3個（具体的に）

## よくある質問
- Q&A形式で3問

## まとめ
- 結論を3行で

【条件】
- 具体的な数字を必ず入れる（実際のデータがなければ国土交通省の統計から推定）
- 読者目線で「だから何？」を常に意識
- Front matterは不要（本文のみ）
- 文字数：1800〜2500字"""

    return call_openrouter(prompt)


def save_article(area: dict, content: str, image: dict | None = None) -> Path:
    """記事をHugoのMarkdownファイルとして保存"""
    now = datetime.now()
    pref = area["pref"]
    city = area["city"]
    prop_type = area["type"]
    pref_en = area["pref_en"]
    article_type = area.get("article_type", "area")

    # タイトルとスラッグ生成
    if article_type == "guide":
        theme = area.get("theme", city)
        title = theme
        slug_base = slugify(city)
    else:
        title = f"{pref}{city}の{prop_type}相場2026年版｜最新価格と将来予測"
        slug_base = slugify(f"{pref}{city}{prop_type}")

    slug = f"{slug_base}-{now.strftime('%Y%m%d%H%M')}"
    filename = CONTENT_DIR / f"{slug}.md"

    # Front matter組み立て
    tags = [pref, city, "不動産価格", "相場"]
    if article_type != "guide":
        tags.append(prop_type)

    image_lines = ""
    if image:
        image_lines = (
            f'\nimage: "{image["url"]}"\n'
            f'image_credit_name: "{image["photographer"]}"\n'
            f'image_credit_url: "{image["photographer_url"]}"'
        )

    frontmatter = f"""---
title: "{title}"
date: {now.strftime('%Y-%m-%dT%H:%M:%S')}+09:00
slug: "{slug}"
area: "{pref}{city}"
prefecture: "{pref}"
property_type: "{prop_type}"
description: "{pref}{city}の{prop_type}相場を解説。最新データと将来予測。"
keywords: {json.dumps(tags, ensure_ascii=False)}
article_type: "{article_type}"
categories: ["{('guide' if article_type == 'guide' else 'market-data')}"]
prefectures: ["{pref_en}"]{image_lines}
draft: false
---

"""
    # H1見出しが本文にない場合は追加
    if not content.startswith("#"):
        content = f"# {title}\n\n{content}"

    filename.write_text(frontmatter + content, encoding="utf-8")
    log.info(f"Saved: {filename.name}")
    return filename


def build_and_deploy(dry_run: bool = False):
    """Hugoビルド + git push（GitHub Pages自動デプロイ）"""
    import subprocess
    site_dir = SITE_DIR
    repo_dir = Path(__file__).parent

    if dry_run:
        log.info("[DRY RUN] Skipped build/deploy")
        return

    log.info("Building Hugo site...")
    hugo_bin = "/opt/homebrew/bin/hugo"
    result = subprocess.run(
        [hugo_bin, "--minify", "--destination", str(repo_dir / "docs")],
        cwd=str(site_dir), capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error(f"Hugo build failed: {result.stderr}")
        return

    log.info("Committing and pushing...")
    subprocess.run(["git", "add", "site/content/post/", "docs/"], cwd=str(repo_dir))
    subprocess.run([
        "git", "commit", "-m",
        f"feat: auto-generate {datetime.now().strftime('%Y-%m-%d')} article(s)"
    ], cwd=str(repo_dir))
    # push前にpull --rebase でリモートの差分を取り込む
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=str(repo_dir))
    subprocess.run(["git", "push", "origin", "main"], cwd=str(repo_dir))
    log.info("Deployed to GitHub Pages ✓")


def log_run(areas: list, dry_run: bool):
    """実行ログ記録"""
    with open(LOG_FILE, "a") as f:
        for area in areas:
            f.write(f"{datetime.now().isoformat()} | {'DRY' if dry_run else 'OK'} | "
                    f"{area['pref']}{area['city']} {area['type']}\n")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw 不動産記事自動生成")
    parser.add_argument("--count", type=int, default=1, help="生成記事数（デフォルト1）")
    parser.add_argument("--dry-run", action="store_true", help="確認のみ（保存・デプロイしない）")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY:
        log.error("OPENROUTER_API_KEY が設定されていません。.envを確認してください。")
        sys.exit(1)

    # 未カバーエリアを選出
    areas = pick_uncovered_areas(args.count)
    if not areas:
        log.info("✅ すべてのエリアが既にカバーされています。")
        return

    area_names = [a["pref"] + a["city"] for a in areas]
    log.info(f"生成対象: {area_names}")

    saved_files = []
    for area in areas:
        log.info(f"=== 記事生成中: {area['pref']}{area['city']} ===")
        if args.dry_run:
            log.info(f"[DRY RUN] Would generate: {area['pref']}{area['city']} {area['type']}")
            continue
        try:
            content = generate_article(area)
            image = fetch_unsplash_image(area)
            if image:
                log.info(f"Unsplash image: {image['photographer']}")
            saved = save_article(area, content, image)
            saved_files.append(saved)
            log.info(f"✓ {area['pref']}{area['city']} 記事完了")
        except Exception as e:
            log.error(f"記事生成失敗: {area} — {e}")

    if saved_files and not args.dry_run:
        build_and_deploy(dry_run=args.dry_run)

    log_run(areas, args.dry_run)
    log.info(f"=== 完了: {len(saved_files)}記事生成 ===")


if __name__ == "__main__":
    main()
