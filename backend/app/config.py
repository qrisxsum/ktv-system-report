"""
应用配置 - 兼容层

此文件保留用于向后兼容，实际配置已迁移到 app.core.config
"""
# 从新位置导入，保持向后兼容
from app.core.config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
