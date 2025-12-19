"""
用户管理接口

管理员管理店长账号的 API
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.models.dims import DimStore
from app.services.user_service import UserService
from app.schemas.user import (
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
    PaginationMeta,
)

router = APIRouter()


def _convert_user_to_manager_info(user: User, store_name: Optional[str] = None) -> ManagerInfo:
    """将 User 对象转换为 ManagerInfo"""
    return ManagerInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        store_id=user.store_id,
        store_name=store_name,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active if user.is_active is not None else True,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/managers", response_model=ManagerCreateResponse, summary="创建店长账号")
async def create_manager(
    request: CreateManagerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    创建店长账号
    
    权限：仅管理员
    
    支持两种方式：
    1. 通过 store_id 指定已有门店
    2. 通过 store_name 指定门店名称，如果门店不存在则自动创建
    """
    from app.services.importer import ImporterService
    
    user_service = UserService(db)
    importer_service = ImporterService(db)
    
    # 0. 验证门店参数：必须提供 store_id 或 store_name 之一，但不能同时提供
    if not request.store_id and not request.store_name:
        raise HTTPException(status_code=400, detail="必须提供门店ID或门店名称")
    if request.store_id and request.store_name:
        raise HTTPException(status_code=400, detail="门店ID和门店名称不能同时提供，请选择其一")
    
    # 1. 验证用户名唯一性
    existing_user = user_service.get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail=f"用户名 '{request.username}' 已存在")
    
    # 2. 处理门店：获取或创建门店
    store = None
    store_id = None
    
    if request.store_id:
        # 方式1：通过门店ID
        store = db.query(DimStore).filter(DimStore.id == request.store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail=f"门店ID {request.store_id} 不存在")
        if not store.is_active:
            raise HTTPException(status_code=400, detail=f"门店 '{store.store_name}' 未启用，无法关联")
        store_id = request.store_id
    elif request.store_name:
        # 方式2：通过门店名称，自动创建或获取（使用 ImporterService 统一方法）
        store_name = request.store_name.strip()
        if not store_name:
            raise HTTPException(status_code=400, detail="门店名称不能为空")
        
        try:
            # 使用 ImporterService 的方法，返回 store 对象以便检查状态
            store_id, store = importer_service._get_or_create_store(db, store_name, return_store=True)
            
            # 检查门店状态（如果门店已存在但未启用，则不允许关联）
            if not store.is_active:
                raise HTTPException(
                    status_code=400, 
                    detail=f"门店 '{store.store_name}' 未启用，无法关联"
                )
        except ValueError as e:
            # 参数验证错误
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # 其他错误（如数据库错误）
            raise HTTPException(status_code=500, detail=f"处理门店失败: {str(e)}")
    
    if not store_id:
        raise HTTPException(status_code=400, detail="必须提供门店ID或门店名称")
    
    # 3. 创建用户
    user_data = {
        "username": request.username,
        "password": request.password,  # UserService 会自动哈希
        "role": "manager",
        "store_id": store_id,
        "full_name": request.full_name,
        "email": request.email,
        "phone": request.phone,
        "is_active": True,
    }
    
    try:
        user = user_service.create_user(user_data)
        message = f"店长账号 '{user.username}' 创建成功"
        if request.store_name and not request.store_id:
            message += f"，已自动创建门店 '{store.store_name}'"
        return ManagerCreateResponse(
            success=True,
            message=message,
            data=_convert_user_to_manager_info(user, store.store_name),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建店长账号失败: {str(e)}")


@router.get("/managers", response_model=ManagerListResponse, summary="获取店长列表")
async def list_managers(
    store_id: Optional[int] = Query(None, description="按门店筛选"),
    is_active: Optional[bool] = Query(None, description="按激活状态筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索（用户名、姓名、手机号）"),
    skip: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    获取店长列表（分页）
    
    权限：仅管理员
    """
    user_service = UserService(db)
    
    # 构建查询条件
    query = db.query(User).filter(User.role == "manager")
    
    # 门店筛选
    if store_id is not None:
        query = query.filter(User.store_id == store_id)
    
    # 激活状态筛选
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # 关键词搜索
    if keyword:
        keyword_filter = or_(
            User.username.like(f"%{keyword}%"),
            User.full_name.like(f"%{keyword}%"),
            User.phone.like(f"%{keyword}%"),
        )
        query = query.filter(keyword_filter)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    # 获取门店名称映射
    store_ids = {user.store_id for user in users if user.store_id}
    stores = {}
    if store_ids:
        store_list = db.query(DimStore).filter(DimStore.id.in_(store_ids)).all()
        stores = {store.id: store.store_name for store in store_list}
    
    # 转换为响应格式
    manager_list = [
        _convert_user_to_manager_info(user, stores.get(user.store_id))
        for user in users
    ]
    
    # 计算总页数
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    current_page = (skip // limit) + 1 if limit > 0 else 1
    
    return ManagerListResponse(
        success=True,
        message="获取店长列表成功",
        data=manager_list,
        meta=PaginationMeta(
            total=total,
            page=current_page,
            page_size=limit,
            total_pages=total_pages,
        ),
    )


@router.get("/managers/{user_id}", response_model=ManagerDetailResponse, summary="获取店长详情")
async def get_manager(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    获取店长详情
    
    权限：仅管理员
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="店长账号不存在")
    
    if user.role != "manager":
        raise HTTPException(status_code=400, detail="该用户不是店长账号")
    
    # 获取门店名称
    store_name = None
    if user.store_id:
        store = db.query(DimStore).filter(DimStore.id == user.store_id).first()
        if store:
            store_name = store.store_name
    
    return ManagerDetailResponse(
        success=True,
        message="获取店长详情成功",
        data=_convert_user_to_manager_info(user, store_name),
    )


@router.put("/managers/{user_id}", response_model=ManagerUpdateResponse, summary="更新店长信息")
async def update_manager(
    user_id: int,
    request: UpdateManagerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    更新店长信息
    
    权限：仅管理员
    注意：用户名不可修改
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="店长账号不存在")
    
    if user.role != "manager":
        raise HTTPException(status_code=400, detail="该用户不是店长账号")
    
    # 构建更新数据（只包含提供的字段）
    update_data = {}
    if request.password is not None:
        update_data["password"] = request.password
    if request.store_id is not None:
        # 验证新门店存在且启用
        store = db.query(DimStore).filter(DimStore.id == request.store_id).first()
        if not store:
            raise HTTPException(status_code=404, detail=f"门店ID {request.store_id} 不存在")
        if not store.is_active:
            raise HTTPException(status_code=400, detail=f"门店 '{store.store_name}' 未启用，无法关联")
        update_data["store_id"] = request.store_id
    if request.full_name is not None:
        update_data["full_name"] = request.full_name
    if request.email is not None:
        update_data["email"] = request.email
    if request.phone is not None:
        update_data["phone"] = request.phone
    
    if not update_data:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")
    
    # 更新用户
    updated_user = user_service.update_user(user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=500, detail="更新店长信息失败")
    
    # 获取门店名称
    store_name = None
    if updated_user.store_id:
        store = db.query(DimStore).filter(DimStore.id == updated_user.store_id).first()
        if store:
            store_name = store.store_name
    
    return ManagerUpdateResponse(
        success=True,
        message=f"店长账号 '{updated_user.username}' 更新成功",
        data=_convert_user_to_manager_info(updated_user, store_name),
    )


@router.delete("/managers/{user_id}", response_model=ManagerDeleteResponse, summary="删除店长账号")
async def delete_manager(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    删除店长账号（物理删除，从数据库表中删除）
    
    权限：仅管理员
    注意：此操作会从数据库中永久删除账号，不可恢复
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="店长账号不存在")
    
    if user.role != "manager":
        raise HTTPException(status_code=400, detail="该用户不是店长账号")
    
    # 不能删除自己（虽然当前用户是管理员，但为了安全还是检查一下）
    if user.id == current_user.get("id"):
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    
    try:
        # 物理删除：从数据库表中删除
        success = user_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除店长账号失败")
        
        return ManagerDeleteResponse(
            success=True,
            message=f"店长账号 '{user.username}' 已删除",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除店长账号失败: {str(e)}")


@router.post("/managers/{user_id}/toggle-status", response_model=ManagerToggleStatusResponse, summary="切换店长账号状态")
async def toggle_manager_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    切换店长账号的激活状态（启用/停用）
    
    权限：仅管理员
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="店长账号不存在")
    
    if user.role != "manager":
        raise HTTPException(status_code=400, detail="该用户不是店长账号")
    
    # 不能停用自己
    if user.id == current_user.get("id"):
        raise HTTPException(status_code=400, detail="不能停用自己的账号")
    
    # 切换状态
    updated_user = user_service.toggle_user_status(user_id)
    if not updated_user:
        raise HTTPException(status_code=500, detail="切换状态失败")
    
    # 如果停用，强制登出
    if not updated_user.is_active:
        user_service.invalidate_user_token(user_id)
    
    # 获取门店名称
    store_name = None
    if updated_user.store_id:
        store = db.query(DimStore).filter(DimStore.id == updated_user.store_id).first()
        if store:
            store_name = store.store_name
    
    status_text = "启用" if updated_user.is_active else "停用"
    return ManagerToggleStatusResponse(
        success=True,
        message=f"店长账号 '{updated_user.username}' 已{status_text}",
        data=_convert_user_to_manager_info(updated_user, store_name),
    )


@router.post("/managers/{user_id}/reset-password", response_model=ResetPasswordResponse, summary="重置店长密码")
async def reset_manager_password(
    user_id: int,
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    """
    重置店长密码
    
    权限：仅管理员
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="店长账号不存在")
    
    if user.role != "manager":
        raise HTTPException(status_code=400, detail="该用户不是店长账号")
    
    # 重置密码
    success = user_service.reset_password(user_id, request.new_password)
    if not success:
        raise HTTPException(status_code=500, detail="重置密码失败")
    
    # 强制登出该用户（让用户使用新密码重新登录）
    user_service.invalidate_user_token(user_id)
    
    return ResetPasswordResponse(
        success=True,
        message=f"店长账号 '{user.username}' 的密码已重置，用户需要重新登录",
    )

