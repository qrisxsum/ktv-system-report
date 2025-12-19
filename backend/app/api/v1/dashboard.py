"""
仪表盘数据接口

Dev C 负责:
1. 调用 Dev A 的 StatsService 获取基础数据
2. 在 Python 层计算衍生指标（如环比增长、毛利率）
3. 将数据转换为前端 ECharts 需要的结构

参考文档:
- docs/聚合4.md (1.1 节 - 口径定义)
- docs/web界面5.md (1.3 节, 2.2.1 节)
- docs/任务分配.md (3.2 节 C6)

对接: Dev A (StatsService)
"""

from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Query, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.schemas.stats import (
    DashboardSummary,
    TrendItem,
    TopItem,
)
from app.core.database import get_db
from app.core.security import get_current_manager, check_store_access, filter_store_access
from app.services.stats import StatsService

router = APIRouter()


# ============================================================
# 辅助函数 - 衍生指标计算
# ============================================================

def calculate_change_rate(current: float, previous: float) -> float:
    """
    计算环比/同比变化率
    
    公式: (当前值 - 上期值) / 上期值
    """
    if previous == 0:
        return 0.0 if current == 0 else 1.0
    return round((current - previous) / previous, 4)


def calculate_gross_margin(profit: float, revenue: float) -> float:
    """
    计算毛利率（销售毛利率）
    
    公式: 毛利 / 销售收入
    """
    if revenue == 0:
        return 0.0
    return round(profit / revenue, 4)


def calculate_gift_rate(gift_qty: int, total_qty: int) -> float:
    """
    计算赠送率
    
    公式: 赠送数量 / (销售数量 + 赠送数量)
    """
    if total_qty == 0:
        return 0.0
    return round(gift_qty / total_qty, 4)


