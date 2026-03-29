from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Article

router = APIRouter()


@router.get("/")
async def list_articles(limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(Article).order_by(Article.created_at.desc()).limit(limit)
    )
    articles = q.scalars().all()
    return [
        {
            "id": a.id,
            "slug": a.slug,
            "title": a.title,
            "area": a.area,
            "prefecture": a.prefecture,
            "property_type": a.property_type,
            "excerpt": a.excerpt,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in articles
    ]


@router.get("/{slug}")
async def get_article(slug: str, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Article).where(Article.slug == slug))
    article = q.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return {
        "id": article.id,
        "slug": article.slug,
        "title": article.title,
        "area": article.area,
        "prefecture": article.prefecture,
        "property_type": article.property_type,
        "content": article.content,
        "excerpt": article.excerpt,
        "meta_title": article.meta_title,
        "meta_description": article.meta_description,
        "keywords": article.keywords,
        "structured_data": article.structured_data,
        "status": article.status,
        "generated_by": article.generated_by,
        "duration_ms": article.duration_ms,
        "created_at": article.created_at.isoformat(),
    }
