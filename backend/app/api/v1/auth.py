"""
认证接口
"""
from fastapi import APIRouter, HTTPException, Response, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import (
    authenticate_user_db,
    create_access_token,
    get_current_user,
    get_current_admin,
)
from app.core.database import get_db

router = APIRouter(prefix="", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    role: str
    store_id: int | None = None


@router.post("/login", response_model=None)
async def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """用户登录"""
    import traceback
    from app.services.user_service import UserService
    from app.core.security import verify_password, create_access_token
    from datetime import datetime
    
    try:
        user_service = UserService(db)
        
        # 查询用户（只查询一次）
        user = user_service.get_user_by_username(request.username)
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        
        # 检查账号是否激活
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已停用，请联系管理员")
        
        # 验证密码（复用已查询的user对象）
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 更新最后登录时间
        try:
            user.last_login_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"❌ 更新最后登录时间失败: {e}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="更新登录信息失败，请稍后重试")

        # 创建 Token
        try:
            token = create_access_token(data={"sub": user.username})
        except Exception as e:
            print(f"❌ 创建Token失败: {e}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="生成访问令牌失败，请稍后重试")

        # 更新用户的token信息到数据库
        try:
            success = user_service.update_user_token(user.id, token)
            if not success:
                print(f"⚠️ 更新用户token失败: user_id={user.id}")
                # 即使更新token失败，也允许登录（token已创建）
        except Exception as e:
            print(f"❌ 更新用户token异常: {e}")
            print(traceback.format_exc())
            # 即使更新token失败，也允许登录（token已创建）
        
        # 获取用户信息用于返回
        try:
            user_info = user.to_user_info()
        except Exception as e:
            print(f"❌ 获取用户信息失败: {e}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail="获取用户信息失败，请稍后重试")

        # 设置 Cookie
        try:
            response.set_cookie(
                key="access_token",
                value=token,
                httponly=True,
                max_age=24 * 60 * 60,  # 24 小时
                samesite="lax",
            )
        except Exception as e:
            print(f"⚠️ 设置Cookie失败: {e}")
            # Cookie设置失败不影响登录，token已在响应体中返回

        return {
            "success": True,
            "message": "登录成功",
            "token": token,
            "user": user_info,
        }
    except HTTPException:
        # 重新抛出HTTP异常（如401、403等）
        raise
    except Exception as e:
        # 捕获所有其他异常
        print(f"❌ 登录过程发生未知错误: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


async def clear_user_token(request, db):
    """清除用户的token"""
    try:
        user_info = await get_current_user_from_request(request, db)
        if user_info:
            from app.services.user_service import UserService
            user_service = UserService(db)
            user = user_service.get_user_by_username(user_info["username"])
            if user:
                user_service.invalidate_user_token(user.id)
    except Exception:
        # 如果获取用户信息失败，忽略错误（可能是token已过期）
        pass


@router.post("/logout", response_model=None)
async def logout(response: Response):
    """用户登出"""
    # 注意：这里不能直接访问request，所以token清除需要在前端处理
    # 前端应该在调用logout API后清除本地存储的token

    # 清除cookie
    response.delete_cookie("access_token")
    return {"success": True, "message": "已登出"}


async def get_current_user_from_request(request, db):
    """从请求中获取当前用户（使用数据库验证token）"""
    # 优先从 Cookie 获取
    token = request.cookies.get("access_token")

    # 如果 Cookie 没有，尝试从 Header 获取
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=401,
            detail="未登录"
        )

    # 首先通过JWT解码验证token格式
    from app.core.security import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token 无效或已过期"
        )

    username = payload.get("sub")
    from app.services.user_service import UserService
    user_service = UserService(db)

    # 通过数据库验证token的有效性（包括过期时间和是否被强制登出）
    user = user_service.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Token 已过期或已被强制登出"
        )

    return user.to_user_info()


@router.get("/me", response_model=UserInfo)
async def get_me(request: Request, db: Session = Depends(get_db)):
    """获取当前用户信息"""
    user = await get_current_user_from_request(request, db)
    return UserInfo(
        username=user["username"],
        role=user["role"],
        store_id=user.get("store_id"),
    )


@router.post("/admin/force-logout/{user_id}", response_model=None)
async def force_logout_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    """管理员强制登出指定用户"""
    from app.services.user_service import UserService
    user_service = UserService(db)

    # 检查要强制登出的用户是否存在
    target_user = user_service.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不能强制登出管理员自己
    if target_user.id == current_user["id"]:
        raise HTTPException(status_code=400, detail="不能强制登出自己")

    # 清除用户的token
    success = user_service.invalidate_user_token(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="操作失败")

    return {
        "success": True,
        "message": f"已强制登出用户 {target_user.username}"
    }


@router.post("/admin/cleanup-expired-tokens", response_model=None)
async def cleanup_expired_tokens(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    """管理员清理过期的tokens"""
    from app.services.user_service import UserService
    user_service = UserService(db)

    cleaned_count = user_service.invalidate_all_expired_tokens()

    return {
        "success": True,
        "message": f"已清理 {cleaned_count} 个过期token"
    }

