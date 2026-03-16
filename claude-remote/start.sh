#!/bin/bash
# Claude Remote Control サーバー起動スクリプト
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# .env 読み込み
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Claude バイナリパスを自動検出
if [ -z "$CLAUDE_BIN" ]; then
  LATEST=$(ls -d "$HOME/Library/Application Support/Claude/claude-code"/*/claude 2>/dev/null | sort -V | tail -1)
  if [ -n "$LATEST" ]; then
    export CLAUDE_BIN="$LATEST"
    echo "🔍 Claude detected: $CLAUDE_BIN"
  else
    echo "❌ Claude Code CLI が見つかりません"
    exit 1
  fi
fi

# 依存関係インストール
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "📦 Installing dependencies..."
  pip3 install -r requirements.txt -q
fi

echo "🚀 Starting Claude Remote Control on port ${PORT:-9999}"
echo "   QR code → http://localhost:${PORT:-9999}/qr"
python3 server.py
