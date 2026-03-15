from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Article, AgentLog
from agents.writer_agent import WriterAgent, ARTICLE_TOPICS

router = APIRouter()

# Simple in-memory topic rotation counter
_topic_index = 0


def _next_topic() -> dict:
    global _topic_index
    topic = ARTICLE_TOPICS[_topic_index % len(ARTICLE_TOPICS)]
    _topic_index += 1
    return topic


async def _generate_and_save(topic: dict, db: AsyncSession):
    """Background task: generate article and save to DB."""
    log = AgentLog(
        agent_name="writer_agent",
        task_type="generate_article",
        status="running",
        input_summary=f"{topic['prefecture']} {topic['area']} {topic['property_type']}",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

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
        await db.refresh(article)

        log.status = "success"
        log.output_summary = f"Article ID {article.id}: {article.title}"
        log.duration_ms = result.get("duration_ms")
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)

    await db.commit()
    return log.id


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    # Total articles
    total_q = await db.execute(select(func.count()).select_from(Article))
    total_articles = total_q.scalar() or 0

    # Last 24h stats
    since = datetime.utcnow() - timedelta(hours=24)
    logs_q = await db.execute(
        select(AgentLog.status, func.count().label("cnt"))
        .where(AgentLog.created_at >= since)
        .group_by(AgentLog.status)
    )
    rows = logs_q.all()
    counts = {r.status: r.cnt for r in rows}

    return {
        "agents": {
            "writer_agent": {"model": "gemini-1.5-flash", "role": "不動産記事自動執筆"},
            "scheduler": {"model": "-", "role": "4時間ごとの定期実行"},
        },
        "last_24h": {
            "success_count": counts.get("success", 0),
            "error_count": counts.get("error", 0),
            "running_count": counts.get("running", 0),
            "total_count": sum(counts.values()),
        },
        "total_articles": total_articles,
    }


@router.get("/logs")
async def get_logs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(AgentLog).order_by(AgentLog.created_at.desc()).limit(limit)
    )
    logs = q.scalars().all()
    return [
        {
            "id": str(l.id),
            "agent_name": l.agent_name,
            "task_type": l.task_type,
            "status": l.status,
            "input_summary": l.input_summary or "",
            "output_summary": l.output_summary or "",
            "error_message": l.error_message or "",
            "duration_ms": l.duration_ms,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.post("/write/article")
async def write_article(
    body: dict = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    topic = body or _next_topic()
    if "area" not in topic:
        topic = _next_topic()

    # Create a placeholder log to return log_id immediately
    log = AgentLog(
        agent_name="writer_agent",
        task_type="generate_article",
        status="running",
        input_summary=f"{topic.get('prefecture', '')} {topic.get('area', '')} {topic.get('property_type', '')}",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    background_tasks.add_task(_generate_and_save, topic, db)

    return {"message": f"{topic.get('area', '')}の記事を生成中です", "log_id": str(log.id)}


@router.post("/write/batch")
async def write_batch(
    body: dict = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    count = (body or {}).get("count", 3)
    count = min(count, len(ARTICLE_TOPICS))

    for _ in range(count):
        topic = _next_topic()
        background_tasks.add_task(_generate_and_save, topic, db)

    return {"message": f"{count}件の記事生成をキューに追加しました"}


async def _run_optimization(db: AsyncSession):
    """Background task: run full optimization cycle."""
    from agents.optimizer_agent import OptimizerAgent
    optimizer = OptimizerAgent()
    await optimizer.run_optimization_cycle(db, limit=3)


@router.post("/optimize")
async def trigger_optimization(
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """低パフォーマンス記事の最適化サイクルを手動トリガー"""
    log = AgentLog(
        agent_name="optimizer_agent",
        task_type="optimization_cycle",
        status="running",
        input_summary="manual trigger",
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    background_tasks.add_task(_run_optimization, db)

    return {"message": "最適化サイクルを開始しました（バックグラウンド実行）", "log_id": str(log.id)}


@router.get("/optimize/targets")
async def get_optimization_targets(db: AsyncSession = Depends(get_db)):
    """最適化候補記事を確認する（実行なし）"""
    from agents.analytics_agent import AnalyticsAgent
    analytics = AnalyticsAgent()
    targets = await analytics.get_optimization_targets(db, limit=5)
    return {"targets": targets, "gsc_enabled": analytics.gsc_available}
