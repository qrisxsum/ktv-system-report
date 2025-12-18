"""
用户服务

提供用户相关的数据库操作服务
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.user import User
from app.core.security import get_password_hash


class UserService:
    """用户服务类"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据用户ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()

    def authenticate_user(self, username: str, password: str, token: Optional[str] = None) -> Optional[User]:
        """验证用户身份"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not user.is_active:
            return None

        from app.core.security import verify_password
        if not verify_password(password, user.hashed_password):
            return None

        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()

        # 如果提供了token，更新用户的token信息（用于单设备登录控制）
        if token:
            from app.core.security import ACCESS_TOKEN_EXPIRE_HOURS
            from datetime import timedelta
            user.current_token = token
            user.token_expires_at = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

        self.db.commit()

        return user

    def create_user(self, user_data: Dict[str, Any]) -> User:
        """创建新用户"""
        # 哈希密码
        if "password" in user_data:
            user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Optional[User]:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # 如果更新密码，需要哈希
        if "password" in user_data:
            user_data["hashed_password"] = get_password_hash(user_data.pop("password"))

        for key, value in user_data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()
        return True

    def get_users(self, skip: int = 0, limit: int = 100, role: Optional[str] = None,
                  store_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[User]:
        """获取用户列表"""
        query = self.db.query(User)

        if role:
            query = query.filter(User.role == role)
        if store_id is not None:
            query = query.filter(User.store_id == store_id)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    def get_users_count(self, role: Optional[str] = None, store_id: Optional[int] = None,
                       is_active: Optional[bool] = None) -> int:
        """获取用户总数"""
        query = self.db.query(User)

        if role:
            query = query.filter(User.role == role)
        if store_id is not None:
            query = query.filter(User.store_id == store_id)
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        return query.count()

    def get_managers_by_store(self, store_id: int) -> List[User]:
        """获取指定门店的店长用户"""
        return self.db.query(User).filter(
            and_(User.role == "manager", User.store_id == store_id, User.is_active == True)
        ).all()

    def get_admins(self) -> List[User]:
        """获取所有管理员用户"""
        return self.db.query(User).filter(
            and_(User.role == "admin", User.is_active == True)
        ).all()

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        from app.core.security import verify_password
        if not verify_password(old_password, user.hashed_password):
            return False

        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def reset_password(self, user_id: int, new_password: str) -> bool:
        """重置密码（管理员操作）"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def toggle_user_status(self, user_id: int) -> Optional[User]:
        """切换用户激活状态"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        user.is_active = not user.is_active
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_token(self, token: str) -> Optional[User]:
        """根据token获取用户"""
        return self.db.query(User).filter(
            User.current_token == token,
            User.token_expires_at > datetime.utcnow(),
            User.is_active == True
        ).first()

    def invalidate_user_token(self, user_id: int) -> bool:
        """使指定用户的token失效（强制登出）"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.current_token = None
        user.token_expires_at = None
        user.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def invalidate_all_expired_tokens(self) -> int:
        """清理所有过期的token"""
        result = self.db.query(User).filter(
            User.token_expires_at <= datetime.utcnow(),
            User.current_token.isnot(None)
        ).update({
            "current_token": None,
            "token_expires_at": None,
            "updated_at": datetime.utcnow()
        })
        self.db.commit()
        return result

    def update_user_token(self, user_id: int, token: str) -> bool:
        """更新用户的token"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        from app.core.security import ACCESS_TOKEN_EXPIRE_HOURS
        from datetime import timedelta

        user.current_token = token
        user.token_expires_at = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        user.updated_at = datetime.utcnow()
        self.db.commit()
        return True
