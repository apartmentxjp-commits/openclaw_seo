"""
Thought Bus — エージェントの思考をリアルタイムで全クライアントに配信する
SSE（Server-Sent Events）バックボーン
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator

# ── エージェントプロファイル ─────────────────────────────────────────
AGENT_PROFILES = {
    "writer": {
        "name": "WriterAgent",
        "role": "記事執筆担当",
        "color": "#6366f1",
        "desk": "top-left",
    },
    "scheduler": {
        "name": "Scheduler",
        "role": "スケジュール管理",
        "color": "#f59e0b",
        "desk": "top-right",
    },
    "analyzer": {
        "name": "AnalyticsAgent",
        "role": "アクセス分析",
        "color": "#8b5cf6",
        "desk": "bottom-left",
    },
    "optimizer": {
        "name": "OptimizerAgent",
        "role": "記事最適化",
        "color": "#10b981",
        "desk": "bottom-right",
    },
}

# ── 現在の状態（エージェントごと最新1件）─────────────────────────────
_state: dict[str, dict] = {
    agent: {
        "agent": agent,
        "thought": "起動待機中...",
        "status": "idle",   # idle | thinking | working | success | error | stuck
        "detail": None,
        "ts": datetime.utcnow().isoformat(),
    }
    for agent in AGENT_PROFILES
}

# ── 接続中の SSE クライアント ──────────────────────────────────────
_subscribers: list[asyncio.Queue] = []

# ── 最近のアクティビティログ（全エージェント合算、最大200件）────────
_activity_log: list[dict] = []
_MAX_LOG = 200


async def emit_thought(
    agent: str,
    thought: str,
    status: str = "thinking",
    detail: str | None = None,
):
    """
    エージェントが「今何を考えているか」を emit する。
    status: idle | thinking | working | success | error | stuck
    """
    entry = {
        "agent": agent,
        "thought": thought,
        "status": status,
        "detail": detail,
        "ts": datetime.utcnow().isoformat(),
    }

    # 最新状態を更新
    _state[agent] = entry

    # アクティビティログに追記
    _activity_log.append(entry)
    if len(_activity_log) > _MAX_LOG:
        _activity_log.pop(0)

    # 全接続クライアントにブロードキャスト
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


async def thought_stream() -> AsyncIterator[dict]:
    """SSE エンドポイント用の無限ジェネレーター"""
    q: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)
    _subscribers.append(q)

    try:
        # 接続時に現在の状態をすべて送信
        for entry in _state.values():
            yield entry

        # 新しい思考をストリーミング
        while True:
            try:
                entry = await asyncio.wait_for(q.get(), timeout=15.0)
                yield entry
            except asyncio.TimeoutError:
                # ハートビート（接続維持）
                yield {"ping": True, "ts": datetime.utcnow().isoformat()}
    finally:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass


def get_snapshot() -> dict:
    """現在の全エージェント状態スナップショット（REST用）"""
    return {
        "agents": _state,
        "profiles": AGENT_PROFILES,
        "recent_activity": _activity_log[-50:],
        "connected_clients": len(_subscribers),
    }
