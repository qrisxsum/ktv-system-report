"""
核心模块

提供配置管理、数据库连接等基础功能
"""
from app.core.config import get_settings, Settings
from app.core.database import (
    get_db,
    SessionLocal,
    Base,
    engine,
    init_db,
    check_db_connection,
    get_db_info
)

__all__ = [
    # 配置
    "get_settings",
    "Settings",
    # 数据库
    "get_db",
    "SessionLocal",
    "Base",
    "engine",
    "init_db",
    "check_db_connection",
    "get_db_info",
]


