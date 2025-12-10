"""
应用配置
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "ktv_user"
    DB_PASSWORD: str = "ktv123456"
    DB_NAME: str = "ktv_report"
    
    # JWT 配置
    JWT_SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # 文件上传配置
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    @property
    def DATABASE_URL(self) -> str:
        """数据库连接 URL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()

