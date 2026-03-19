#!/bin/bash
# deploy.sh — サムネイル追加 → Hugoビルド → Git push を一括実行
# 使い方: bash scripts/deploy.sh
# または: bash scripts/deploy.sh "コミットメッセージ"

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "🖼️  Step 1: サムネイル自動追加..."
python3 scripts/add_thumbnails.py

echo "🔗 Step 1b: 内部リンク（用語集↔記事）自動追加..."
python3 scripts/add_internal_links.py

echo "🔨 Step 2: Hugo ビルド..."
cd site && hugo --minify --destination ../docs
cd "$ROOT"

echo "📦 Step 3: Git コミット & プッシュ..."
MSG="${1:-Auto-publish: $(date '+%Y-%m-%d %H:%M')}"

# リモートの変更を取り込む
git stash 2>/dev/null || true
git pull --rebase origin main 2>/dev/null || true
git stash pop 2>/dev/null || true

git add docs/ site/content/ site/static/ site/layouts/ scripts/ 2>/dev/null || git add docs/ site/content/
git commit -m "$MSG" || echo "Nothing to commit."
git push origin main

echo "✅ デプロイ完了！"
