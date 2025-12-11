"""
批次管理接口

参考文档:
- docs/web界面5.md (1.2 节, 2.2.4 节)
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from app.schemas import (
    TableType,
    BatchStatus,
    BatchInfo,
    BatchList,
    BatchDetail,
)
from app.schemas.batch import BatchDeleteResponse

router = APIRouter()


# ============================================================
# Mock 数据 (等待 Dev A 实现数据库后替换)
# ============================================================

TABLE_TYPE_NAMES = {
    TableType.BOOKING: "预订汇总表",
    TableType.ROOM: "包厢开台分析表",
    TableType.SALES: "酒水销售分析表",
}

MOCK_BATCHES = [
    BatchInfo(
        id=1,
        batch_no="20251208_万象城店_room",
        file_name="万象城店_包厢开台分析_202512.xlsx",
        store_id=1,
        store_name="万象城店",
        table_type=TableType.ROOM,
        table_type_name=TABLE_TYPE_NAMES[TableType.ROOM],
        status=BatchStatus.SUCCESS,
        row_count=78,
        created_at=datetime.now() - timedelta(hours=2),
    ),
    BatchInfo(
        id=2,
        batch_no="20251208_万象城店_sales",
        file_name="万象城店_酒水销售分析_202512.xlsx",
        store_id=1,
        store_name="万象城店",
        table_type=TableType.SALES,
        table_type_name=TABLE_TYPE_NAMES[TableType.SALES],
        status=BatchStatus.SUCCESS,
        row_count=34,
        created_at=datetime.now() - timedelta(hours=3),
    ),
    BatchInfo(
        id=3,
        batch_no="20251208_青年路店_booking",
        file_name="青年路店_预订汇总_202512.xlsx",
        store_id=2,
        store_name="青年路店",
        table_type=TableType.BOOKING,
        table_type_name=TABLE_TYPE_NAMES[TableType.BOOKING],
        status=BatchStatus.SUCCESS,
        row_count=18,
        created_at=datetime.now() - timedelta(hours=4),
    ),
]


# ============================================================
# API 接口
# ============================================================

@router.get("", response_model=BatchList, summary="获取批次列表")
async def list_batches(
    store_id: Optional[int] = Query(None, description="门店ID"),
    table_type: Optional[TableType] = Query(None, description="表类型"),
    status: Optional[BatchStatus] = Query(None, description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取上传批次历史
    
    参考: docs/web界面5.md (1.2 节)
    """
    # ============================================================
    # TODO: 调用数据库查询 (Dev A 负责)
    # from app.services.importer import ImporterService
    # importer = ImporterService()
    # batches = importer.list_batches(store_id, table_type, status, page, page_size)
    # ============================================================
    
    # Mock 数据筛选
    result = MOCK_BATCHES.copy()
    
    if store_id:
        result = [b for b in result if b.store_id == store_id]
    if table_type:
        result = [b for b in result if b.table_type == table_type]
    if status:
        result = [b for b in result if b.status == status]
    
    return BatchList(
        success=True,
        data=result,
        total=len(result),
    )


@router.get("/{batch_id}", response_model=BatchDetail, summary="获取批次详情")
async def get_batch_detail(batch_id: int):
    """
    获取批次详情（含错误日志）
    """
    # Mock 数据
    for batch in MOCK_BATCHES:
        if batch.id == batch_id:
            return BatchDetail(
                **batch.model_dump(),
                error_log=None,
                sales_total=50000.00,
                actual_total=48000.00,
            )
    
    raise HTTPException(status_code=404, detail="批次不存在")


@router.delete("/{batch_id}", response_model=BatchDeleteResponse, summary="删除批次")
async def delete_batch(batch_id: int):
    """
    删除批次（回滚数据）
    
    参考: docs/web界面5.md (1.2 节)
    """
    # ============================================================
    # TODO: 调用 Dev A 的 Importer 进行回滚
    # from app.services.importer import ImporterService
    # importer = ImporterService()
    # deleted_rows = importer.delete_batch(batch_id)
    # ============================================================
    
    # Mock 数据
    for batch in MOCK_BATCHES:
        if batch.id == batch_id:
            deleted_rows = batch.row_count
            MOCK_BATCHES.remove(batch)
            
            return BatchDeleteResponse(
                success=True,
                message=f"批次 {batch.batch_no} 已删除，回滚 {deleted_rows} 条数据",
                batch_id=batch_id,
                deleted_rows=deleted_rows,
            )
    
    raise HTTPException(status_code=404, detail="批次不存在")

