"""
门店管理接口 (基础数据)

参考文档:
- docs/web界面5.md (1.4 节)

对接: Dev A 的数据库模型 (DimStore)
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_manager
from app.models.dims import DimStore

router = APIRouter()


# ============================================================
# Schema 定义
# ============================================================

class StoreInfo(BaseModel):
    """门店信息"""
    id: int = Field(..., description="门店ID")
    name: str = Field(..., description="门店名称")
    is_active: bool = Field(True, description="是否启用")
    
    class Config:
        from_attributes = True


class StoreListResponse(BaseModel):
    """门店列表响应"""
    success: bool = True
    data: List[StoreInfo] = Field(default_factory=list)


# ============================================================
# API 接口
# ============================================================

@router.get("", response_model=StoreListResponse, summary="获取门店列表")
async def list_stores(
    is_active: Optional[bool] = Query(None, description="是否只返回启用的门店"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取门店列表

    参考: docs/web界面5.md (1.4 节)
    """
    # 构建查询
    query = db.query(DimStore)

    # 根据用户角色过滤门店权限
    if current_user["role"] == "manager":
        # 店长只能看到自己的门店
        query = query.filter(DimStore.id == current_user["store_id"])
    
    # 应用筛选条件
    if is_active is not None:
        query = query.filter(DimStore.is_active == is_active)
    
    # 按 ID 排序
    stores = query.order_by(DimStore.id).all()
    
    # 转换为 Schema
    result = [
        StoreInfo(
            id=store.id,
            name=store.store_name,
            is_active=store.is_active if store.is_active is not None else True,
        )
        for store in stores
    ]
    
    return StoreListResponse(
        success=True,
        data=result,
    )


@router.get("/{store_id}", response_model=StoreInfo, summary="获取门店详情")
async def get_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """获取单个门店信息"""
    # 检查用户是否有权限访问该门店
    if current_user["role"] == "manager" and store_id != current_user["store_id"]:
        raise HTTPException(
            status_code=403,
            detail="无权限访问其他门店信息"
        )

    store = db.query(DimStore).filter(DimStore.id == store_id).first()

    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    
    return StoreInfo(
        id=store.id,
        name=store.store_name,
        is_active=store.is_active if store.is_active is not None else True,
    )

