#!/usr/bin/env python3
"""
内部リンク自動挿入スクリプト（用語集 ↔ 記事）

機能：
- site/content/post/*.md の記事本文に用語集用語が出現したら
  [用語](/glossary/reading/) 形式のリンクを最初の1回だけ挿入する
- front matter / code block / 既存リンク内 は処理しない
- ドライラン（--dry-run）で実際に変更せずに確認できる

Usage:
  python3 scripts/add_internal_links.py           # 実際に変更
  python3 scripts/add_internal_links.py --dry-run # ドライラン
"""

import os
import re
import sys
import glob

# ── 設定 ──────────────────────────────────────────────────────────────────────
POST_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "content", "post")
GLOSSARY_DIR = os.path.join(os.path.dirname(__file__), "..", "site", "content", "glossary")
DRY_RUN = "--dry-run" in sys.argv

# ── 用語集を読み込む ──────────────────────────────────────────────────────────
def load_glossary_terms():
    """glossary/*.md から (term, reading) のリストを返す（長い用語を先に）"""
    terms = []
    for fpath in glob.glob(os.path.join(GLOSSARY_DIR, "*.md")):
        if "_index" in fpath:
            continue
        with open(fpath, encoding="utf-8") as f:
            content = f.read()

        # front matter から term と reading を抽出
        term_m = re.search(r'^term:\s*"([^"]+)"', content, re.MULTILINE)
        reading_m = re.search(r'^reading:\s*"([^"]+)"', content, re.MULTILINE)
        if term_m and reading_m:
            terms.append((term_m.group(1), reading_m.group(1)))

    # 長い用語から処理（「修繕積立金」より先に「積立金」が置換されないように）
    terms.sort(key=lambda x: -len(x[0]))
    return terms


# ── 記事本文にリンクを挿入 ────────────────────────────────────────────────────
def insert_links(content: str, terms: list) -> str:
    """
    front matter と script タグを除いた本文に対して、
    各用語の最初の出現箇所にのみリンクを挿入する。
    """
    # front matter の終わり位置を特定
    fm_end = 0
    if content.startswith("---"):
        second = content.find("---", 3)
        if second != -1:
            fm_end = second + 3

    front_matter = content[:fm_end]
    body = content[fm_end:]

    # <script> タグ内はリンク挿入しない → プレースホルダーに置換
    script_blocks = []
    def extract_script(m):
        script_blocks.append(m.group(0))
        return f"__SCRIPT_{len(script_blocks)-1}__"
    body_no_script = re.sub(r'<script[\s\S]*?</script>', extract_script, body)

    # コードブロック（``` ... ```）を保護
    code_blocks = []
    def extract_code(m):
        code_blocks.append(m.group(0))
        return f"__CODE_{len(code_blocks)-1}__"
    body_protected = re.sub(r'```[\s\S]*?```', extract_code, body_no_script)

    # 既存のリンク `[text](url)` 内にある用語は置換しない → 保護
    existing_links = []
    def extract_link(m):
        existing_links.append(m.group(0))
        return f"__LINK_{len(existing_links)-1}__"
    body_protected = re.sub(r'\[.*?\]\(.*?\)', extract_link, body_protected)

    # 各用語を置換（最初の1回だけ）
    changed = False
    for term, reading in terms:
        link = f"[{term}](/glossary/{reading}/)"
        # 既にリンクになっているか確認（用語が __LINK__ で保護済みなら skip）
        # 用語が本文に存在するかチェック（前後が日本語・英数字・記号でないこと）
        # 簡易版：単純に最初の出現だけ置換
        new_body = body_protected.replace(term, link, 1)
        if new_body != body_protected:
            body_protected = new_body
            changed = True

    if not changed:
        return content  # 変更なし

    # 保護したブロックを元に戻す
    for i, block in enumerate(existing_links):
        body_protected = body_protected.replace(f"__LINK_{i}__", block)
    for i, block in enumerate(code_blocks):
        body_protected = body_protected.replace(f"__CODE_{i}__", block)
    for i, block in enumerate(script_blocks):
        body_protected = body_protected.replace(f"__SCRIPT_{i}__", block)

    return front_matter + body_protected


def process_article(fpath: str, terms: list) -> bool:
    """記事ファイルを処理し、変更があれば上書き保存する"""
    with open(fpath, encoding="utf-8") as f:
        original = f.read()

    updated = insert_links(original, terms)
    if updated == original:
        return False

    if not DRY_RUN:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(updated)
    return True


def main():
    terms = load_glossary_terms()
    print(f"📚 Loaded {len(terms)} glossary terms")
    if DRY_RUN:
        print("   [DRY RUN mode — no files will be changed]\n")
    else:
        print()

    post_files = sorted(glob.glob(os.path.join(POST_DIR, "*.md")))
    # ツール系ファイルはスキップ
    skip_files = {"loan-calculator.md", "yield-calculator.md", "rent-estimator.md",
                  "price-prediction.md", "sale-simulator.md"}

    updated_count = 0
    for fpath in post_files:
        fname = os.path.basename(fpath)
        if fname in skip_files:
            continue
        changed = process_article(fpath, terms)
        if changed:
            print(f"  ✅ {'[DRY] ' if DRY_RUN else ''}Updated: {fname}")
            updated_count += 1

    print(f"\n✅ Done! Updated {updated_count} / {len(post_files)} articles")
    if DRY_RUN:
        print("   Run without --dry-run to apply changes")


if __name__ == "__main__":
    main()
