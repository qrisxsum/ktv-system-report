"""
用户管理相关 Schema 定义

用于管理员管理店长账号的 API 数据契约
"""

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime

from .common import ResponseBase, PaginationMeta


# ============================================================
# 请求 Schema
# ============================================================

class CreateManagerRequest(BaseModel):
    """创建店长账号请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名（3-50字符）")
    password: str = Field(..., min_length=8, max_length=100, description="密码（至少8位）")
    store_id: Optional[int] = Field(None, description="门店ID（与store_name二选一）")
    store_name: Optional[str] = Field(None, max_length=100, description="门店名称（如果门店不存在，将自动创建）")
    full_name: Optional[str] = Field(None, max_length=100, description="真实姓名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    
    @validator('password')
    def validate_password(cls, v):
        """密码强度验证"""
        if len(v) < 8:
            raise ValueError('密码至少需要8位')
        # 可选：检查是否包含字母和数字
        # if not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
        #     raise ValueError('密码必须包含字母和数字')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """手机号格式验证"""
        if v and not v.isdigit():
            raise ValueError('手机号只能包含数字')
        return v


class UpdateManagerRequest(BaseModel):
    """更新店长账号请求"""
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="新密码（不传则不修改）")
    store_id: Optional[int] = Field(None, description="门店ID")
    full_name: Optional[str] = Field(None, max_length=100, description="真实姓名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    
    @validator('password')
    def validate_password(cls, v):
        """密码强度验证"""
        if v and len(v) < 8:
            raise ValueError('密码至少需要8位')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """手机号格式验证"""
        if v and not v.isdigit():
            raise ValueError('手机号只能包含数字')
        return v


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码（至少8位）")
    
    @validator('new_password')
    def validate_password(cls, v):
        """密码强度验证"""
        if len(v) < 8:
            raise ValueError('密码至少需要8位')
        return v


# ============================================================
# 响应 Schema
# ============================================================

class ManagerInfo(BaseModel):
    """店长信息"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="角色（固定为manager）")
    store_id: int = Field(..., description="关联门店ID")
    store_name: Optional[str] = Field(None, description="门店名称")
    full_name: Optional[str] = Field(None, description="真实姓名")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    is_active: bool = Field(..., description="是否激活")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class ManagerListResponse(ResponseBase):
    """店长列表响应"""
    data: List[ManagerInfo] = Field(default_factory=list, description="店长列表")
    meta: PaginationMeta = Field(..., description="分页信息")


class ManagerDetailResponse(ResponseBase):
    """店长详情响应"""
    data: ManagerInfo = Field(..., description="店长信息")


class ManagerCreateResponse(ResponseBase):
    """创建店长响应"""
    data: ManagerInfo = Field(..., description="创建的店长信息")


class ManagerUpdateResponse(ResponseBase):
    """更新店长响应"""
    data: ManagerInfo = Field(..., description="更新后的店长信息")


class ManagerDeleteResponse(ResponseBase):
    """删除店长响应"""
    pass


class ManagerToggleStatusResponse(ResponseBase):
    """切换状态响应"""
    data: ManagerInfo = Field(..., description="更新后的店长信息")


class ResetPasswordResponse(ResponseBase):
    """重置密码响应"""
    pass

