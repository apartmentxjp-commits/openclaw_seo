#!/bin/bash
# Post-tool-use hook: バックエンドファイル変更後に Docker rebuild を促す

TOOL="$1"
FILE="$2"

if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
  if echo "$FILE" | grep -q "backend/"; then
    echo ""
    echo "⚠️  バックエンドファイルを変更しました。"
    echo "   変更を反映するには Docker rebuild が必要です:"
    echo "   cd .claude/worktrees/jovial-rosalind && docker compose up -d --build backend"
    echo ""
  fi
fi
