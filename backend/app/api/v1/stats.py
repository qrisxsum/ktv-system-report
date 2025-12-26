"""
数据统计与查询接口

Dev C 负责:
1. 接收前端请求参数
2. 调用 Dev A 的 StatsService 获取基础数据
3. 在 Python 层计算衍生指标（如环比增长、毛利率）
4. 将数据转换为前端需要的结构

参考文档:
- docs/web界面5.md (1.3 节)
- docs/聚合4.md (第二章)
- docs/任务分配.md (3.2 节 C6)

对接: Dev A (StatsService)
"""

from datetime import date, datetime, timedelta
from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.schemas import TableType, Dimension, TimeGranularity
from app.core.database import get_db
from app.core.security import get_current_manager
from app.services.stats import StatsService

router = APIRouter()


# ============================================================
# 辅助函数
# ============================================================

def _convert_dimension_to_string(dimension: Dimension) -> str:
    """将 Dimension 枚举转换为 StatsService 接受的字符串"""
    dimension_map = {
        Dimension.DATE: "date",
        Dimension.STORE: "store",
        Dimension.EMPLOYEE: "employee",
        Dimension.PRODUCT: "product",
        Dimension.CATEGORY: "category",
        Dimension.ROOM: "room",
        Dimension.ROOM_TYPE: "room_type",
        Dimension.BOOKER: "booker",
        Dimension.TIME_SLOT: "time_slot",
        Dimension.HOUR: "hour",
    }
    return dimension_map.get(dimension, "date")


def _convert_granularity_to_string(granularity: TimeGranularity) -> str:
    """将 TimeGranularity 枚举转换为字符串"""
    granularity_map = {
        TimeGranularity.DAY: "day",
        TimeGranularity.WEEK: "week",
        TimeGranularity.MONTH: "month",
    }
    return granularity_map.get(granularity, "day")


def _safe_float(value, default: float = 0.0) -> float:
    """安全地转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """安全地转换为整数"""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# 通用查询接口
# ============================================================

@router.get("/query", response_model=None, summary="通用数据查询")
async def query_stats(
    table: TableType = Query(TableType.BOOKING, description="表类型"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    store_id: Optional[int] = Query(None, description="门店ID"),
    dimension: Dimension = Query(Dimension.DATE, description="聚合维度"),
    granularity: TimeGranularity = Query(TimeGranularity.DAY, description="时间粒度"),
    page: int = Query(1, ge=1, description="分页页码（表格 rows 用）"),
    page_size: int = Query(20, ge=1, le=200, description="分页大小（表格 rows 用）"),
    top_n: int = Query(50, ge=1, le=200, description="非时间维度 Top-N（series_rows 用）"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    通用聚合查询接口
    
    根据不同参数组合返回不同维度的统计数据
    
    参考: docs/web界面5.md (1.3 节)
    """
    # 店长权限：只能查看自己门店
    if current_user.get("role") == "manager":
        if store_id is None:
            store_id = current_user.get("store_id")
        elif store_id != current_user.get("store_id"):
            raise HTTPException(status_code=403, detail="无权限访问其他门店数据")

    stats_service = StatsService(db)
    try:
        result = stats_service.query_stats(
            table=table.value,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            dimension=_convert_dimension_to_string(dimension),
            granularity=_convert_granularity_to_string(granularity),
            page=page,
            page_size=page_size,
            top_n=top_n,
        )
    except ValueError as e:
        return {"success": False, "message": str(e), "data": None}

    # 轻量字段兼容：部分前端仍使用 cost（而 StatsService 输出 cost_total）
    if table.value == "sales":
        for row in (result.get("rows") or []):
            if "cost" not in row and "cost_total" in row:
                row["cost"] = row.get("cost_total")
        for row in (result.get("series_rows") or []):
            if "cost" not in row and "cost_total" in row:
                row["cost"] = row.get("cost_total")

    return {"success": True, "data": result}


@router.get("/date-range", summary="获取数据日期范围")
async def get_date_range(
    table: TableType = Query(TableType.BOOKING, description="表类型"),
    db: Session = Depends(get_db),
):
    """
    获取指定表的数据日期范围
    
    用于前端页面自动设置默认日期范围
    """
    stats_service = StatsService(db)
    
    if table.value not in stats_service.TABLE_MAP:
        return {
            "success": False,
            "min_date": None,
            "max_date": None,
            "suggested_start": None,
            "suggested_end": None,
        }
    
    model = stats_service.TABLE_MAP[table.value]
    
    try:
        min_date = db.query(func.min(model.biz_date)).scalar()
        max_date = db.query(func.max(model.biz_date)).scalar()
        
        if max_date:
            # 建议日期范围：最新数据所在月份
            suggested_start = max_date.replace(day=1)
            suggested_end = max_date
        else:
            suggested_start = None
            suggested_end = None
        
        return {
            "success": True,
            "min_date": min_date.isoformat() if min_date else None,
            "max_date": max_date.isoformat() if max_date else None,
            "suggested_start": suggested_start.isoformat() if suggested_start else None,
            "suggested_end": suggested_end.isoformat() if suggested_end else None,
        }
    except Exception as e:
        return {
            "success": False,
            "min_date": None,
            "max_date": None,
            "suggested_start": None,
            "suggested_end": None,
            "error": str(e),
        }

