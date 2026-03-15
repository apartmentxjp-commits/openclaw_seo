"""
Agent Scheduler — 4時間ごとに記事を自動生成する常駐プロセス
"""
import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import init_db, AsyncSessionLocal
from models import Article, AgentLog
from agents.writer_agent import WriterAgent, ARTICLE_TOPICS

_topic_index = 0


def _next_topic() -> dict:
    global _topic_index
    topic = ARTICLE_TOPICS[_topic_index % len(ARTICLE_TOPICS)]
    _topic_index += 1
    return topic


async def run_article_generation():
    topic = _next_topic()
    print(f"[Scheduler] {datetime.utcnow().isoformat()} — 記事生成開始: {topic['prefecture']} {topic['area']}")

    async with AsyncSessionLocal() as db:
        log = AgentLog(
            agent_name="scheduler",
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
            print(f"[Scheduler] 完了: {article.title}")

        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            print(f"[Scheduler] エラー: {e}")

        await db.commit()


async def main():
    print("[Scheduler] 起動中...")
    await init_db()

    interval_hours = int(os.getenv("ARTICLE_GENERATION_INTERVAL_HOURS", "4"))
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_article_generation,
        IntervalTrigger(hours=interval_hours),
        id="article_generation",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[Scheduler] 起動完了 — {interval_hours}時間ごとに記事生成")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("[Scheduler] 停止")


if __name__ == "__main__":
    asyncio.run(main())
