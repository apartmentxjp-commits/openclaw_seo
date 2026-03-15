"""
Optimizer Agent — 低パフォーマンス記事を Groq でリライトし
SEO・内容ともに改善する。
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from groq import Groq

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "llama-3.3-70b-versatile"

OPTIMIZE_SYSTEM_PROMPT = """あなたは日本の不動産SEO記事の専門ライターです。
既存の記事を以下の観点でリライト・強化してください：

1. 文字数を元記事の1.5倍以上に増やす（最低3000文字）
2. 見出し（##）を5つ以上設ける
3. 具体的な数値・価格帯・地域情報を追加する
4. 読者が知りたいQ&Aセクションを末尾に追加する
5. 検索クエリが指定されている場合、その言葉を自然に本文に組み込む
6. メタタイトル・メタディスクリプションも改善する

出力形式：
---ARTICLE---
（改善後のMarkdown記事本文）
---META---
{"meta_title": "改善後タイトル", "meta_description": "改善後ディスクリプション(120文字以内)"}
---END---
"""


class OptimizerAgent:
    """既存記事を分析データをもとに Groq でリライトする"""

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    async def optimize_article(
        self,
        db: AsyncSession,
        slug: str,
        target_info: dict,
    ) -> dict:
        """
        1記事をリライトして DB を更新する。
        target_info: {slug, title, area, prefecture, queries(list), reason, ...}
        Returns: {success, slug, old_len, new_len, duration_ms}
        """
        from backend.models import Article, AgentLog

        start = datetime.now(timezone.utc)

        # 記事を取得
        result = await db.execute(select(Article).where(Article.slug == slug))
        article = result.scalar_one_or_none()
        if not article:
            return {"success": False, "slug": slug, "error": "Article not found"}

        old_len = len(article.content or "")
        queries_str = "、".join(target_info.get("queries", [])) or "なし"
        reason = target_info.get("reason", "")

        prompt = f"""以下の記事を改善してください。

【改善理由】{reason}
【実際の検索クエリ（流入キーワード）】{queries_str}

【既存記事】
タイトル: {article.title}
エリア: {article.area}（{article.prefecture}）
物件種別: {article.property_type}

本文:
{article.content[:3000]}
{"...(以下省略)" if len(article.content or "") > 3000 else ""}
"""

        log = AgentLog(
            agent_name="optimizer_agent",
            task_type="optimize_article",
            status="running",
            input_summary=f"slug={slug} reason={reason} queries={queries_str[:100]}",
        )
        db.add(log)
        await db.commit()

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=MODEL,
                messages=[
                    {"role": "system", "content": OPTIMIZE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
            )

            raw = response.choices[0].message.content or ""
            new_content, new_meta = self._parse_response(raw, article)

            # DB 更新
            article.content = new_content
            article.meta_title = new_meta.get("meta_title", article.meta_title)
            article.meta_description = new_meta.get("meta_description", article.meta_description)
            article.last_optimized_at = datetime.now(timezone.utc)
            article.updated_at = datetime.now(timezone.utc)
            article.status = "pending_publish"  # 再公開フラグ

            duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            new_len = len(new_content)

            log.status = "success"
            log.output_summary = f"old={old_len}chars new={new_len}chars ({new_len - old_len:+})"
            log.duration_ms = duration_ms
            await db.commit()

            logger.info(f"Optimized: {slug} {old_len}→{new_len} chars")
            return {
                "success": True,
                "slug": slug,
                "old_len": old_len,
                "new_len": new_len,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            log.status = "error"
            log.error_message = str(e)
            await db.commit()
            logger.error(f"Optimize error for {slug}: {e}")
            return {"success": False, "slug": slug, "error": str(e)}

    def _parse_response(self, raw: str, article) -> tuple[str, dict]:
        """レスポンスから記事本文とメタデータを分離する"""
        import json as _json

        content = article.content  # フォールバック
        meta = {}

        try:
            if "---ARTICLE---" in raw and "---META---" in raw:
                parts = raw.split("---ARTICLE---")
                article_part = parts[1].split("---META---")[0].strip()
                meta_part = parts[1].split("---META---")[1].split("---END---")[0].strip()

                if article_part:
                    content = article_part
                if meta_part:
                    # JSON ブロック抽出
                    if "```json" in meta_part:
                        meta_part = meta_part.split("```json")[1].split("```")[0]
                    elif "```" in meta_part:
                        meta_part = meta_part.split("```")[1].split("```")[0]
                    meta = _json.loads(meta_part.strip())
            else:
                # セパレータなし → 全体を記事とみなす
                content = raw.strip() if len(raw.strip()) > 500 else content
        except Exception as e:
            logger.warning(f"Parse warning: {e}")

        return content, meta

    async def run_optimization_cycle(
        self, db: AsyncSession, limit: int = 3
    ) -> list[dict]:
        """
        最適化サイクルをフルで実行:
        1. AnalyticsAgent で改善対象を特定
        2. 各記事をリライト
        3. Publisher で再公開
        """
        from backend.agents.analytics_agent import AnalyticsAgent
        from backend.publisher import publish_pending_articles

        analytics = AnalyticsAgent()
        targets = await analytics.get_optimization_targets(db, limit=limit)

        if not targets:
            logger.info("No optimization targets found")
            return []

        logger.info(f"Optimization targets: {[t['slug'] for t in targets]}")

        results = []
        for target in targets:
            result = await self.optimize_article(db, target["slug"], target)
            results.append(result)

        # 再公開
        published = await publish_pending_articles(db)
        logger.info(f"Re-published {published} optimized articles")

        return results
