"""
数据库连接管理

提供 SQLAlchemy 引擎、会话工厂和依赖注入
"""
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings

settings = get_settings()

# ==================== 创建数据库引擎 ====================
engine = create_engine(
    settings.DATABASE_URL,
    # 连接池配置
    poolclass=QueuePool,
    pool_pre_ping=True,           # 连接前检测（防止连接失效）
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    # 调试选项
    echo=settings.DEBUG,          # DEBUG 模式下打印 SQL
    echo_pool=False,              # 不打印连接池信息
)

# ==================== 连接事件处理 ====================
@event.listens_for(engine, "connect")
def set_mysql_charset(dbapi_connection, connection_record):
    """设置 MySQL 连接字符集"""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET NAMES utf8mb4")
    cursor.execute("SET CHARACTER SET utf8mb4")
    cursor.close()


# ==================== 创建会话工厂 ====================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ==================== 声明基类 ====================
Base = declarative_base()


# ==================== 依赖注入 ====================
def get_db() -> Generator[Session, None, None]:
    """
    依赖注入：获取数据库会话
    
    用法:
        @app.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== 工具函数 ====================
def init_db() -> None:
    """
    初始化数据库（创建所有表）
    
    注意：生产环境应该使用 Alembic 迁移
    """
    # 导入所有模型，确保它们被注册到 Base.metadata
    # from app.models import *  # noqa
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """
    检查数据库连接是否正常
    
    Returns:
        bool: 连接是否正常
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"数据库连接错误: {e}")
        return False


def get_db_info() -> dict:
    """
    获取数据库连接信息（用于健康检查）
    
    Returns:
        dict: 数据库连接信息
    """
    return {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "database": settings.DB_NAME,
        "pool_size": settings.DB_POOL_SIZE,
        "connected": check_db_connection()
    }

