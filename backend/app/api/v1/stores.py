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
from app.core.security import get_current_manager, get_current_admin
from app.models.dims import DimStore
import uuid

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


class CreateStoreRequest(BaseModel):
    """创建门店请求"""
    store_name: str = Field(..., min_length=1, max_length=100, description="门店名称")
    region: Optional[str] = Field(None, max_length=50, description="所属区域/城市")
    address: Optional[str] = Field(None, max_length=200, description="门店地址")


class StoreListResponse(BaseModel):
    """门店列表响应"""
    success: bool = True
    data: List[StoreInfo] = Field(default_factory=list)


class StoreCreateResponse(BaseModel):
    """创建门店响应"""
    success: bool = True
    message: str = "创建成功"
    data: StoreInfo


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


@router.post("", response_model=StoreCreateResponse, summary="创建门店")
async def create_store(
    request: CreateStoreRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    创建新门店
    
    权限：仅管理员
    """
    # 检查门店名称是否已存在
    existing_store = db.query(DimStore).filter(
        DimStore.store_name == request.store_name.strip()
    ).first()
    
    if existing_store:
        raise HTTPException(
            status_code=400,
            detail=f"门店名称 '{request.store_name}' 已存在"
        )
    
    # 生成门店编码
    store_code = f"STORE-{uuid.uuid4().hex[:8].upper()}"
    
    # 创建门店
    new_store = DimStore(
        store_name=request.store_name.strip(),
        original_name=request.store_name.strip(),
        store_code=store_code,
        region=request.region,
        address=request.address,
        is_active=True,
    )
    
    try:
        db.add(new_store)
        db.commit()
        db.refresh(new_store)
        
        return StoreCreateResponse(
            success=True,
            message=f"门店 '{new_store.store_name}' 创建成功",
            data=StoreInfo(
                id=new_store.id,
                name=new_store.store_name,
                is_active=new_store.is_active if new_store.is_active is not None else True,
            ),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建门店失败: {str(e)}")


@router.delete("/{store_id}", summary="删除门店")
async def delete_store(
    store_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    删除门店（物理删除，从数据库表中删除）
    
    权限：仅管理员
    
    注意：删除门店会同时删除该门店的所有相关数据，此操作不可恢复
    """
    # 检查门店是否存在
    store = db.query(DimStore).filter(DimStore.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    
    # 检查是否有店长账号关联此门店
    from app.models.user import User
    managers = db.query(User).filter(
        User.store_id == store_id,
        User.role == "manager"
    ).count()
    
    if managers > 0:
        raise HTTPException(
            status_code=400,
            detail=f"门店 '{store.store_name}' 下还有 {managers} 个店长账号，请先删除或转移这些账号"
        )
    
    try:
        # 物理删除门店
        db.delete(store)
        db.commit()
        
        return {
            "success": True,
            "message": f"门店 '{store.store_name}' 已删除",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除门店失败: {str(e)}")

