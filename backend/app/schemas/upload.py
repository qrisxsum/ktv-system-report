"""
文件上传相关 Schema 定义

参考文档: 
- docs/web界面5.md (1.2 节 - 文件上传与管理)
- docs/任务分配.md (5.2 节 - 校验反馈格式)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from .common import TableType, BatchStatus


# ============================================================
# 校验相关 Schema
# ============================================================

class RowError(BaseModel):
    """
    行级错误信息
    
    参考: docs/任务分配.md (5.2 节)
    """
    row_index: int = Field(..., description="原始 Excel 行号 (从 1 开始)")
    column: str = Field(..., description="出错列名 (如 '实收金额')")
    message: str = Field(..., description="错误信息 (如 '金额不平衡: 应收(100) != 实收(90) + 优惠(0)')")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="该行的原始数据快照 (用于前端展示)")


class ValidationResult(BaseModel):
    """
    校验结果
    
    由 Dev B (Cleaner) 产出，供 Dev C (API) 使用
    """
    is_valid: bool = Field(..., description="校验是否通过")
    summary: Dict[str, int] = Field(
        default_factory=lambda: {"total_rows": 0, "error_rows": 0, "warning_rows": 0},
        description="统计摘要"
    )
    errors: List[RowError] = Field(default_factory=list, description="错误详情列表")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


# ============================================================
# 解析结果 Schema (步骤1: 文件解析)
# ============================================================

class ParseResult(BaseModel):
    """
    文件解析结果 - 用于前端预览确认
    
    对应前端 Upload.vue 中的 parseResult
    """
    # 文件识别信息
    file_type: TableType = Field(..., description="表类型")
    file_type_name: str = Field(..., description="表类型中文名")
    
    # 门店信息
    store_id: Optional[int] = Field(None, description="门店ID (如果能识别)")
    store_name: str = Field(..., description="门店名称")
    
    # 数据概览
    data_month: Optional[str] = Field(None, description="数据月份 (YYYY-MM)")
    row_count: int = Field(..., description="数据行数")
    
    # 预览数据
    preview_rows: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="预览数据 (前5行)"
    )
    
    # 校验结果
    validation: ValidationResult = Field(..., description="校验结果")
    
    # 会话标识 (用于后续确认入库)
    session_id: str = Field(..., description="临时会话ID")


# ============================================================
# 入库结果 Schema (步骤2: 确认入库)
# ============================================================

class ImportSummary(BaseModel):
    """入库统计摘要"""
    row_count: int = Field(..., description="导入行数")
    sales_total: Optional[float] = Field(None, description="销售总额")
    actual_total: Optional[float] = Field(None, description="实收总额")
    balance_diff_count: int = Field(0, description="金额不平的行数")


class ImportResult(BaseModel):
    """
    入库结果
    
    参考: docs/web界面5.md (1.2 节 Response 示例)
    """
    batch_id: int = Field(..., description="批次ID")
    batch_no: str = Field(..., description="批次编号")
    status: BatchStatus = Field(..., description="入库状态")
    summary: ImportSummary = Field(..., description="入库统计摘要")
    message: str = Field("入库成功", description="结果消息")


# ============================================================
# 上传响应 Schema (统一响应)
# ============================================================

class UploadResponse(BaseModel):
    """
    上传接口统一响应
    """
    success: bool = True
    message: str = "操作成功"
    data: Optional[ParseResult | ImportResult] = None
    timestamp: datetime = Field(default_factory=datetime.now)

