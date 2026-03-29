"""
Thoughts Router — エージェント思考の SSE ストリーミングエンドポイント
"""

import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from agents.thoughts import thought_stream, get_snapshot

router = APIRouter()


@router.get("/stream")
async def stream_thoughts():
    """
    SSE エンドポイント: エージェントの思考をリアルタイムでストリーミング
    EventSource で接続すると、各エージェントの思考が data: JSON の形式で送られる
    """
    async def generate():
        async for entry in thought_stream():
            yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # nginx バッファリング無効
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/snapshot")
async def snapshot():
    """全エージェントの現在状態スナップショット（REST）"""
    return get_snapshot()
