"""
通用枚举和基础类定义

参考文档: docs/任务分配.md (5.3 节 - 枚举约束)
"""

from enum import StrEnum
from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime


# ============================================================
# 枚举定义 - 严禁使用裸字符串传递关键参数
# ============================================================

class TimeGranularity(StrEnum):
    """时间粒度枚举"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class Dimension(StrEnum):
    """聚合维度枚举"""
    DATE = "date"
    STORE = "store"
    EMPLOYEE = "employee"
    ROOM = "room"
    ROOM_TYPE = "room_type"
    PRODUCT = "product"


class TableType(StrEnum):
    """表类型枚举"""
    BOOKING = "booking"     # 预订汇总表
    ROOM = "room"           # 包厢开台分析表
    SALES = "sales"         # 酒水销售分析表


class BatchStatus(StrEnum):
    """批次状态枚举"""
    PENDING = "pending"     # 处理中
    SUCCESS = "success"     # 成功
    FAILED = "failed"       # 失败
    WARNING = "warning"     # 有警告但成功


# ============================================================
# 基础响应模型
# ============================================================

class ResponseBase(BaseModel):
    """API 响应基类"""
    success: bool = True
    message: str = "操作成功"
    timestamp: datetime = None
    
    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class PaginationMeta(BaseModel):
    """分页元信息"""
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Any] = None

