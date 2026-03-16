"""
claude-remote — Claude Code CLI をHTTP経由でリモートコントロールするサーバー

起動: python server.py
接続: POST http://localhost:9999/instruct

使用例:
  curl -X POST http://localhost:9999/instruct \\
       -H "Authorization: Bearer <CLAUDE_REMOTE_SECRET>" \\
       -H "Content-Type: application/json" \\
       -d '{"instruction": "src/app/page.tsx を読んで概要を教えて", "dir": "/Users/Mrt0309/Desktop/openclaw_seo"}'
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

# ── 設定 ─────────────────────────────────────────────────────────────
CLAUDE_BIN = os.getenv(
    "CLAUDE_BIN",
    str(Path.home() / "Library/Application Support/Claude/claude-code/2.1.51/claude"),
)
SECRET = os.getenv("CLAUDE_REMOTE_SECRET", "")
DEFAULT_DIR = os.getenv("DEFAULT_PROJECT_DIR", str(Path.home() / "Desktop/openclaw_seo"))
PORT = int(os.getenv("PORT", "9999"))

app = FastAPI(title="Claude Remote Control", version="1.0.0")


def _verify(authorization: str | None):
    if not SECRET:
        raise HTTPException(503, "CLAUDE_REMOTE_SECRET が設定されていません")
    if authorization != f"Bearer {SECRET}":
        raise HTTPException(401, "認証エラー")


# ── POST /instruct  (レスポンスを一括返却) ────────────────────────────
@app.post("/instruct")
async def instruct(body: dict, authorization: str = Header(None)):
    """
    Claude Code CLI に指示を送り、実行結果を返す。

    Body:
      instruction: str   — Claude への指示（自然言語）
      dir:         str   — 作業ディレクトリ（省略時は DEFAULT_PROJECT_DIR）
      model:       str   — モデル名（省略時は claude-sonnet-4-6）
      tools:       list  — 許可ツール（省略時は全ツール許可）
    """
    _verify(authorization)

    instruction = body.get("instruction", "").strip()
    if not instruction:
        raise HTTPException(400, "instruction が必要です")

    work_dir = body.get("dir", DEFAULT_DIR)
    model = body.get("model", "claude-sonnet-4-6")
    tools = body.get("tools", [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task"
    ])

    cmd = [
        CLAUDE_BIN,
        "-p", instruction,
        "--model", model,
        "--output-format", "text",
        "--permission-mode", "acceptEdits",
        "--allowedTools", ",".join(tools),
    ]

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "HOME": str(Path.home())},
            ),
        )
        return {
            "ok": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() or None,
            "instruction": instruction,
            "dir": work_dir,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "タイムアウト（300秒）")
    except FileNotFoundError:
        raise HTTPException(500, f"Claude CLIが見つかりません: {CLAUDE_BIN}")


# ── POST /instruct/stream  (出力をリアルタイムストリーミング) ──────────
@app.post("/instruct/stream")
async def instruct_stream(body: dict, authorization: str = Header(None)):
    """
    Claude Code CLI の出力をServer-Sent Eventsでリアルタイム配信。
    """
    _verify(authorization)

    instruction = body.get("instruction", "").strip()
    if not instruction:
        raise HTTPException(400, "instruction が必要です")

    work_dir = body.get("dir", DEFAULT_DIR)
    model = body.get("model", "claude-sonnet-4-6")
    tools = body.get("tools", [
        "Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task"
    ])

    cmd = [
        CLAUDE_BIN,
        "-p", instruction,
        "--model", model,
        "--output-format", "text",
        "--permission-mode", "acceptEdits",
        "--allowedTools", ",".join(tools),
    ]

    async def generate():
        yield f"data: {json.dumps({'type':'start','instruction':instruction,'dir':work_dir}, ensure_ascii=False)}\n\n"
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=work_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "HOME": str(Path.home())},
        )
        async for line in proc.stdout:
            text = line.decode("utf-8", errors="replace")
            yield f"data: {json.dumps({'type':'output','text':text}, ensure_ascii=False)}\n\n"
        await proc.wait()
        yield f"data: {json.dumps({'type':'done','returncode':proc.returncode}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /status ───────────────────────────────────────────────────────
@app.get("/status")
async def status():
    return {
        "claude_bin": CLAUDE_BIN,
        "claude_found": Path(CLAUDE_BIN).exists(),
        "default_dir": DEFAULT_DIR,
        "secret_set": bool(SECRET),
        "port": PORT,
    }


# ── GET /qr  (QRコード表示) ────────────────────────────────────────────
@app.get("/qr", response_class=None)
async def show_qr():
    """ローカルIPのWebhook URLをQRコードで表示"""
    import socket
    import urllib.request

    # ローカルIPを取得
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    url = f"http://{local_ip}:{PORT}/instruct"
    qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>Claude Remote QR</title>
<style>
  body {{ background:#0d0d0d; color:#e5e5e5; font-family:monospace;
          display:flex; flex-direction:column; align-items:center;
          justify-content:center; min-height:100vh; margin:0; gap:20px; }}
  .box {{ background:#1a1a1a; border:1px solid #333; border-radius:12px;
          padding:32px; text-align:center; max-width:400px; }}
  h1 {{ color:#8b5cf6; font-size:1.1rem; margin:0 0 8px; }}
  .url {{ color:#60a5fa; font-size:0.8rem; word-break:break-all;
          background:#111; padding:8px 12px; border-radius:6px; margin:12px 0; }}
  .token {{ color:#f59e0b; font-size:0.75rem; background:#111;
            padding:8px 12px; border-radius:6px; margin:4px 0; }}
  img {{ border-radius:8px; background:white; padding:8px; }}
  .hint {{ color:#6b7280; font-size:0.7rem; margin-top:16px; }}
</style>
</head>
<body>
<div class="box">
  <h1>🤖 Claude Remote Control</h1>
  <img src="{qr_api}" width="200" height="200" alt="QR Code" />
  <div class="url">{url}</div>
  <div class="token">Bearer: {'*' * 8 + SECRET[-8:] if len(SECRET) > 8 else '未設定'}</div>
  <div class="hint">このQRをスマホで読み取るとエンドポイントURLを取得できます</div>
</div>
</body>
</html>"""

    from fastapi.responses import HTMLResponse
    return HTMLResponse(html)


if __name__ == "__main__":
    print(f"🤖 Claude Remote Control starting on port {PORT}")
    print(f"   Claude bin : {CLAUDE_BIN}")
    print(f"   Default dir: {DEFAULT_DIR}")
    print(f"   Secret set : {'✅' if SECRET else '❌ CLAUDE_REMOTE_SECRET を設定してください'}")
    print(f"   QR code    : http://localhost:{PORT}/qr")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
