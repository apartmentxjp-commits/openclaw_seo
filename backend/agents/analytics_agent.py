"""
Analytics Agent — Google Search Console でパフォーマンスを取得し
改善が必要な記事を特定する。GSC未設定時はヒューリスティックで判定。
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import asyncio

logger = logging.getLogger(__name__)

GSC_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "")
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "https://realestate.tacky-consulting.com/")


class AnalyticsAgent:
    """Google Search Console からパフォーマンスデータを取得し、改善対象記事を特定する"""

    def __init__(self):
        self.gsc_available = bool(GSC_CREDENTIALS_FILE and os.path.exists(GSC_CREDENTIALS_FILE))
        if self.gsc_available:
            logger.info("Google Search Console mode: enabled")
        else:
            logger.info("Google Search Console mode: disabled (heuristic fallback)")

    # ------------------------------------------------------------------ #
    #  GSC モード                                                          #
    # ------------------------------------------------------------------ #

    def _get_gsc_service(self):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            GSC_CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        return build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    def fetch_page_performance(self, days: int = 28) -> list[dict]:
        """
        各ページの検索パフォーマンスを取得する。
        Returns: [{url, clicks, impressions, ctr, position}, ...]
        """
        if not self.gsc_available:
            return []

        try:
            service = self._get_gsc_service()
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)

            body = {
                "startDate": str(start_date),
                "endDate": str(end_date),
                "dimensions": ["page"],
                "rowLimit": 500,
            }
            resp = service.searchanalytics().query(siteUrl=GSC_SITE_URL, body=body).execute()
            rows = resp.get("rows", [])

            result = []
            for row in rows:
                url = row["keys"][0]
                # /posts/{slug}/ → slug 抽出
                slug = url.rstrip("/").split("/")[-1]
                result.append({
                    "url": url,
                    "slug": slug,
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 99), 1),
                })
            logger.info(f"GSC: fetched {len(result)} pages")
            return result
        except Exception as e:
            logger.error(f"GSC fetch error: {e}")
            return []

    def fetch_top_queries_for_page(self, page_url: str, days: int = 28) -> list[str]:
        """あるページに流入している検索クエリ上位10件を返す"""
        if not self.gsc_available:
            return []
        try:
            service = self._get_gsc_service()
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=days)
            body = {
                "startDate": str(start_date),
                "endDate": str(end_date),
                "dimensions": ["query"],
                "dimensionFilterGroups": [{
                    "filters": [{"dimension": "page", "expression": page_url}]
                }],
                "rowLimit": 10,
            }
            resp = service.searchanalytics().query(siteUrl=GSC_SITE_URL, body=body).execute()
            return [row["keys"][0] for row in resp.get("rows", [])]
        except Exception as e:
            logger.error(f"GSC query fetch error: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  ヒューリスティック モード（GSC なし）                               #
    # ------------------------------------------------------------------ #

    async def identify_underperformers_heuristic(
        self, db: AsyncSession, limit: int = 3
    ) -> list[dict]:
        """
        GSC なし版: 以下の基準で改善対象を選ぶ
        1. 公開から14日以上経過
        2. 最適化されていない（last_optimized_at IS NULL）
        3. content が短い（2000文字未満）
        優先度: last_optimized_at IS NULL → 古い順
        """
        from backend.models import Article

        stmt = (
            select(Article)
            .where(Article.status == "published")
            .where(
                Article.created_at < datetime.now(timezone.utc) - timedelta(days=14)
            )
            .order_by(Article.created_at.asc())
            .limit(limit * 3)  # 余分に取って絞る
        )
        result = await db.execute(stmt)
        articles = result.scalars().all()

        candidates = []
        for a in articles:
            score = 0
            if a.last_optimized_at is None:
                score += 10
            content_len = len(a.content or "")
            if content_len < 2000:
                score += 5
            elif content_len < 3000:
                score += 2
            age_days = (datetime.now(timezone.utc) - a.created_at).days
            score += min(age_days // 7, 10)

            candidates.append({
                "slug": a.slug,
                "title": a.title,
                "area": a.area,
                "prefecture": a.prefecture,
                "property_type": a.property_type,
                "content_len": content_len,
                "age_days": age_days,
                "score": score,
                "reason": "content_short" if content_len < 2000 else "not_optimized_recently",
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:limit]

    # ------------------------------------------------------------------ #
    #  メイン: 改善対象リストを返す                                        #
    # ------------------------------------------------------------------ #

    async def get_optimization_targets(
        self, db: AsyncSession, limit: int = 3
    ) -> list[dict]:
        """
        改善対象記事を返す。GSC があれば実データ、なければヒューリスティック。
        Returns: [{slug, title, area, prefecture, clicks, ctr, position, queries, reason}, ...]
        """
        if self.gsc_available:
            perf = self.fetch_page_performance(days=28)
            if perf:
                # CTR < 2% または 検索順位 > 15 の記事を優先
                underperformers = [
                    p for p in perf
                    if p["impressions"] >= 10 and (p["ctr"] < 2.0 or p["position"] > 15)
                ]
                underperformers.sort(key=lambda x: (-x["impressions"], x["ctr"]))

                results = []
                for p in underperformers[:limit]:
                    queries = self.fetch_top_queries_for_page(p["url"])
                    results.append({**p, "queries": queries, "reason": "low_ctr_or_position"})
                return results

        # フォールバック
        return await self.identify_underperformers_heuristic(db, limit)
