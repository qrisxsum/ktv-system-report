"""
API v1 路由聚合
"""

from fastapi import APIRouter

from .upload import router as upload_router
from .stats import router as stats_router
from .batches import router as batches_router
from .stores import router as stores_router
from .dashboard import router as dashboard_router
from .auth import router as auth_router
from .users import router as users_router

router = APIRouter(prefix="/api")

# 注册子路由
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(upload_router, prefix="/upload", tags=["文件上传"])
router.include_router(stats_router, prefix="/stats", tags=["数据统计"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["仪表盘"])
router.include_router(batches_router, prefix="/batches", tags=["批次管理"])
router.include_router(stores_router, prefix="/stores", tags=["门店管理"])
router.include_router(users_router, prefix="/users", tags=["用户管理"])

