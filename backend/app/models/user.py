"""
用户模型

定义用户表的SQLAlchemy模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增主键")
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    hashed_password = Column(String(255), nullable=False, comment="密码哈希")
    role = Column(String(20), nullable=False, comment="角色: admin/manager")
    store_id = Column(Integer, nullable=True, comment="关联门店ID (管理员为NULL)")
    full_name = Column(String(100), nullable=True, comment="真实姓名")
    email = Column(String(100), nullable=True, comment="邮箱")
    phone = Column(String(20), nullable=True, comment="手机号")
    is_active = Column(Boolean, default=True, nullable=True, comment="是否激活")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    current_token = Column(String(500), nullable=True, comment="当前有效的token (用于单设备登录控制)")
    token_expires_at = Column(DateTime, nullable=True, comment="token过期时间")
    created_at = Column(DateTime, server_default=func.now(), nullable=True, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=True, comment="更新时间")

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "store_id": self.store_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_user_info(self):
        """转换为用户信息格式（用于认证返回）"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "store_id": self.store_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
        }
