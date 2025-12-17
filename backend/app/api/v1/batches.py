"""
批次管理接口

参考文档:
- docs/web界面5.md (1.2 节, 2.2.4 节)

对接: Dev A (ImporterService) + 数据库 (MetaFileBatch, DimStore)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.schemas import (
    TableType,
    BatchStatus,
    BatchInfo,
    BatchList,
    BatchDetail,
)
from app.schemas.batch import BatchDeleteResponse
from app.core.database import get_db
from app.core.security import get_current_manager, get_current_admin
from app.models.meta import MetaFileBatch
from app.models.dims import DimStore
from app.services.importer import ImporterService

router = APIRouter()


# ============================================================
# 表类型名称映射
# ============================================================

TABLE_TYPE_NAMES = {
    TableType.BOOKING: "预订汇总表",
    TableType.ROOM: "包厢开台分析表",
    TableType.SALES: "酒水销售分析表",
    "booking": "预订汇总表",
    "room": "包厢开台分析表",
    "sales": "酒水销售分析表",
}


def _convert_to_batch_info(batch: MetaFileBatch, store_name: Optional[str] = None) -> BatchInfo:
    """将 ORM 对象转换为 BatchInfo Schema"""
    # 转换 table_type 字符串为枚举
    try:
        table_type_enum = TableType(batch.table_type)
    except ValueError:
        table_type_enum = TableType.BOOKING
    
    # 转换 status 字符串为枚举
    try:
        status_enum = BatchStatus(batch.status)
    except ValueError:
        status_enum = BatchStatus.PENDING
    
    return BatchInfo(
        id=batch.id,
        batch_no=batch.batch_no,
        file_name=batch.file_name,
        store_id=batch.store_id,
        store_name=store_name or f"门店{batch.store_id}",
        table_type=table_type_enum,
        table_type_name=TABLE_TYPE_NAMES.get(batch.table_type, "未知"),
        status=status_enum,
        row_count=batch.row_count or 0,
        created_at=batch.created_at or datetime.now(),
    )


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
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取上传批次历史

    参考: docs/web界面5.md (1.2 节)
    """
    # 根据用户角色过滤store_id权限
    if current_user["role"] == "manager":
        # 店长只能查看自己门店的数据
        if store_id is None:
            store_id = current_user["store_id"]
        elif store_id != current_user["store_id"]:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="无权限访问其他门店数据"
            )

    # 构建查询
    query = db.query(MetaFileBatch)
    
    # 应用筛选条件
    if store_id:
        query = query.filter(MetaFileBatch.store_id == store_id)
    if table_type:
        query = query.filter(MetaFileBatch.table_type == table_type.value)
    if status:
        query = query.filter(MetaFileBatch.status == status.value)
    
    # 获取总数
    total = query.count()
    
    # 分页并排序（按创建时间倒序）
    offset = (page - 1) * page_size
    batches = (
        query
        .order_by(desc(MetaFileBatch.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    # 批量获取门店名称
    store_ids = list(set(b.store_id for b in batches))
    stores = db.query(DimStore).filter(DimStore.id.in_(store_ids)).all() if store_ids else []
    store_map = {s.id: s.store_name for s in stores}
    
    # 转换为 Schema
    result = [
        _convert_to_batch_info(batch, store_map.get(batch.store_id))
        for batch in batches
    ]
    
    return BatchList(
        success=True,
        data=result,
        total=total,
    )


@router.get("/{batch_id}", response_model=BatchDetail, summary="获取批次详情")
async def get_batch_detail(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取批次详情（含错误日志）
    """
    batch = db.query(MetaFileBatch).filter(MetaFileBatch.id == batch_id).first()

    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 检查用户是否有权限访问该批次
    if current_user["role"] == "manager" and batch.store_id != current_user["store_id"]:
        raise HTTPException(
            status_code=403,
            detail="无权限访问其他门店数据"
        )
    
    # 获取门店名称
    store = db.query(DimStore).filter(DimStore.id == batch.store_id).first()
    store_name = store.store_name if store else f"门店{batch.store_id}"
    
    # 转换为 BatchInfo
    batch_info = _convert_to_batch_info(batch, store_name)
    
    return BatchDetail(
        **batch_info.model_dump(),
        error_log=batch.error_log,
        sales_total=None,  # TODO: 从关联的事实表聚合计算
        actual_total=None,
    )


@router.delete("/{batch_id}", response_model=BatchDeleteResponse, summary="删除批次")
async def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),  # 删除批次需要管理员权限
):
    """
    删除批次（回滚数据）
    
    参考: docs/web界面5.md (1.2 节)
    """
    # 先检查批次是否存在
    batch = db.query(MetaFileBatch).filter(MetaFileBatch.id == batch_id).first()

    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 管理员可以删除任何批次，这里不需要额外的权限检查
    
    batch_no = batch.batch_no
    row_count = batch.row_count or 0
    
    # 调用 ImporterService 删除批次及其关联数据
    importer = ImporterService(db)
    try:
        deleted = importer.delete_batch(batch_id)
        
        if deleted:
            return BatchDeleteResponse(
                success=True,
                message=f"批次 {batch_no} 已删除，回滚 {row_count} 条数据",
                batch_id=batch_id,
                deleted_rows=row_count,
            )
        else:
            raise HTTPException(status_code=500, detail="删除批次失败")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除批次失败: {str(e)}")

