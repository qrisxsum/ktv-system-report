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
"""

from datetime import date, datetime, timedelta
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Query

from app.schemas.stats import (
    DashboardSummary,
    TrendItem,
    TopItem,
)

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
        return 0.0 if current == 0 else 1.0  # 上期为0时，有值则100%增长
    return round((current - previous) / previous, 4)


def calculate_profit_rate(profit: float, cost: float) -> float:
    """
    计算利润率（成本利润率）
    
    公式: 利润 / 成本
    参考: docs/字段映射1.md (2.3 节)
    """
    if cost == 0:
        return 0.0
    return round(profit / cost, 4)


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
    参考: docs/聚合4.md (1.4 节)
    """
    if total_qty == 0:
        return 0.0
    return round(gift_qty / total_qty, 4)


# ============================================================
# API 接口
# ============================================================

@router.get("/summary", response_model=DashboardSummary, summary="首页看板汇总数据")
async def get_dashboard_summary(
    store_id: Optional[int] = Query(None, description="门店ID (不传则汇总所有门店)"),
):
    """
    获取首页看板汇总数据
    
    包含:
    - 昨日实收 & 环比
    - 本月实收 & 同比
    - 毛利率
    - 赠送率
    - 近30天营收趋势
    - Top5 门店/员工/商品
    
    参考: docs/web界面5.md (2.2.1 节)
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    
    # 本月第一天
    month_start = today.replace(day=1)
    # 上月同期
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)
    last_month_same_day = yesterday.replace(month=last_month_start.month, year=last_month_start.year)
    
    # ============================================================
    # TODO: 调用 Dev A 的 StatsService 获取真实数据
    # from app.services.stats import StatsService
    # stats_service = StatsService()
    # 
    # # 昨日数据
    # yesterday_data = stats_service.get_daily_summary(yesterday, store_id)
    # day_before_data = stats_service.get_daily_summary(day_before_yesterday, store_id)
    # 
    # # 本月累计
    # month_data = stats_service.get_period_summary(month_start, yesterday, store_id)
    # last_month_data = stats_service.get_period_summary(last_month_start, last_month_same_day, store_id)
    # ============================================================
    
    # Mock 数据 (等待 Dev A 实现后替换)
    yesterday_actual = 18500.0
    day_before_actual = 16500.0
    
    month_actual = 485000.0
    last_month_actual = 449000.0
    
    month_cost = 287000.0
    month_profit = month_actual - month_cost
    
    total_qty = 2500
    gift_qty = 125
    
    # 计算衍生指标
    yesterday_change = calculate_change_rate(yesterday_actual, day_before_actual)
    month_change = calculate_change_rate(month_actual, last_month_actual)
    profit_rate = calculate_gross_margin(month_profit, month_actual)
    gift_rate = calculate_gift_rate(gift_qty, total_qty)
    
    # ============================================================
    # 生成趋势数据 (近30天)
    # TODO: 调用 stats_service.get_daily_trend(30, store_id)
    # ============================================================
    revenue_trend = []
    for i in range(30, 0, -1):
        d = today - timedelta(days=i)
        # Mock: 基于日期 hash 生成波动数据
        base = 15000
        variation = (hash(d.strftime("%Y%m%d")) % 8000) - 4000
        revenue_trend.append(TrendItem(
            date=d.strftime("%Y-%m-%d"),
            value=round(base + variation + (30 - i) * 100, 2),  # 轻微上升趋势
        ))
    
    # ============================================================
    # 生成排行榜数据
    # TODO: 调用 stats_service.get_top_stores/employees/products(5, store_id)
    # ============================================================
    top_stores = [
        TopItem(rank=1, name="万象城店", value=156000),
        TopItem(rank=2, name="青年路店", value=142000),
        TopItem(rank=3, name="高新店", value=128000),
        TopItem(rank=4, name="曲江店", value=115000),
        TopItem(rank=5, name="小寨店", value=98000),
    ]
    
    top_employees = [
        TopItem(rank=1, name="张三", value=45000),
        TopItem(rank=2, name="李四", value=38000),
        TopItem(rank=3, name="王五", value=32000),
        TopItem(rank=4, name="赵六", value=28000),
        TopItem(rank=5, name="钱七", value=24000),
    ]
    
    top_products = [
        TopItem(rank=1, name="百威啤酒", value=12500),
        TopItem(rank=2, name="青岛啤酒", value=9800),
        TopItem(rank=3, name="可乐", value=7600),
        TopItem(rank=4, name="台湾香肠", value=5400),
        TopItem(rank=5, name="薯条", value=4200),
    ]
    
    return DashboardSummary(
        yesterday_actual=yesterday_actual,
        yesterday_change=yesterday_change,
        month_actual=month_actual,
        month_change=month_change,
        month_profit=month_profit,
        profit_rate=profit_rate,
        gift_rate=gift_rate,
        revenue_trend=revenue_trend,
        top_stores=top_stores,
        top_employees=top_employees,
        top_products=top_products,
    )


@router.get("/kpi", summary="获取 KPI 指标卡片数据")
async def get_kpi_cards(
    store_id: Optional[int] = Query(None, description="门店ID"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
):
    """
    获取 KPI 指标卡片数据（可自定义时间范围）
    
    返回:
    - 实收金额
    - 销售金额
    - 毛利
    - 毛利率
    - 开台数
    - 赠送金额
    """
    # 默认时间范围: 本月
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    
    # ============================================================
    # TODO: 调用 Dev A 的 StatsService
    # ============================================================
    
    # Mock 数据
    return {
        "success": True,
        "data": {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "metrics": {
                "actual_amount": 485000.0,
                "sales_amount": 520000.0,
                "profit": 198000.0,
                "profit_rate": 0.408,
                "order_count": 1250,
                "gift_amount": 35000.0,
                "gift_rate": 0.067,
            },
            "comparison": {
                "actual_change": 0.08,
                "profit_change": 0.12,
                "order_change": -0.03,
            }
        }
    }


@router.get("/trend", summary="获取趋势数据")
async def get_trend_data(
    metric: str = Query("actual", description="指标: actual/sales/profit/orders"),
    days: int = Query(30, ge=7, le=90, description="天数"),
    store_id: Optional[int] = Query(None, description="门店ID"),
):
    """
    获取指定指标的趋势数据（用于折线图）
    """
    today = date.today()
    
    # ============================================================
    # TODO: 调用 Dev A 的 StatsService
    # ============================================================
    
    # Mock 数据
    data = []
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        base_values = {
            "actual": 15000,
            "sales": 18000,
            "profit": 6000,
            "orders": 40,
        }
        base = base_values.get(metric, 15000)
        variation = (hash(d.strftime("%Y%m%d") + metric) % int(base * 0.5)) - int(base * 0.25)
        
        data.append({
            "date": d.strftime("%Y-%m-%d"),
            "value": round(base + variation, 2),
        })
    
    return {
        "success": True,
        "metric": metric,
        "data": data,
    }


@router.get("/ranking", summary="获取排行榜数据")
async def get_ranking_data(
    dimension: str = Query("store", description="维度: store/employee/product/room"),
    metric: str = Query("actual", description="指标: actual/sales/profit/qty"),
    limit: int = Query(10, ge=5, le=50, description="返回数量"),
    store_id: Optional[int] = Query(None, description="门店ID (当 dimension != store 时有效)"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
):
    """
    获取排行榜数据（用于柱状图）
    """
    # ============================================================
    # TODO: 调用 Dev A 的 StatsService
    # ============================================================
    
    # Mock 数据
    mock_data = {
        "store": [
            {"name": "万象城店", "value": 156000},
            {"name": "青年路店", "value": 142000},
            {"name": "高新店", "value": 128000},
            {"name": "曲江店", "value": 115000},
            {"name": "小寨店", "value": 98000},
        ],
        "employee": [
            {"name": "张三", "value": 45000},
            {"name": "李四", "value": 38000},
            {"name": "王五", "value": 32000},
            {"name": "赵六", "value": 28000},
            {"name": "钱七", "value": 24000},
        ],
        "product": [
            {"name": "百威啤酒", "value": 12500},
            {"name": "青岛啤酒", "value": 9800},
            {"name": "可乐", "value": 7600},
            {"name": "台湾香肠", "value": 5400},
            {"name": "薯条", "value": 4200},
        ],
        "room": [
            {"name": "K01", "value": 85000},
            {"name": "K07", "value": 72000},
            {"name": "K11", "value": 68000},
            {"name": "K18", "value": 55000},
            {"name": "派对包", "value": 120000},
        ],
    }
    
    data = mock_data.get(dimension, mock_data["store"])[:limit]
    
    # 添加排名
    result = [
        TopItem(rank=i + 1, name=item["name"], value=item["value"])
        for i, item in enumerate(data)
    ]
    
    return {
        "success": True,
        "dimension": dimension,
        "metric": metric,
        "data": result,
    }
