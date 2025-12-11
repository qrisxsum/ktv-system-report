"""
门店管理接口 (基础数据)

参考文档:
- docs/web界面5.md (1.4 节)
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Query

router = APIRouter()


# ============================================================
# Schema 定义
# ============================================================

class StoreInfo(BaseModel):
    """门店信息"""
    id: int = Field(..., description="门店ID")
    name: str = Field(..., description="门店名称")
    is_active: bool = Field(True, description="是否启用")


class StoreListResponse(BaseModel):
    """门店列表响应"""
    success: bool = True
    data: List[StoreInfo] = Field(default_factory=list)


# ============================================================
# Mock 数据 (等待 Dev A 实现数据库后替换)
# ============================================================

MOCK_STORES = [
    StoreInfo(id=1, name="万象城店", is_active=True),
    StoreInfo(id=2, name="青年路店", is_active=True),
    StoreInfo(id=3, name="高新店", is_active=True),
    StoreInfo(id=4, name="曲江店", is_active=True),
    StoreInfo(id=5, name="小寨店", is_active=False),
]


# ============================================================
# API 接口
# ============================================================

@router.get("", response_model=StoreListResponse, summary="获取门店列表")
async def list_stores(
    is_active: Optional[bool] = Query(None, description="是否只返回启用的门店"),
):
    """
    获取门店列表
    
    参考: docs/web界面5.md (1.4 节)
    """
    # ============================================================
    # TODO: 调用数据库查询 (Dev A 负责)
    # from app.services.store import StoreService
    # stores = store_service.list_stores(is_active)
    # ============================================================
    
    result = MOCK_STORES.copy()
    
    if is_active is not None:
        result = [s for s in result if s.is_active == is_active]
    
    return StoreListResponse(
        success=True,
        data=result,
    )


@router.get("/{store_id}", response_model=StoreInfo, summary="获取门店详情")
async def get_store(store_id: int):
    """获取单个门店信息"""
    for store in MOCK_STORES:
        if store.id == store_id:
            return store
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="门店不存在")

