"""
Agent Scheduler — 記事生成・最適化を自律的に実行する常駐プロセス

ジョブ:
  1. 記事生成 (ARTICLE_GENERATION_INTERVAL_HOURS ごと、デフォルト0.5h)
     WriterAgent → PostgreSQL → GitHub Pages
  2. 最適化サイクル (OPTIMIZATION_INTERVAL_HOURS ごと、デフォルト168h=週1回)
     AnalyticsAgent で低パフォーマンス記事を特定 → OptimizerAgent でリライト → 再公開
"""
import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import init_db, AsyncSessionLocal
from models import Article, AgentLog
from agents.writer_agent import WriterAgent, ARTICLE_TOPICS
from agents.thoughts import emit_thought
from publisher import publish_pending_articles

_topic_index = 0


def _next_topic() -> dict:
    global _topic_index
    topic = ARTICLE_TOPICS[_topic_index % len(ARTICLE_TOPICS)]
    _topic_index += 1
    return topic


# ------------------------------------------------------------------ #
#  ジョブ1: 記事生成                                                   #
# ------------------------------------------------------------------ #

async def run_article_generation():
    topic = _next_topic()
    print(f"[Writer] {datetime.utcnow().isoformat()} — 記事生成: {topic['prefecture']} {topic['area']}")

    await emit_thought("scheduler",
                       f"WriterAgent に指示: {topic['prefecture']} {topic['area']} {topic['property_type']}",
                       "working", detail=f"トピック #{_topic_index}/{len(ARTICLE_TOPICS)}")

    async with AsyncSessionLocal() as db:
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
                generated_by="groq",
                duration_ms=result.get("duration_ms"),
            )
            db.add(article)
            await db.commit()
            await db.refresh(article)

            log.status = "success"
            log.output_summary = f"Article ID {article.id}: {article.title}"
            log.duration_ms = result.get("duration_ms")
            print(f"[Writer] 完了: {article.title}")
            await emit_thought("scheduler", f"✅ 記事生成完了。次は GitHub Pages に公開", "success",
                               detail=f"「{result['title'][:30]}...」")

        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            print(f"[Writer] エラー: {e}")
            await emit_thought("scheduler", f"❌ 記事生成でエラー発生", "error", detail=str(e)[:80])

        await db.commit()

    try:
        published = await publish_pending_articles()
        if published:
            print(f"[Writer] {published}件を GitHub Pages に公開しました")
            await emit_thought("scheduler", f"📤 {published}件を GitHub Pages に公開完了", "success")
    except Exception as e:
        print(f"[Writer] 公開エラー: {e}")
        await emit_thought("scheduler", f"⚠️ GitHub Pages 公開でエラー", "error", detail=str(e)[:80])


# ------------------------------------------------------------------ #
#  ジョブ2: 最適化サイクル                                              #
# ------------------------------------------------------------------ #

async def run_optimization_cycle():
    print(f"[Optimizer] {datetime.utcnow().isoformat()} — 最適化サイクル開始")
    await emit_thought("scheduler", "最適化サイクル開始。AnalyticsAgent に分析依頼", "working")

    async with AsyncSessionLocal() as db:
        log = AgentLog(
            agent_name="optimizer_agent",
            task_type="optimization_cycle",
            status="running",
            input_summary="scheduled weekly optimization",
        )
        db.add(log)
        await db.commit()

        try:
            from agents.optimizer_agent import OptimizerAgent
            optimizer = OptimizerAgent()
            results = await optimizer.run_optimization_cycle(db, limit=3)

            success = [r for r in results if r.get("success")]
            log.status = "success"
            log.output_summary = (
                f"{len(success)}/{len(results)} articles optimized: "
                + ", ".join(r["slug"] for r in success)
            )
            print(f"[Optimizer] 完了: {len(success)}件最適化")

        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            print(f"[Optimizer] エラー: {e}")

        await db.commit()


# ------------------------------------------------------------------ #
#  メイン                                                              #
# ------------------------------------------------------------------ #

async def main():
    print("[Scheduler] 起動中...")
    await init_db()

    generation_minutes = int(float(os.getenv("ARTICLE_GENERATION_INTERVAL_HOURS", "4")) * 60)
    optimization_hours = int(float(os.getenv("OPTIMIZATION_INTERVAL_HOURS", "168")))  # 週1

    scheduler = AsyncIOScheduler()

    # ジョブ1: 記事生成
    scheduler.add_job(
        run_article_generation,
        IntervalTrigger(minutes=generation_minutes),
        id="article_generation",
        replace_existing=True,
    )

    # ジョブ2: 最適化（起動から1時間後に初回実行）
    scheduler.add_job(
        run_optimization_cycle,
        IntervalTrigger(hours=optimization_hours),
        id="optimization_cycle",
        replace_existing=True,
        next_run_time=None,  # 手動または初回起動1h後
    )

    scheduler.start()
    print(f"[Scheduler] 起動完了")
    print(f"  - 記事生成: {generation_minutes}分ごと")
    print(f"  - 最適化: {optimization_hours}時間ごと（週1回）")

    await emit_thought("scheduler",
                       f"起動完了。記事生成: {generation_minutes}分ごと / 最適化: {optimization_hours}h ごと",
                       "idle", detail="次の実行を待機中...")

    # 起動時に記事生成を即実行
    asyncio.create_task(run_article_generation())

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("[Scheduler] 停止")


if __name__ == "__main__":
    asyncio.run(main())
