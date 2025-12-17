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
from typing import Optional

from fastapi import APIRouter, Query, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.schemas import (
    TableType,
    Dimension,
    TimeGranularity,
    StatsResponse,
    StatsItem,
    StatsMeta,
)
from app.core.database import get_db
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
        Dimension.ROOM: "room",
        Dimension.ROOM_TYPE: "room_type",
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

@router.get("/query", response_model=StatsResponse, summary="通用数据查询")
async def query_stats(
    table: TableType = Query(TableType.BOOKING, description="表类型"),
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    store_id: Optional[int] = Query(None, description="门店ID"),
    dimension: Dimension = Query(Dimension.DATE, description="聚合维度"),
    granularity: TimeGranularity = Query(TimeGranularity.DAY, description="时间粒度"),
    db: Session = Depends(get_db),
):
    """
    通用聚合查询接口
    
    根据不同参数组合返回不同维度的统计数据
    
    参考: docs/web界面5.md (1.3 节)
    """
    # 调用 StatsService 获取基础数据
    stats_service = StatsService(db)
    
    try:
        result = stats_service.query_stats(
            table=table.value,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            dimension=_convert_dimension_to_string(dimension),
            granularity=_convert_granularity_to_string(granularity),
        )
    except ValueError as e:
        # 如果维度不支持，返回空数据
        return StatsResponse(
            success=False,
            data=[],
            meta=StatsMeta(
                total_sales=0,
                total_actual=0,
                total_profit=None,
                total_records=0,
            ),
        )
    
    # 将 StatsService 返回的数据转换为前端需要的格式
    raw_data = result.get("data", [])
    stats_items = []
    
    for row in raw_data:
        raw_sales_amount = row.get("sales_amount")
        if raw_sales_amount is None:
            raw_sales_amount = row.get("sales")
        sales_amount_value = _safe_float(raw_sales_amount)
        orders_value = _safe_int(row.get("orders"))
        duration_value = _safe_int(row.get("duration"))
        item = StatsItem(
            dimension_key=str(row.get("dimension_key", "")),
            dimension_label=row.get("dimension_label"),
            # booking 表指标
            sales=sales_amount_value,
            actual=_safe_float(row.get("actual")),
            performance=_safe_float(row.get("performance")),
            booking_qty=orders_value,
            orders=orders_value,
            # room 表指标
            gmv=_safe_float(row.get("gmv")),
            room_discount=_safe_float(row.get("room_discount")),
            beverage_discount=_safe_float(row.get("beverage_discount")),
            order_count=orders_value,
            duration=duration_value,
            # sales 表指标
            sales_qty=_safe_int(row.get("sales_qty")),
            sales_amount=sales_amount_value,
            cost=_safe_float(row.get("cost_total")),
            profit=_safe_float(row.get("profit")),
            profit_rate=_safe_float(row.get("profit_rate")),
            # 赠送相关 (通用)
            gift_qty=_safe_int(row.get("gift_qty")),
            gift_amount=_safe_float(row.get("gift_amount")),
        )
        stats_items.append(item)
    
    # 计算汇总
    total_sales = sum(item.sales for item in stats_items)
    total_actual = sum(item.actual for item in stats_items)
    total_profit = sum(item.profit or 0 for item in stats_items)
    
    return StatsResponse(
        success=True,
        data=stats_items,
        meta=StatsMeta(
            total_sales=round(total_sales, 2),
            total_actual=round(total_actual, 2),
            total_profit=round(total_profit, 2) if total_profit else None,
            total_records=len(stats_items),
        ),
    )


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

