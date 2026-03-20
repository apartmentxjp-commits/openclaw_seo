"""
Agent Scheduler — OpenClaw Phase 1 Commander Agent 搭載版

ジョブ:
  1. 記事生成 (ARTICLE_GENERATION_INTERVAL_HOURS ごと、デフォルト0.5h)
     Commander Agent → topic_queue から優先選択 → WriterAgent → PostgreSQL → GitHub Pages
  2. 最適化サイクル (OPTIMIZATION_INTERVAL_HOURS ごと、デフォルト168h=週1回)
     AnalyticsAgent → OptimizerAgent → 再公開

リスク対策:
  - topic_queue の status 管理で重複記事を完全防止
  - error_count が 3 以上のトピックは自動 skip
  - Groq エラー時は topic を error 状態に戻してスキップ
  - topic_queue 枯渇時は ARTICLE_TOPICS フォールバック
"""
import asyncio
import os
import json
import psycopg2
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import init_db, AsyncSessionLocal
from models import Article, AgentLog
from agents.writer_agent import WriterAgent, ARTICLE_TOPICS
from agents.thoughts import emit_thought
from publisher import publish_pending_articles


# ─────────────────────────────────────────────────────────────────────────────
# Commander Agent: topic_queue から優先トピックを選択
# リスク対策:
#   - status='pending' のみ選択
#   - error_count >= 3 は自動 skip
#   - 記事タイプ比率を維持（area:50% guide:20% qa:15% ranking:15%）
# ─────────────────────────────────────────────────────────────────────────────

# 記事タイプ比率設定（Commander Agent の指揮ロジック）
# 環境変数 ARTICLE_TYPE_RATIOS で上書き可能: "area:35,guide:25,qa:15,ranking:25"
_DEFAULT_RATIOS = {"area": 35, "guide": 25, "qa": 15, "ranking": 25}

def _parse_ratios() -> dict:
    """環境変数からタイプ比率を解析。デフォルト: area35/guide25/qa15/ranking25"""
    raw = os.getenv("ARTICLE_TYPE_RATIOS", "")
    if not raw:
        return _DEFAULT_RATIOS.copy()
    try:
        result = {}
        for pair in raw.split(","):
            k, v = pair.strip().split(":")
            result[k.strip()] = int(v.strip())
        return result
    except Exception:
        return _DEFAULT_RATIOS.copy()

TYPE_RATIOS = _parse_ratios()
_generation_count = 0  # 総生成回数カウンター


def _get_next_article_type() -> str:
    """生成回数に基づいて記事タイプを決定（比率維持）"""
    global _generation_count
    c = _generation_count % 100
    if c < TYPE_RATIOS["area"]:
        return "area"
    elif c < TYPE_RATIOS["area"] + TYPE_RATIOS["guide"]:
        return "guide"
    elif c < TYPE_RATIOS["area"] + TYPE_RATIOS["guide"] + TYPE_RATIOS["qa"]:
        return "qa"
    else:
        return "ranking"


