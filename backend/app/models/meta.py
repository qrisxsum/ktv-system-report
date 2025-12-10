"""
元数据表模型

包含文件批次管理等系统元数据
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Index
from sqlalchemy.sql import func

from app.core.database import Base


class MetaFileBatch(Base):
    """
    文件导入批次表
    
    用于记录每次文件导入的状态，支持幂等性和回滚
    """
    __tablename__ = "meta_file_batch"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
    batch_no = Column(String(50), unique=True, nullable=False, comment="唯一批次号 (YYYYMMDD_Store_Type)")
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), comment="文件存储路径")
    file_hash = Column(String(64), comment="文件MD5哈希(防重复)")
    store_id = Column(Integer, nullable=False, index=True, comment="关联门店ID")
    table_type = Column(String(50), nullable=False, comment="表类型: booking/room/sales")
    
    # 数据范围
    data_start_date = Column(DateTime, comment="数据开始日期")
    data_end_date = Column(DateTime, comment="数据结束日期")
    
    # 状态管理
    status = Column(String(20), default="pending", comment="状态: pending/processing/success/failed")
    row_count = Column(Integer, default=0, comment="导入行数")
    error_count = Column(Integer, default=0, comment="错误行数")
    error_log = Column(Text, comment="错误日志(JSON格式)")
    
    # 操作信息
    upload_user = Column(String(50), comment="上传人")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index("idx_batch_no", "batch_no", unique=True),
        Index("idx_store_date", "store_id", "created_at"),
        Index("idx_status", "status"),
        Index("idx_file_hash", "file_hash"),
        {"comment": "文件导入批次管理表"}
    )
    
    def __repr__(self):
        return f"<MetaFileBatch(id={self.id}, batch_no={self.batch_no}, status={self.status})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "batch_no": self.batch_no,
            "file_name": self.file_name,
            "store_id": self.store_id,
            "table_type": self.table_type,
            "status": self.status,
            "row_count": self.row_count,
            "error_count": self.error_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

