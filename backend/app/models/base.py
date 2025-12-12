"""
模型基类定义

提供通用的时间戳字段和基类
"""
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class TimestampMixin:
    """
    时间戳混入类
    
    为模型提供 created_at 和 updated_at 字段
    """
    created_at = Column(
        DateTime,
        default=datetime.now,
        server_default=func.now(),
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        server_default=func.now(),
        server_onupdate=func.now(),
        comment="更新时间"
    )


# 导出 Base 供其他模型使用
__all__ = ["Base", "TimestampMixin"]

