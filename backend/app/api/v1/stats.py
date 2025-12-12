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
"""

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Depends

from app.schemas import (
    TableType,
    Dimension,
    TimeGranularity,
    QueryFilters,
    StatsResponse,
    StatsItem,
    StatsMeta,
    DashboardSummary,
    TrendItem,
    TopItem,
)

router = APIRouter()


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
):
    """
    通用聚合查询接口
    
    根据不同参数组合返回不同维度的统计数据
    
    参考: docs/web界面5.md (1.3 节)
    """
    # ============================================================
    # TODO: 调用 Dev A 的 StatsService
    # from app.services.stats import StatsService
    # 
    # stats_service = StatsService()
    # result = stats_service.query_stats(
    #     granularity=granularity,
    #     dimension=dimension,
    #     start_date=start_date,
    #     end_date=end_date,
    #     store_id=store_id,
    #     table_type=table,
    # )
    # ============================================================
    
    # Mock 数据 (等待 Dev A 实现后替换)
    mock_data = []
    
    if dimension == Dimension.DATE:
        # 按日期聚合
        current = start_date
        while current <= end_date:
            if granularity == TimeGranularity.DAY:
                key = current.strftime("%Y-%m-%d")
            elif granularity == TimeGranularity.WEEK:
                key = current.strftime("%Y-W%W")
            else:  # MONTH
                key = current.strftime("%Y-%m")
            
            mock_data.append(StatsItem(
                dimension_key=key,
                sales=round(15000 + (hash(key) % 10000), 2),
                actual=round(14000 + (hash(key) % 9000), 2),
                cost=round(5000 + (hash(key) % 3000), 2),
                profit=round(9000 + (hash(key) % 6000), 2),
                gift_qty=hash(key) % 50,
                gift_amount=round(500 + (hash(key) % 1000), 2),
                order_count=10 + (hash(key) % 20),
            ))
            
            if granularity == TimeGranularity.DAY:
                current += timedelta(days=1)
            elif granularity == TimeGranularity.WEEK:
                current += timedelta(weeks=1)
            else:
                # 简化处理，按30天算一个月
                current += timedelta(days=30)
                if current > end_date:
                    break
    
    elif dimension == Dimension.STORE:
        # 按门店聚合
        stores = ["万象城店", "青年路店", "高新店", "曲江店"]
        for i, store in enumerate(stores):
            mock_data.append(StatsItem(
                dimension_key=str(i + 1),
                dimension_label=store,
                sales=round(50000 + i * 10000, 2),
                actual=round(48000 + i * 9500, 2),
                profit=round(20000 + i * 4000, 2),
                order_count=100 + i * 30,
            ))
    
    elif dimension == Dimension.EMPLOYEE:
        # 按员工聚合
        employees = ["张三", "李四", "王五", "赵六", "钱七"]
        for i, emp in enumerate(employees):
            mock_data.append(StatsItem(
                dimension_key=str(i + 1),
                dimension_label=emp,
                sales=round(20000 - i * 2000, 2),
                actual=round(19000 - i * 1900, 2),
                booking_qty=20 - i * 3,
            ))
    
    elif dimension == Dimension.PRODUCT:
        # 按商品聚合 (酒水销售表)
        products = ["百威啤酒", "青岛啤酒", "可乐", "台湾香肠", "薯条"]
        for i, prod in enumerate(products):
            mock_data.append(StatsItem(
                dimension_key=str(i + 1),
                dimension_label=prod,
                sales=round(8000 - i * 1000, 2),
                actual=round(8000 - i * 1000, 2),
                cost=round(3000 - i * 300, 2),
                profit=round(5000 - i * 700, 2),
                gift_qty=10 + i * 2,
                gift_amount=round(200 + i * 50, 2),
            ))
    
    # 计算汇总
    total_sales = sum(item.sales for item in mock_data)
    total_actual = sum(item.actual for item in mock_data)
    total_profit = sum(item.profit or 0 for item in mock_data)
    
    return StatsResponse(
        success=True,
        data=mock_data,
        meta=StatsMeta(
            total_sales=round(total_sales, 2),
            total_actual=round(total_actual, 2),
            total_profit=round(total_profit, 2) if total_profit else None,
            total_records=len(mock_data),
        ),
    )


# ============================================================
# Dashboard 接口
# ============================================================

@router.get("/dashboard/summary", response_model=DashboardSummary, summary="首页看板数据")
async def get_dashboard_summary(
    store_id: Optional[int] = Query(None, description="门店ID (不传则汇总所有门店)"),
):
    """
    获取首页看板汇总数据
    
    参考: docs/web界面5.md (2.2.1 节)
    """
    # ============================================================
    # TODO: 调用 Dev A 的 StatsService 获取基础数据
    # 然后在这里计算衍生指标
    # ============================================================
    
    # Mock 数据
    today = datetime.now()
    
    # 生成趋势数据 (近30天)
    revenue_trend = []
    for i in range(30, 0, -1):
        d = today - timedelta(days=i)
        revenue_trend.append(TrendItem(
            date=d.strftime("%Y-%m-%d"),
            value=round(12000 + (hash(d.strftime("%Y%m%d")) % 8000), 2),
        ))
    
    # Top 5 门店
    top_stores = [
        TopItem(rank=1, name="万象城店", value=156000),
        TopItem(rank=2, name="青年路店", value=142000),
        TopItem(rank=3, name="高新店", value=128000),
        TopItem(rank=4, name="曲江店", value=115000),
        TopItem(rank=5, name="小寨店", value=98000),
    ]
    
    # Top 5 员工
    top_employees = [
        TopItem(rank=1, name="张三", value=45000),
        TopItem(rank=2, name="李四", value=38000),
        TopItem(rank=3, name="王五", value=32000),
        TopItem(rank=4, name="赵六", value=28000),
        TopItem(rank=5, name="钱七", value=24000),
    ]
    
    # Top 5 商品
    top_products = [
        TopItem(rank=1, name="百威啤酒", value=12500),
        TopItem(rank=2, name="青岛啤酒", value=9800),
        TopItem(rank=3, name="可乐", value=7600),
        TopItem(rank=4, name="台湾香肠", value=5400),
        TopItem(rank=5, name="薯条", value=4200),
    ]
    
    return DashboardSummary(
        yesterday_actual=18500.00,
        yesterday_change=0.12,  # 12% 增长
        month_actual=485000.00,
        month_change=0.08,  # 8% 增长
        month_profit=198000.00,
        profit_rate=0.408,  # 40.8%
        gift_rate=0.05,  # 5%
        revenue_trend=revenue_trend,
        top_stores=top_stores,
        top_employees=top_employees,
        top_products=top_products,
    )

