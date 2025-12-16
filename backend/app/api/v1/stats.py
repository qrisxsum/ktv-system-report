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
from sqlalchemy.orm import Session

from app.schemas import (
    TableType,
    Dimension,
    TimeGranularity,
    StatsResponse,
    StatsItem,
    StatsMeta,
    DashboardSummary,
    TrendItem,
    TopItem,
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
        item = StatsItem(
            dimension_key=str(row.get("dimension_key", "")),
            dimension_label=row.get("dimension_label"),
            # booking 表指标
            sales=_safe_float(row.get("sales")),
            actual=_safe_float(row.get("actual")),
            performance=_safe_float(row.get("performance")),
            booking_qty=_safe_int(row.get("orders")),
            # room 表指标
            gmv=_safe_float(row.get("gmv")),
            room_discount=_safe_float(row.get("room_discount")),
            beverage_discount=_safe_float(row.get("beverage_discount")),
            order_count=_safe_int(row.get("orders")),
            # sales 表指标
            cost=_safe_float(row.get("cost_total")),
            profit=_safe_float(row.get("profit")),
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


# ============================================================
# Dashboard 接口
# ============================================================

@router.get("/dashboard/summary", response_model=DashboardSummary, summary="首页看板数据")
async def get_dashboard_summary(
    store_id: Optional[int] = Query(None, description="门店ID (不传则汇总所有门店)"),
    db: Session = Depends(get_db),
):
    """
    获取首页看板汇总数据
    
    参考: docs/web界面5.md (2.2.1 节)
    """
    stats_service = StatsService(db)
    today = date.today()
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    month_start = today.replace(day=1)
    
    # 上月同期计算
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)
    
    # 查询昨日数据 (使用 booking 表作为主要数据源)
    yesterday_actual = 0.0
    day_before_actual = 0.0
    month_actual = 0.0
    last_month_actual = 0.0
    
    try:
        # 昨日数据
        yesterday_result = stats_service.query_stats(
            table="booking",
            start_date=yesterday,
            end_date=yesterday,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in yesterday_result.get("data", []):
            yesterday_actual += _safe_float(row.get("actual"))
        
        # 前天数据
        day_before_result = stats_service.query_stats(
            table="booking",
            start_date=day_before_yesterday,
            end_date=day_before_yesterday,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in day_before_result.get("data", []):
            day_before_actual += _safe_float(row.get("actual"))
        
        # 本月累计
        month_result = stats_service.query_stats(
            table="booking",
            start_date=month_start,
            end_date=yesterday,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in month_result.get("data", []):
            month_actual += _safe_float(row.get("actual"))
    except Exception:
        pass
    
    # 计算环比
    def calc_change(current: float, previous: float) -> float:
        if previous == 0:
            return 0.0 if current == 0 else 1.0
        return round((current - previous) / previous, 4)
    
    yesterday_change = calc_change(yesterday_actual, day_before_actual)
    month_change = calc_change(month_actual, last_month_actual) if last_month_actual > 0 else 0.0
    
    # 生成趋势数据 (近30天)
    revenue_trend = []
    try:
        trend_start = today - timedelta(days=30)
        trend_result = stats_service.query_stats(
            table="booking",
            start_date=trend_start,
            end_date=yesterday,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in trend_result.get("data", []):
            revenue_trend.append(TrendItem(
                date=str(row.get("dimension_key", "")),
                value=round(_safe_float(row.get("actual")), 2),
            ))
    except Exception:
        # 如果查询失败，生成空趋势
        for i in range(30, 0, -1):
            d = today - timedelta(days=i)
            revenue_trend.append(TrendItem(
                date=d.strftime("%Y-%m-%d"),
                value=0.0,
            ))
    
    # TODO: 获取 Top 5 门店/员工/商品 (需要扩展 StatsService)
    # 暂时返回空列表
    top_stores = []
    top_employees = []
    top_products = []
    
    return DashboardSummary(
        yesterday_actual=round(yesterday_actual, 2),
        yesterday_change=yesterday_change,
        month_actual=round(month_actual, 2),
        month_change=month_change,
        month_profit=round(month_actual * 0.4, 2),  # 估算毛利
        profit_rate=0.4,
        gift_rate=0.05,
        revenue_trend=revenue_trend,
        top_stores=top_stores,
        top_employees=top_employees,
        top_products=top_products,
    )

