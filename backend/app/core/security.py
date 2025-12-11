"""
安全与鉴权模块
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# 密码哈希配置（使用 pbkdf2_sha256 以避免 bcrypt 后端依赖问题）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Token 配置
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = settings.SESSION_EXPIRE_HOURS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# 简单的用户存储（实际项目应使用数据库）
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("admin123"),
        "role": "admin",
        "store_id": None,  # admin 可以访问所有门店
    },
    "manager": {
        "username": "manager",
        "hashed_password": get_password_hash("manager123"),
        "role": "manager",
        "store_id": 1,  # 只能访问门店 1
    }
}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """验证用户"""
    user = USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


# 依赖注入：获取当前用户
security = HTTPBearer(auto_error=False)


async def get_current_user(request: Request) -> dict:
    """获取当前登录用户"""
    # 优先从 Cookie 获取
    token = request.cookies.get("access_token")

    # 如果 Cookie 没有，尝试从 Header 获取
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录"
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期"
        )

    username = payload.get("sub")
    user = USERS_DB.get(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    return user


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    """要求管理员权限"""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return user