def _safe_float(value, default: float = 0.0) -> float:
    """安全地转换为浮点数"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# API 接口
# ============================================================

@router.get("/summary", response_model=DashboardSummary, summary="首页看板汇总数据")
async def get_dashboard_summary(
    store_id: Optional[int] = Query(None, description="门店ID (不传则汇总所有门店)"),
    target_date: Optional[date] = Query(None, description="统计基准日 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取首页看板汇总数据

    包含:
    - 当日实收 & 环比
    - 本月实收 & 同比
    - 毛利率
    - 赠送率
    - 近30天营收趋势
    - Top5 门店/员工/商品

    参考: docs/web界面5.md (2.2.1 节)
    """
    # 根据用户角色过滤store_id权限
    if current_user["role"] == "manager":
        # 店长只能查看自己门店的数据
        if store_id is None:
            store_id = current_user["store_id"]
        elif store_id != current_user["store_id"]:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="无权限访问其他门店数据"
            )

    stats_service = StatsService(db)

    # 以 target_date 为看板“参考日”，否则回退到昨天
    reference_end = target_date or (date.today() - timedelta(days=1))

    yesterday = reference_end
    today = reference_end + timedelta(days=1)

    day_before_yesterday = yesterday - timedelta(days=1)
    month_start = yesterday.replace(day=1)
    
    # 上月同期（基于 reference 的“今天/昨天”）
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
        last_month_end = today.replace(year=today.year - 1, month=12, day=min(yesterday.day, 31))
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)
        try:
            last_month_end = yesterday.replace(month=today.month - 1)
        except ValueError:
            last_month_end = last_month_start.replace(day=28)
    
    # 初始化数据
    yesterday_actual = 0.0
    day_before_actual = 0.0
    month_actual = 0.0
    last_month_actual = 0.0
    month_cost = 0.0
    sales_qty_total = 0
    gift_qty_total = 0
    room_efficiency = {
        "total_orders": 0,
        "avg_duration": 0.0,
        "turnover_rate": 0.0,
    }
    
    # 查询数据
    try:
        # 基准日数据
        yesterday_result = stats_service.query_stats(
            table="booking",
            start_date=yesterday,
            end_date=yesterday,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in yesterday_result.get("series_rows", []):
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
        for row in day_before_result.get("series_rows", []):
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
        for row in month_result.get("series_rows", []):
            month_actual += _safe_float(row.get("actual"))
        
        # 上月同期
        last_month_result = stats_service.query_stats(
            table="booking",
            start_date=last_month_start,
            end_date=last_month_end,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in last_month_result.get("series_rows", []):
            last_month_actual += _safe_float(row.get("actual"))
    except Exception:
        pass

    # 包厢效率指标
    try:
        efficiency_result = stats_service.get_room_efficiency_stats(
            store_id=store_id,
            start_date=month_start,
            end_date=yesterday,
        ) or {}
        room_efficiency["total_orders"] = int(_safe_float(efficiency_result.get("total_orders")))
        room_efficiency["avg_duration"] = _safe_float(efficiency_result.get("avg_duration"))
        room_efficiency["turnover_rate"] = _safe_float(efficiency_result.get("turnover_rate"))
    except Exception:
        pass

    # 本月销售/成本聚合（sales 表）
    try:
        sales_month_result = stats_service.query_stats(
            table="sales",
            start_date=month_start,
            end_date=yesterday,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in sales_month_result.get("series_rows", []):
            month_cost += _safe_float(row.get("cost_total"))
            sales_qty_total += int(_safe_float(row.get("sales_qty")))
            gift_qty_total += int(_safe_float(row.get("gift_qty")))
    except Exception:
        pass
    
    # 计算衍生指标
    yesterday_change = calculate_change_rate(yesterday_actual, day_before_actual)
    month_change = calculate_change_rate(month_actual, last_month_actual)
    month_profit = month_actual - month_cost
    profit_rate = calculate_gross_margin(month_profit, month_actual)
    total_qty = sales_qty_total + gift_qty_total
    gift_rate = calculate_gift_rate(gift_qty_total, total_qty)
    
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
        for row in trend_result.get("series_rows", []):
            actual_value = round(_safe_float(row.get("actual")), 2)
            orders_value = int(_safe_float(row.get("orders")))
            revenue_trend.append(
                TrendItem(
                    date=str(row.get("dimension_key", "")),
                    value=actual_value,
                    revenue=actual_value,
                    orders=orders_value,
                )
            )
    except Exception:
        for i in range(30, 0, -1):
            d = today - timedelta(days=i)
            revenue_trend.append(
                TrendItem(
                    date=d.strftime("%Y-%m-%d"),
                    value=0.0,
                    revenue=0.0,
                    orders=0.0,
                )
            )
    
    # 获取 Top 5 排行榜
    top_stores = []
    top_employees = []
    top_products = []

    try:
        # 门店排行
        stores_data = stats_service.get_top_items(
            table="booking",
            metric="actual",
            dimension="store",
            limit=5,
            start_date=month_start,
            end_date=yesterday,
            store_id=None,  # store 维度下不使用 store_id 过滤
        )
        top_stores = [
            TopItem(rank=i + 1, name=row["dimension_label"], value=round(row["metric_value"], 2))
            for i, row in enumerate(stores_data)
        ]
    except Exception as e:
        import logging
        logging.warning(f"Failed to get top stores: {e}")

    try:
        # 员工排行
        employees_data = stats_service.get_top_items(
            table="booking",
            metric="actual",
            dimension="employee",
            limit=5,
            start_date=month_start,
            end_date=yesterday,
            store_id=store_id,
        )
        top_employees = [
            TopItem(rank=i + 1, name=row["dimension_label"], value=round(row["metric_value"], 2))
            for i, row in enumerate(employees_data)
        ]
    except Exception as e:
        import logging
        logging.warning(f"Failed to get top employees: {e}")

    try:
        # 商品排行
        products_data = stats_service.get_top_items(
            table="sales",
            metric="sales",
            dimension="product",
            limit=5,
            start_date=month_start,
            end_date=yesterday,
            store_id=store_id,  # 支持按门店筛选商品排行
        )
        top_products = [
            TopItem(rank=i + 1, name=row["dimension_label"], value=round(row["metric_value"], 2))
            for i, row in enumerate(products_data)
        ]
    except Exception as e:
        import logging
        logging.warning(f"Failed to get top products: {e}")
    
    return DashboardSummary(
        reference_date=yesterday,
        period_start=month_start,
        yesterday_actual=round(yesterday_actual, 2),
        yesterday_change=yesterday_change,
        month_actual=round(month_actual, 2),
        month_change=month_change,
        month_cost=round(month_cost, 2),
        month_profit=round(month_profit, 2),
        profit_rate=profit_rate,
        gift_rate=gift_rate,
        total_orders=room_efficiency["total_orders"],
        avg_duration=room_efficiency["avg_duration"],
        turnover_rate=room_efficiency["turnover_rate"],
        revenue_trend=revenue_trend,
        top_stores=top_stores,
        top_employees=top_employees,
        top_products=top_products,
    )


@router.get("/kpi", summary="获取 KPI 指标卡片数据", response_model=None)
async def get_kpi_cards(
    store_id: Optional[int] = Query(None, description="门店ID"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取 KPI 指标卡片数据（可自定义时间范围）
    """
    # 根据用户角色过滤store_id权限
    if current_user["role"] == "manager":
        # 店长只能查看自己门店的数据
        if store_id is None:
            store_id = current_user["store_id"]
        elif store_id != current_user["store_id"]:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="无权限访问其他门店数据"
            )

    # 默认时间范围: 本月
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()

    stats_service = StatsService(db)
    
    # 初始化数据
    actual_amount = 0.0
    sales_amount = 0.0
    order_count = 0
    gift_amount = 0.0
    
    try:
        result = stats_service.query_stats(
            table="booking",
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in result.get("series_rows", []):
            actual_amount += _safe_float(row.get("actual"))
            sales_amount += _safe_float(row.get("sales"))
            order_count += int(_safe_float(row.get("orders")))
            gift_amount += _safe_float(row.get("gift_amount"))
    except Exception:
        pass
    
    profit = actual_amount * 0.4
    profit_rate = 0.4 if actual_amount > 0 else 0.0
    gift_rate = gift_amount / sales_amount if sales_amount > 0 else 0.0
    
    return {
        "success": True,
        "data": {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "metrics": {
                "actual_amount": round(actual_amount, 2),
                "sales_amount": round(sales_amount, 2),
                "profit": round(profit, 2),
                "profit_rate": round(profit_rate, 4),
                "order_count": order_count,
                "gift_amount": round(gift_amount, 2),
                "gift_rate": round(gift_rate, 4),
            },
            "comparison": {
                "actual_change": 0.0,
                "profit_change": 0.0,
                "order_change": 0.0,
            }
        }
    }


@router.get("/trend", summary="获取趋势数据", response_model=None)
async def get_trend_data(
    metric: str = Query("actual", description="指标: actual/sales/profit/orders"),
    days: int = Query(30, ge=7, le=90, description="天数"),
    store_id: Optional[int] = Query(None, description="门店ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取指定指标的趋势数据（用于折线图）
    """
    # 根据用户角色过滤store_id权限
    if current_user["role"] == "manager":
        # 店长只能查看自己门店的数据
        if store_id is None:
            store_id = current_user["store_id"]
        elif store_id != current_user["store_id"]:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="无权限访问其他门店数据"
            )

    today = date.today()
    start_date = today - timedelta(days=days)

    stats_service = StatsService(db)
    
    # 指标映射
    metric_field_map = {
        "actual": "actual",
        "sales": "sales",
        "profit": "performance",
        "orders": "orders",
    }
    field = metric_field_map.get(metric, "actual")
    
    data = []
    try:
        result = stats_service.query_stats(
            table="booking",
            start_date=start_date,
            end_date=today - timedelta(days=1),
            store_id=store_id,
            dimension="date",
            granularity="day",
        )
        for row in result.get("series_rows", []):
            data.append({
                "date": str(row.get("dimension_key", "")),
                "value": round(_safe_float(row.get(field)), 2),
            })
    except Exception:
        for i in range(days, 0, -1):
            d = today - timedelta(days=i)
            data.append({
                "date": d.strftime("%Y-%m-%d"),
                "value": 0.0,
            })
    
    return {
        "success": True,
        "metric": metric,
        "data": data,
    }


@router.get("/ranking", summary="获取排行榜数据", response_model=None)
async def get_ranking_data(
    dimension: str = Query("store", description="维度: store/employee/product/room"),
    metric: str = Query("actual", description="指标: actual/sales/profit/qty"),
    limit: int = Query(10, ge=5, le=50, description="返回数量"),
    store_id: Optional[int] = Query(None, description="门店ID (当 dimension != store 时有效)"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取排行榜数据（用于柱状图）
    """
    # 根据用户角色过滤store_id权限
    if current_user["role"] == "manager":
        # 店长只能查看自己门店的数据
        if dimension == "store":
            # 按门店排行时，强制限制为只看自己的门店
            store_id = current_user["store_id"]
        else:
            # 按其他维度排行时，如果没有指定store_id或指定了其他门店，强制使用自己的门店
            if store_id is None or store_id != current_user["store_id"]:
                store_id = current_user["store_id"]

    stats_service = StatsService(db)
    
    # 选择合适的表和维度
    table_map = {
        "store": "booking",
        "employee": "booking",
        "product": "sales",
        "room": "room",
    }
    table = table_map.get(dimension, "booking")

    # 默认时间范围：如果未传 start/end，则取“该表最新 biz_date 所在月份”
    if not start_date or not end_date:
        max_date = None
        try:
            model = stats_service.TABLE_MAP.get(table)
            if model is not None:
                q = db.query(func.max(model.biz_date))
                if store_id is not None and dimension != "store" and hasattr(model, "store_id"):
                    q = q.filter(model.store_id == store_id)
                max_date = q.scalar()
        except Exception:
            max_date = None

        if max_date is None:
            if not start_date:
                start_date = date.today().replace(day=1)
            if not end_date:
                end_date = date.today()
        else:
            if not end_date:
                end_date = max_date
            if not start_date:
                start_date = end_date.replace(day=1)
    
    data = []
    try:
        # 调用新增的 get_top_items 方法
        top_items = stats_service.get_top_items(
            table=table,
            metric=metric,
            dimension=dimension,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id if dimension != "store" else None,
        )

        data = [
            TopItem(rank=i + 1, name=item["dimension_label"], value=round(item["metric_value"], 2))
            for i, item in enumerate(top_items)
        ]
    except Exception as e:
        import logging
        logging.warning(f"Failed to get ranking data: {e}")

    return {
        "success": True,
        "dimension": dimension,
        "metric": metric,
        "data": data,
    }
