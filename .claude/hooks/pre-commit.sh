#!/bin/bash
# Pre-commit hook: .env や機密情報のコミットを防ぐ

FILES=$(git diff --cached --name-only 2>/dev/null)

# .env ファイルのコミットを禁止
if echo "$FILES" | grep -qE "^\.env$|/\.env$"; then
  echo "❌ .env ファイルはコミットできません（機密情報を含む可能性）"
  exit 1
fi

# APIキーのパターンを検出
if git diff --cached 2>/dev/null | grep -qE "(sk-|gsk_|ghp_)[a-zA-Z0-9]{20,}"; then
  echo "❌ APIキーらしき文字列を検出しました。コミット前に確認してください。"
  exit 1
fi

echo "✅ Pre-commit チェック通過"
exit 0
