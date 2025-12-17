"""
数据查询与统计相关 Schema 定义

参考文档:
- docs/web界面5.md (1.3 节 - 数据查询与聚合)
- docs/聚合4.md (第二章 - 聚合策略)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime

from .common import TimeGranularity, Dimension, TableType


# ============================================================
# 查询参数 Schema
# ============================================================

class QueryFilters(BaseModel):
    """
    通用查询参数
    
    参考: docs/web界面5.md (1.3 节 Query Params)
    """
    # 表类型
    table: TableType = Field(TableType.BOOKING, description="查询哪张事实表")
    
    # 时间范围
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    
    # 门店筛选
    store_id: Optional[int] = Field(None, description="门店ID (可选)")
    
    # 聚合维度
    dimension: Dimension = Field(Dimension.DATE, description="聚合维度")
    
    # 时间粒度 (仅当 dimension=date 时有效)
    granularity: TimeGranularity = Field(
        TimeGranularity.DAY, 
        description="时间粒度，仅当 dimension=date 时有效"
    )
    
    # 分页
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


# ============================================================
# 统计结果 Schema
# ============================================================

class StatsItem(BaseModel):
    """
    统计项
    
    参考: docs/web界面5.md (1.3 节 Response 示例)
    """
    dimension_key: str = Field(..., description="维度键 (如日期、门店名等)")
    dimension_label: Optional[str] = Field(None, description="维度显示名称")
    
    # booking 表核心指标
    sales: float = Field(0, description="销售金额 (booking)")
    actual: float = Field(0, description="实收金额")
    performance: Optional[float] = Field(None, description="基本业绩")
    booking_qty: Optional[int] = Field(None, description="订台数")
    orders: Optional[int] = Field(None, description="通用订单/开台数")
    
    # room 表指标
    gmv: Optional[float] = Field(None, description="GMV (应收金额)")
    room_discount: Optional[float] = Field(None, description="包厢折扣")
    beverage_discount: Optional[float] = Field(None, description="酒水折扣")
    order_count: Optional[int] = Field(None, description="订单数/开台数")
    duration: Optional[int] = Field(None, description="包厢时长(分钟)")
    
    # sales 表指标
    sales_qty: Optional[int] = Field(None, description="销售数量")
    sales_amount: Optional[float] = Field(None, description="销售金额 (sales)")
    cost: Optional[float] = Field(None, description="成本")
    profit: Optional[float] = Field(None, description="毛利")
    
    # 赠送相关 (通用)
    gift_qty: Optional[int] = Field(None, description="赠送数量")
    gift_amount: Optional[float] = Field(None, description="赠送金额")
    
    # 扣减项统计
    discount_amount: Optional[float] = Field(None, description="折扣金额")
    credit_amount: Optional[float] = Field(None, description="挂账金额")


class StatsMeta(BaseModel):
    """统计元信息"""
    total_sales: float = Field(0, description="销售总额")
    total_actual: float = Field(0, description="实收总额")
    total_profit: Optional[float] = Field(None, description="毛利总额")
    total_records: int = Field(0, description="记录总数")


class StatsResponse(BaseModel):
    """
    统计查询响应
    
    参考: docs/web界面5.md (1.3 节)
    """
    success: bool = True
    data: List[StatsItem] = Field(default_factory=list, description="统计数据列表")
    meta: StatsMeta = Field(default_factory=StatsMeta, description="汇总信息")
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================
# Dashboard 相关 Schema
# ============================================================

class TrendItem(BaseModel):
    """趋势数据项"""
    date: str = Field(..., description="日期")
    value: float = Field(..., description="数值")


class TopItem(BaseModel):
    """排行榜数据项"""
    rank: int = Field(..., description="排名")
    name: str = Field(..., description="名称")
    value: float = Field(..., description="数值")


class DashboardSummary(BaseModel):
    """
    首页看板汇总数据
    
    参考: docs/web界面5.md (2.2.1 节 - 仪表盘)
    """
    # 核心指标卡片
    yesterday_actual: float = Field(0, description="昨日实收")
    yesterday_change: float = Field(0, description="昨日环比变化率")
    
    month_actual: float = Field(0, description="本月实收累计")
    month_change: float = Field(0, description="本月同比变化率")
    
    month_profit: float = Field(0, description="本月毛利累计")
    profit_rate: float = Field(0, description="毛利率")
    
    gift_rate: float = Field(0, description="赠送率")
    
    # 趋势数据 (近30天)
    revenue_trend: List[TrendItem] = Field(default_factory=list, description="营收趋势")
    
    # 排行榜
    top_stores: List[TopItem] = Field(default_factory=list, description="Top 5 门店")
    top_employees: List[TopItem] = Field(default_factory=list, description="Top 5 员工")
    top_products: List[TopItem] = Field(default_factory=list, description="Top 5 商品")

