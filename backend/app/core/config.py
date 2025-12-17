"""
应用配置管理

从环境变量读取配置，支持 .env 文件
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """应用配置类 - 从环境变量读取"""
    
    # ==================== 数据库配置 ====================
    DB_HOST: str = "localhost"  # Docker 服务名，本地直连可改为 localhost
    DB_PORT: int = 3306
    DB_USER: str = "ktv_user"
    DB_PASSWORD: str = "ktv123456"
    DB_NAME: str = "ktv_report"
    
    # 连接池配置
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600  # 连接回收时间（秒）
    
    # ==================== 安全配置 ====================
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    SESSION_EXPIRE_HOURS: int = 24
    
    # JWT 配置（兼容旧配置）
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # ==================== 文件上传配置 ====================
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: set = {".csv", ".xls", ".xlsx"}
    
    # ==================== 应用配置 ====================
    APP_NAME: str = "KTV 经营分析系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    @property
    def DATABASE_URL(self) -> str:
        """同步数据库连接 URL (pymysql)"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """异步数据库连接 URL (aiomysql) - 如需要"""
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )
    
    @property
    def effective_secret_key(self) -> str:
        """获取有效的密钥（兼容旧配置）"""
        return self.JWT_SECRET_KEY or self.SECRET_KEY
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # 允许额外字段
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    
    使用 lru_cache 确保配置只加载一次
    """
    return Settings()
