"""
统计查询接口
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import get_db
from app.services import StatsService

router = APIRouter(prefix="/api", tags=["统计"])


@router.get("/stats/query")
def query_stats(
    table: str = Query(..., regex="^(booking|room|sales)$"),
    start_date: date = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="结束日期 YYYY-MM-DD"),
    store_id: Optional[int] = Query(None),
    dimension: str = Query("date"),
    granularity: str = Query("day"),
    db: Session = Depends(get_db),
):
    """
    通用统计查询
    """
    service = StatsService(db)
    result = service.query_stats(
        table=table,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
        dimension=dimension,
        granularity=granularity,
    )
    return {
        "success": True,
        "data": result["data"],
        "meta": result["meta"],
    }

