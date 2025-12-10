"""
Alembic 环境配置

用于数据库迁移的环境设置
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置和模型
from app.core.config import get_settings
from app.core.database import Base

# 导入所有模型，确保它们被注册到 Base.metadata
from app.models import (
    MetaFileBatch,
    DimStore, DimEmployee, DimRoom, DimProduct, DimPaymentMethod,
    FactBooking, FactRoom, FactSales
)

# Alembic Config 对象
config = context.config

# 获取应用配置
settings = get_settings()

# 设置数据库 URL（覆盖 alembic.ini 中的配置）
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 设置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置 target_metadata（用于自动生成迁移）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    在"离线"模式下运行迁移
    
    这将配置上下文以仅使用 URL，
    而不是 Engine，尽管此处也可以接受 Engine。
    通过跳过 Engine 创建，我们甚至不需要 DBAPI 可用。
    
    这里对 context.execute() 的调用会将给定的字符串发出到脚本输出。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 检测列类型变化
        compare_server_default=True,  # 检测默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在"在线"模式下运行迁移
    
    在这种情况下，我们需要创建一个 Engine
    并将连接与上下文关联。
    """
    from sqlalchemy import create_engine
    
    # 直接使用配置中的 URL 创建引擎
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 检测列类型变化
            compare_server_default=True,  # 检测默认值变化
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

