"""
认证接口
"""
from fastapi import APIRouter, HTTPException, Response, Depends
from pydantic import BaseModel

from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/api", tags=["认证"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    role: str
    store_id: int | None = None


@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """用户登录"""
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 创建 Token
    token = create_access_token(data={"sub": user["username"]})

    # 设置 Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=24 * 60 * 60,  # 24 小时
        samesite="lax",
    )

    return {
        "success": True,
        "message": "登录成功",
        "user": {
            "username": user["username"],
            "role": user["role"],
            "store_id": user.get("store_id"),
        },
    }


@router.post("/logout")
async def logout(response: Response):
    """用户登出"""
    response.delete_cookie("access_token")
    return {"success": True, "message": "已登出"}


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserInfo(
        username=user["username"],
        role=user["role"],
        store_id=user.get("store_id"),
    )

