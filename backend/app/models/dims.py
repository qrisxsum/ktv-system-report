"""
维度表模型

包含门店、员工、包厢、商品、支付方式等维度数据
"""
from sqlalchemy import Column, Integer, String, Boolean, Index, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class DimStore(Base):
    """
    门店维度表
    
    存储门店基本信息，用于多门店数据隔离
    """
    __tablename__ = "dim_store"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="代理键")
    store_code = Column(String(20), unique=True, comment="门店编码")
    store_name = Column(String(100), nullable=False, comment="门店名(标准化)")
    original_name = Column(String(100), comment="原始门店名(用于匹配)")
    region = Column(String(50), comment="所属区域/城市")
    address = Column(String(200), comment="门店地址")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index("idx_store_name", "store_name", unique=True),
        Index("idx_store_code", "store_code"),
        {"comment": "门店维度表"}
    )
    
    def __repr__(self):
        return f"<DimStore(id={self.id}, name={self.store_name})>"


class DimEmployee(Base):
    """
    员工维度表
    
    存储员工/订房人信息
    """
    __tablename__ = "dim_employee"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="代理键")
    store_id = Column(Integer, nullable=False, index=True, comment="关联门店")
    name = Column(String(50), nullable=False, comment="员工姓名")
    department = Column(String(50), comment="部门")
    position = Column(String(50), comment="职位")
    is_active = Column(Boolean, default=True, comment="是否在职")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index("idx_store_name", "store_id", "name"),
        {"comment": "员工维度表"}
    )
    
    def __repr__(self):
        return f"<DimEmployee(id={self.id}, name={self.name})>"


class DimRoom(Base):
    """
    包厢维度表
    
    存储包厢基本信息
    """
    __tablename__ = "dim_room"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="代理键")
    store_id = Column(Integer, nullable=False, index=True, comment="关联门店")
    room_no = Column(String(50), nullable=False, comment="包厢号")
    room_name = Column(String(50), comment="包厢名称")
    room_type = Column(String(50), comment="包厢类型")
    area_name = Column(String(50), comment="区域名称")
    capacity = Column(Integer, comment="容纳人数")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index("idx_store_room", "store_id", "room_no", unique=True),
        Index("idx_room_type", "room_type"),
        {"comment": "包厢维度表"}
    )
    
    def __repr__(self):
        return f"<DimRoom(id={self.id}, room_no={self.room_no})>"


class DimProduct(Base):
    """
    商品维度表
    
    存储酒水/商品信息
    """
    __tablename__ = "dim_product"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="代理键")
    store_id = Column(Integer, nullable=False, index=True, comment="关联门店")
    name = Column(String(100), nullable=False, comment="商品名称")
    category = Column(String(50), comment="商品分类")
    unit = Column(String(20), comment="单位")
    price = Column(Integer, comment="单价(分)")
    cost = Column(Integer, comment="成本(分)")
    is_active = Column(Boolean, default=True, comment="是否在售")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index("idx_store_product", "store_id", "name"),
        Index("idx_category", "category"),
        {"comment": "商品维度表"}
    )
    
    def __repr__(self):
        return f"<DimProduct(id={self.id}, name={self.name})>"


class DimPaymentMethod(Base):
    """
    支付方式维度表
    
    用于动态归类支付方式（收入类/权益类/成本类）
    """
    __tablename__ = "dim_payment_method"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="代理键")
    code = Column(String(50), unique=True, nullable=False, comment="支付方式代码")
    name = Column(String(50), nullable=False, comment="支付方式名称")
    category = Column(String(20), nullable=False, comment="分类: income/equity/cost")
    is_core = Column(Boolean, default=False, comment="是否核心字段(独立建列)")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    __table_args__ = (
        Index("idx_code", "code", unique=True),
        Index("idx_category", "category"),
        {"comment": "支付方式维度表"}
    )
    
    def __repr__(self):
        return f"<DimPaymentMethod(code={self.code}, name={self.name})>"


# 导出所有维度模型
__all__ = [
    "DimStore",
    "DimEmployee",
    "DimRoom",
    "DimProduct",
    "DimPaymentMethod",
]

