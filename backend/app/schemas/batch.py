"""
批次管理相关 Schema 定义

参考文档:
- docs/web界面5.md (1.2 节 - 文件上传与管理)
- docs/入库模型3.md (3.1 节 - 批次表)
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from .common import TableType, BatchStatus


class BatchInfo(BaseModel):
    """
    批次基础信息
    
    对应 meta_file_batch 表
    """
    id: int = Field(..., description="批次ID")
    batch_no: str = Field(..., description="批次编号 (YYYYMMDD_Store_Type)")
    file_name: str = Field(..., description="原始文件名")
    
    # 关联信息
    store_id: int = Field(..., description="门店ID")
    store_name: Optional[str] = Field(None, description="门店名称")
    
    # 表类型
    table_type: TableType = Field(..., description="表类型")
    table_type_name: Optional[str] = Field(None, description="表类型中文名")
    
    # 状态
    status: BatchStatus = Field(..., description="批次状态")
    row_count: int = Field(0, description="导入行数")
    
    # 时间
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True  # 支持从 ORM 对象转换


class BatchDetail(BatchInfo):
    """
    批次详情 (包含错误日志)
    """
    error_log: Optional[str] = Field(None, description="错误日志 (JSON格式)")
    
    # 统计摘要
    sales_total: Optional[float] = Field(None, description="销售总额")
    actual_total: Optional[float] = Field(None, description="实收总额")


class BatchList(BaseModel):
    """
    批次列表响应
    """
    success: bool = True
    data: List[BatchInfo] = Field(default_factory=list, description="批次列表")
    total: int = Field(0, description="总数")
    timestamp: datetime = Field(default_factory=datetime.now)


class BatchDeleteResponse(BaseModel):
    """
    批次删除响应
    """
    success: bool = True
    message: str = "批次删除成功，数据已回滚"
    batch_id: int = Field(..., description="被删除的批次ID")
    deleted_rows: int = Field(0, description="回滚的数据行数")

