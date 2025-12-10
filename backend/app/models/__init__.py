"""
数据库模型

导出所有模型供其他模块使用
"""
from app.core.database import Base

# 元数据表
from app.models.meta import MetaFileBatch

# 维度表
from app.models.dims import (
    DimStore,
    DimEmployee,
    DimRoom,
    DimProduct,
    DimPaymentMethod,
)

# 事实表
from app.models.facts import (
    FactBooking,
    FactRoom,
    FactSales,
)


__all__ = [
    # 基类
    "Base",
    
    # 元数据表
    "MetaFileBatch",
    
    # 维度表
    "DimStore",
    "DimEmployee",
    "DimRoom",
    "DimProduct",
    "DimPaymentMethod",
    
    # 事实表
    "FactBooking",
    "FactRoom",
    "FactSales",
]

