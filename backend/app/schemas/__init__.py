"""
Pydantic Schemas - API 数据契约定义

Dev C 负责定义 "前端需要什么数据"
"""

from .common import (
    TimeGranularity,
    Dimension,
    TableType,
    BatchStatus,
    ResponseBase,
)
from .upload import (
    UploadResponse,
    ParseResult,
    ValidationResult,
    RowError,
    ImportResult,
    ImportSummary,
)
from .stats import (
    QueryFilters,
    StatsResponse,
    StatsItem,
    DashboardSummary,
    StatsMeta,
    TrendItem,
    TopItem,
)
from .batch import (
    BatchInfo,
    BatchList,
    BatchDetail,
)
from .user import (
    CreateManagerRequest,
    UpdateManagerRequest,
    ResetPasswordRequest,
    ManagerInfo,
    ManagerListResponse,
    ManagerDetailResponse,
    ManagerCreateResponse,
    ManagerUpdateResponse,
    ManagerDeleteResponse,
    ManagerToggleStatusResponse,
    ResetPasswordResponse,
)

__all__ = [
    # Common
    "TimeGranularity",
    "Dimension",
    "TableType",
    "BatchStatus",
    "ResponseBase",
    # Upload
    "UploadResponse",
    "ParseResult",
    "ValidationResult",
    "RowError",
    "ImportResult",
    "ImportSummary",
    # Stats
    "QueryFilters",
    "StatsResponse",
    "StatsItem",
    "DashboardSummary",
    "StatsMeta",
    "TrendItem",
    "TopItem",
    # Batch
    "BatchInfo",
    "BatchList",
    "BatchDetail",
    # User
    "CreateManagerRequest",
    "UpdateManagerRequest",
    "ResetPasswordRequest",
    "ManagerInfo",
    "ManagerListResponse",
    "ManagerDetailResponse",
    "ManagerCreateResponse",
    "ManagerUpdateResponse",
    "ManagerDeleteResponse",
    "ManagerToggleStatusResponse",
    "ResetPasswordResponse",
]
