"""
统计查询接口
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import get_db
from app.core.security import get_current_manager
from app.services import StatsService

router = APIRouter(prefix="/api", tags=["统计"])


@router.get("/stats/query", response_model=None)
def query_stats(
    table: str = Query(..., regex="^(booking|room|sales)$"),
    start_date: date = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: date = Query(..., description="结束日期 YYYY-MM-DD"),
    store_id: Optional[int] = Query(None),
    dimension: str = Query("date"),
    granularity: str = Query("day"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    top_n: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    通用统计查询
    """
    # 根据用户角色过滤store_id权限
    if current_user["role"] == "manager":
        # 店长只能查看自己门店的数据
        if store_id is None:
            store_id = current_user["store_id"]
        elif store_id != current_user["store_id"]:
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail="无权限访问其他门店数据")

    service = StatsService(db)
    result = service.query_stats(
        table=table,
        start_date=start_date,
        end_date=end_date,
        store_id=store_id,
        dimension=dimension,
        granularity=granularity,
        page=page,
        page_size=page_size,
        top_n=top_n,
    )
    return {"success": True, "data": result}
