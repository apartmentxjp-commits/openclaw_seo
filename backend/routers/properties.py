from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Property

router = APIRouter()


@router.get("/")
async def list_properties(
    municipality: str = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(Property).order_by(Property.created_at.desc()).limit(limit)
    if municipality:
        q = q.where(Property.municipality == municipality)
    result = await db.execute(q)
    props = result.scalars().all()
    return [
        {
            "id": p.id,
            "prefecture": p.prefecture,
            "municipality": p.municipality,
            "district": p.district,
            "trade_price": p.trade_price,
            "price_per_unit": p.price_per_unit,
            "area": p.area,
            "floor_plan": p.floor_plan,
            "building_year": p.building_year,
            "trade_period": p.trade_period,
        }
        for p in props
    ]


@router.get("/summary")
async def properties_summary(db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(
            Property.prefecture,
            func.count().label("count"),
            func.avg(Property.trade_price).label("avg_price"),
        )
        .group_by(Property.prefecture)
        .order_by(func.count().desc())
    )
    rows = q.all()
    return [
        {
            "prefecture": r.prefecture,
            "count": r.count,
            "avg_price": int(r.avg_price) if r.avg_price else None,
        }
        for r in rows
    ]
