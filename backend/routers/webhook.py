"""
Webhook Router — 外部サービスからエージェントへ指示を送るエンドポイント

認証: Authorization: Bearer <WEBHOOK_SECRET>

対応アクション:
  generate_article  — 記事1件生成（topic省略時は自動選択）
  generate_batch    — 複数記事まとめて生成
  optimize          — 最適化サイクル実行
  emit_thought      — オフィス画面にカスタムメッセージ表示
  status            — 現在のエージェント状態確認

使用例:
  curl -X POST https://your-domain/api/webhook \\
       -H "Authorization: Bearer <WEBHOOK_SECRET>" \\
       -H "Content-Type: application/json" \\
       -d '{"action": "generate_article", "topic": {"prefecture": "東京都", "area": "渋谷区", "property_type": "マンション"}}'
"""

import os
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import AgentLog
from agents.writer_agent import WriterAgent, ARTICLE_TOPICS
from agents.thoughts import emit_thought

router = APIRouter()

_topic_index = 0


def _next_topic() -> dict:
    global _topic_index
    topic = ARTICLE_TOPICS[_topic_index % len(ARTICLE_TOPICS)]
    _topic_index += 1
    return topic


def _verify_token(authorization: str = Header(None)) -> None:
    secret = os.getenv("WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="WEBHOOK_SECRET が設定されていません")
    if authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="認証エラー: トークンが正しくありません")


async def _bg_generate_article(topic: dict, db: AsyncSession):
    log = AgentLog(
        agent_name="writer_agent",
        task_type="generate_article",
        status="running",
        input_summary=f"[webhook] {topic['prefecture']} {topic['area']} {topic['property_type']}",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    from models import Article
    try:
        writer = WriterAgent()
        result = await writer.generate_article(**topic)

        article = Article(
            slug=result["slug"],
            title=result["title"],
            area=result["area"],
            prefecture=result["prefecture"],
            property_type=result["property_type"],
            content=result["content"],
            excerpt=result.get("excerpt"),
            meta_title=result.get("meta_title"),
            meta_description=result.get("meta_description"),
            keywords=result.get("keywords"),
            structured_data=result.get("structured_data"),
            status="published",
            generated_by="gemini",
            duration_ms=result.get("duration_ms"),
        )
        db.add(article)
        await db.commit()
        log.status = "success"
        log.output_summary = f"[webhook] {result['title']}"
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)

    await db.commit()


async def _bg_run_optimization(db: AsyncSession):
    from agents.optimizer_agent import OptimizerAgent
    optimizer = OptimizerAgent()
    await optimizer.run_optimization_cycle(db, limit=3)


@router.post("")
async def webhook(
    body: dict,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(None),
):
    """
    外部サービスからエージェントへ指示を送る

    Body:
      action: "generate_article" | "generate_batch" | "optimize" | "emit_thought" | "status"
      topic:  {prefecture, area, property_type}  ← generate_article 用（省略時は自動）
      count:  int                                 ← generate_batch 用（デフォルト3）
      agent:  str                                 ← emit_thought 用
      thought: str                                ← emit_thought 用
      status_key: str                             ← emit_thought のステータス
      detail: str                                 ← emit_thought の詳細
    """
    _verify_token(authorization)

    action = body.get("action")
    if not action:
        raise HTTPException(status_code=400, detail="action が必要です")

    # ── generate_article ─────────────────────────────────────────────
    if action == "generate_article":
        topic = body.get("topic") or _next_topic()
        if "area" not in topic:
            topic = _next_topic()

        log = AgentLog(
            agent_name="writer_agent",
            task_type="generate_article",
            status="running",
            input_summary=f"[webhook] {topic.get('prefecture','')} {topic.get('area','')} {topic.get('property_type','')}",
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        await emit_thought(
            "writer",
            f"[Webhook] 指示受信: {topic.get('prefecture','')} {topic.get('area','')} の記事生成",
            "thinking",
            detail="外部サービスからの指示",
        )

        background_tasks.add_task(_bg_generate_article, topic, db)
        return {
            "ok": True,
            "action": "generate_article",
            "topic": topic,
            "log_id": str(log.id),
            "message": f"{topic.get('area','')}の記事を生成キューに追加しました",
        }

    # ── generate_batch ───────────────────────────────────────────────
    if action == "generate_batch":
        count = min(int(body.get("count", 3)), len(ARTICLE_TOPICS))
        topics = [_next_topic() for _ in range(count)]

        await emit_thought(
            "scheduler",
            f"[Webhook] バッチ生成指示: {count}件",
            "working",
            detail="外部サービスからの指示",
        )

        for t in topics:
            background_tasks.add_task(_bg_generate_article, t, db)

        return {
            "ok": True,
            "action": "generate_batch",
            "count": count,
            "topics": [f"{t['prefecture']} {t['area']}" for t in topics],
            "message": f"{count}件の記事生成をキューに追加しました",
        }

    # ── optimize ─────────────────────────────────────────────────────
    if action == "optimize":
        log = AgentLog(
            agent_name="optimizer_agent",
            task_type="optimization_cycle",
            status="running",
            input_summary="[webhook] external trigger",
        )
        db.add(log)
        await db.commit()

        await emit_thought(
            "optimizer",
            "[Webhook] 最適化サイクル開始指示を受信",
            "working",
            detail="外部サービスからの指示",
        )

        background_tasks.add_task(_bg_run_optimization, db)
        return {
            "ok": True,
            "action": "optimize",
            "message": "最適化サイクルをバックグラウンドで開始しました",
        }

    # ── emit_thought ─────────────────────────────────────────────────
    if action == "emit_thought":
        agent = body.get("agent", "scheduler")
        thought = body.get("thought", "外部からのメッセージ")
        status_key = body.get("status_key", "thinking")
        detail = body.get("detail")

        await emit_thought(agent, thought, status_key, detail)
        return {
            "ok": True,
            "action": "emit_thought",
            "agent": agent,
            "thought": thought,
        }

    # ── status ───────────────────────────────────────────────────────
    if action == "status":
        from agents.thoughts import get_snapshot
        return {"ok": True, "action": "status", "snapshot": get_snapshot()}

    raise HTTPException(status_code=400, detail=f"不明なアクション: {action}")