def _pick_topic_from_queue(article_type: str) -> dict | None:
    """
    topic_queue から指定タイプの pending トピックを取得。
    優先度降順・作成日昇順（FIFO with priority）
    リスク対策: 既にarticles.slugに存在するトピックは skip 更新
    """
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        return None
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, article_type, prefecture, area, property_type,
                   title_hint, keywords
            FROM topic_queue
            WHERE status = 'pending'
              AND article_type = %s
              AND error_count < 3
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        """, (article_type,))
        row = cur.fetchone()
        if not row:
            # 同タイプがない場合は全 pending から選択
            cur.execute("""
                SELECT id, article_type, prefecture, area, property_type,
                       title_hint, keywords
                FROM topic_queue
                WHERE status = 'pending'
                  AND error_count < 3
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """)
            row = cur.fetchone()

        if not row:
            cur.close()
            conn.close()
            return None

        topic_id, atype, pref, area, ptype, hint, kw = row

        # generating 状態にセット（重複防止ロック）
        cur.execute(
            "UPDATE topic_queue SET status='generating' WHERE id=%s",
            (topic_id,)
        )
        conn.commit()
        cur.close()
        conn.close()

        return {
            "_topic_id":    topic_id,
            "article_type": atype,
            "prefecture":   pref or "",
            "area":         area or "",
            "property_type": ptype or "マンション",
            "title_hint":   hint or "",
            "keywords":     kw or [],
        }
    except Exception as e:
        print(f"[Commander] topic_queue 取得エラー: {e}")
        return None


def _update_topic_status(topic_id: int, status: str, article_slug: str = None):
    """topic_queue のステータスを更新（done / error / skip）"""
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        return
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        if status == "done":
            cur.execute("""
                UPDATE topic_queue
                SET status='done', generated_at=NOW(), article_slug=%s
                WHERE id=%s
            """, (article_slug, topic_id))
        elif status == "error":
            cur.execute("""
                UPDATE topic_queue
                SET status='pending', error_count=error_count+1
                WHERE id=%s
            """, (topic_id,))
            # 3回エラーなら自動 skip
            cur.execute("""
                UPDATE topic_queue
                SET status='skip'
                WHERE id=%s AND error_count >= 3
            """, (topic_id,))
        else:
            cur.execute("UPDATE topic_queue SET status=%s WHERE id=%s", (status, topic_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Commander] topic_queue 更新エラー: {e}")


# フォールバック用（topic_queue 枯渇時）
_fallback_index = 0

def _fallback_topic(article_type: str = "area") -> dict:
    """topic_queue が空の場合の静的リストフォールバック"""
    global _fallback_index
    topic = ARTICLE_TOPICS[_fallback_index % len(ARTICLE_TOPICS)]
    _fallback_index += 1
    return {**topic, "article_type": article_type, "_topic_id": None}


# ─────────────────────────────────────────────────────────────────────────────
#  ジョブ1: 記事生成（Commander Agent 主導）
# ─────────────────────────────────────────────────────────────────────────────

async def run_article_generation():
    global _generation_count
    _generation_count += 1

    # Commander Agent がタイプを決定
    desired_type = _get_next_article_type()
    topic = _pick_topic_from_queue(desired_type) or _fallback_topic(desired_type)
    topic_id = topic.pop("_topic_id", None)
    article_type = topic.get("article_type", desired_type)

    pref  = topic.get("prefecture", "")
    area  = topic.get("area", "")
    ptype = topic.get("property_type", "マンション")

    print(f"[Commander] {datetime.utcnow().isoformat()} — "
          f"タイプ:{article_type} / {pref} {area} / {ptype}", flush=True)

    await emit_thought(
        "scheduler",
        f"Commander: {article_type}記事を選択 → WriterAgent に指示",
        "working",
        detail=f"{pref} {area} [{article_type}] #{_generation_count}"
    )

    async with AsyncSessionLocal() as db:
        log = AgentLog(
            agent_name="writer_agent",
            task_type=f"generate_{article_type}",
            status="running",
            input_summary=f"[{article_type}] {pref} {area} {ptype}",
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
                article_type=result.get("article_type", "area"),
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
            log.output_summary = f"[{article_type}] ID {article.id}: {article.title}"
            log.duration_ms = result.get("duration_ms")
            print(f"[Writer] 完了 [{article_type}] {len(result['content'])}文字: {article.title}", flush=True)

            # topic_queue を done に更新
            if topic_id:
                _update_topic_status(topic_id, "done", result["slug"])

            await emit_thought(
                "scheduler",
                f"✅ [{article_type}]記事完成 ({len(result['content'])}文字)",
                "success",
                detail=f"「{result['title'][:35]}」"
            )

        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            print(f"[Writer] エラー [{article_type}]: {e}")

            # topic_queue をエラーに戻す（3回失敗でスキップ）
            if topic_id:
                _update_topic_status(topic_id, "error")

            await emit_thought("scheduler", f"❌ [{article_type}]記事生成エラー",
                               "error", detail=str(e)[:80])

        await db.commit()

    # GitHub Pages 公開
    try:
        published = await publish_pending_articles()
        if published:
            print(f"[Publisher] {published}件を GitHub Pages に公開")
            await emit_thought("scheduler", f"📤 {published}件を GitHub Pages に公開完了", "success")
    except Exception as e:
        print(f"[Publisher] 公開エラー: {e}")
        await emit_thought("scheduler", f"⚠️ GitHub Pages 公開エラー", "error", detail=str(e)[:80])


# ─────────────────────────────────────────────────────────────────────────────
#  ジョブ2: 最適化サイクル
# ─────────────────────────────────────────────────────────────────────────────

async def run_optimization_cycle():
    print(f"[Optimizer] {datetime.utcnow().isoformat()} — 最適化サイクル開始")
    await emit_thought("scheduler", "最適化サイクル開始", "working")

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


# ─────────────────────────────────────────────────────────────────────────────
#  ジョブ3: topic_queue 補充チェック（毎日0時）
#  pending が 20件以下になったら area トピックを自動補充
# ─────────────────────────────────────────────────────────────────────────────

async def run_sitemap_ping():
    """Googleサーチコンソール・Bing へ sitemap.xml を ping して再クロールを促す"""
    SITEMAP_URL = os.getenv("SITE_BASE_URL", "https://realestate.tacky-consulting.com") + "/sitemap.xml"
    PING_URLS = [
        f"https://www.google.com/ping?sitemap={SITEMAP_URL}",
        f"https://www.bing.com/ping?sitemap={SITEMAP_URL}",
    ]
    import urllib.request as _ureq
    results = []
    for ping_url in PING_URLS:
        try:
            with _ureq.urlopen(ping_url, timeout=10) as resp:
                status = resp.status
                results.append(f"{ping_url.split('.')[1]}: {status}")
        except Exception as e:
            results.append(f"{ping_url.split('.')[1]}: error({e})")
    msg = " / ".join(results)
    print(f"[Sitemap] Ping 送信: {msg}", flush=True)
    await emit_thought("scheduler", f"Sitemap ping 送信: {msg}", "idle")


async def run_internal_link_cycle():
    """Internal Link Agent — 週1回（または記事が蓄積されたとき）、記事間相互リンクを生成"""
    print(f"[InternalLink] {datetime.utcnow().isoformat()} — Internal Link Agent 起動", flush=True)
    await emit_thought("scheduler", "Internal Link Agent: 記事間リンク生成開始", "working")
    try:
        from agents.internal_link_agent import run_internal_linking
        import asyncio as _asyncio
        stats = await _asyncio.to_thread(run_internal_linking, 50)
        msg = f"処理{stats['processed']}件 / リンク{stats['links_added']}件 / MD更新{stats['md_updated']}件"
        print(f"[InternalLink] {msg}", flush=True)
        await emit_thought("scheduler", f"Internal Link Agent 完了: {msg}", "success")
    except Exception as e:
        print(f"[InternalLink] エラー: {e}", flush=True)
        await emit_thought("scheduler", "Internal Link Agent エラー", "error", detail=str(e)[:80])


async def run_research_cycle():
    """Research Agent — 週1回、knowledge_base を最新データで更新"""
    print(f"[Research] {datetime.utcnow().isoformat()} — Research Agent 起動", flush=True)
    await emit_thought("scheduler", "Research Agent: 外部データ収集開始", "working")
    try:
        from agents.research_agent import run_research
        import asyncio as _asyncio
        count = await _asyncio.to_thread(run_research)
        print(f"[Research] knowledge_base {count}件更新完了", flush=True)
        await emit_thought("scheduler",
                           f"Research Agent 完了: {count}件を knowledge_base に保存",
                           "success")
    except Exception as e:
        print(f"[Research] エラー: {e}", flush=True)
        await emit_thought("scheduler", "Research Agent エラー", "error", detail=str(e)[:80])


async def run_topic_refill():
    """topic_queue の pending 件数をチェックし、不足時は補充"""
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        return
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM topic_queue WHERE status='pending'")
        pending_count = cur.fetchone()[0]
        print(f"[Commander] topic_queue pending: {pending_count}件")

        if pending_count < 20:
            # done になったトピックを pending にリセット（再サイクル）
            cur.execute("""
                UPDATE topic_queue
                SET status='pending', error_count=0, generated_at=NULL
                WHERE status='done'
                  AND article_type='area'
                ORDER BY generated_at ASC
                LIMIT 30
            """)
            refilled = cur.rowcount
            conn.commit()
            print(f"[Commander] {refilled}件の area トピックをリセット（再サイクル）")
            await emit_thought("scheduler",
                               f"topic_queue 補充: {refilled}件をリセット",
                               "idle")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Commander] topic_queue 補充エラー: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  メイン
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    # Python stdout をアンバッファリング（docker logs に即時反映）
    import sys as _sys
    _sys.stdout.reconfigure(line_buffering=True)
    print("[Scheduler] OpenClaw Phase 1 起動中...", flush=True)
    await init_db()

    generation_minutes = int(float(os.getenv("ARTICLE_GENERATION_INTERVAL_HOURS", "4")) * 60)
    optimization_hours = int(float(os.getenv("OPTIMIZATION_INTERVAL_HOURS", "168")))

    scheduler = AsyncIOScheduler()

    # ジョブ1: 記事生成（Commander Agent 主導）
    scheduler.add_job(
        run_article_generation,
        IntervalTrigger(minutes=generation_minutes),
        id="article_generation",
        replace_existing=True,
    )

    # ジョブ2: 最適化（週1回）
    scheduler.add_job(
        run_optimization_cycle,
        IntervalTrigger(hours=optimization_hours),
        id="optimization_cycle",
        replace_existing=True,
        next_run_time=None,
    )

    # ジョブ3: topic_queue 補充チェック（毎日）
    scheduler.add_job(
        run_topic_refill,
        IntervalTrigger(hours=24),
        id="topic_refill",
        replace_existing=True,
    )

    # ジョブ4: Research Agent（週1回 = 168時間ごと）
    research_hours = int(float(os.getenv("RESEARCH_INTERVAL_HOURS", "168")))
    scheduler.add_job(
        run_research_cycle,
        IntervalTrigger(hours=research_hours),
        id="research_cycle",
        replace_existing=True,
        next_run_time=None,
    )

    # ジョブ5: Internal Link Agent（72時間ごと）
    internallink_hours = int(float(os.getenv("INTERNALLINK_INTERVAL_HOURS", "72")))
    scheduler.add_job(
        run_internal_link_cycle,
        IntervalTrigger(hours=internallink_hours),
        id="internal_link_cycle",
        replace_existing=True,
        next_run_time=None,
    )

    # ジョブ6: Sitemap ping（24時間ごと）
    scheduler.add_job(
        run_sitemap_ping,
        IntervalTrigger(hours=24),
        id="sitemap_ping",
        replace_existing=True,
    )

    scheduler.start()
    print(f"[Scheduler] 起動完了", flush=True)
    print(f"  - 記事生成: {generation_minutes}分ごと（Commander Agent: area/guide/qa/ranking 比率制御）", flush=True)
    print(f"  - 最適化: {optimization_hours}時間ごと", flush=True)
    print(f"  - topic_queue 補充: 24時間ごと", flush=True)
    print(f"  - Research Agent: {research_hours}時間ごと（knowledge_base 更新）", flush=True)
    print(f"  - Internal Link Agent: {internallink_hours}時間ごと（記事間相互リンク生成）", flush=True)
    print(f"  - Sitemap ping: 24時間ごと（Google・Bing）", flush=True)

    await emit_thought(
        "scheduler",
        f"OpenClaw Phase 1 起動完了。{generation_minutes}分ごとに記事生成",
        "idle",
        detail="Commander Agent: area50% / guide20% / qa15% / ranking15%"
    )

    # 起動時に即実行
    asyncio.create_task(run_article_generation())

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("[Scheduler] 停止")


if __name__ == "__main__":
    asyncio.run(main())
