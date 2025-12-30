"""
KTV 多店经营分析系统 - 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 导入核心模块
from app.core import get_settings, get_db_info, check_db_connection
from app.api import v1_router
from app.services.cleanup import start_scheduler, stop_scheduler

settings = get_settings()


# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    
    # 检查数据库连接
    if check_db_connection():
        print(f"✅ 数据库连接成功: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    else:
        print(f"⚠️ 数据库连接失败: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    # 启动定时清理任务
    start_scheduler()
    
    yield
    
    # 关闭时
    stop_scheduler()
    print(f"👋 {settings.APP_NAME} 正在关闭...")


# ==================== 创建应用实例 ====================
app = FastAPI(
    title=settings.APP_NAME,
    description="KTV 多店经营分析系统后端服务 - 上传 Excel → 清洗入库 → 老板看图",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ==================== 配置 CORS ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(v1_router)


# ==================== 基础接口 ====================
@app.get("/", tags=["系统"])
async def root():
    """根路径 - 系统信息"""
    return {
        "message": settings.APP_NAME,
        "status": "running",
        "version": settings.APP_VERSION
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    db_connected = check_db_connection()
    return {
        "status": "healthy" if db_connected else "degraded",
        "database": "connected" if db_connected else "disconnected"
    }


@app.get("/health/detail", tags=["系统"])
async def health_detail():
    """详细健康检查"""
    db_info = get_db_info()
    return {
        "status": "healthy" if db_info["connected"] else "unhealthy",
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "debug": settings.DEBUG
        },
        "database": db_info
    }


@app.get("/api/test", tags=["测试"])
async def test_api():
    """测试接口"""
    return {
        "success": True,
        "message": "后端服务正常运行！",
        "data": {
            "framework": "FastAPI",
            "database": "MySQL 8.0",
            "hot_reload": True,
            "db_host": settings.DB_HOST,
            "db_name": settings.DB_NAME
        }
    }


# ==================== 数据库模型测试接口 ====================
@app.get("/api/models/info", tags=["测试"])
async def get_models_info():
    """获取数据库模型信息（测试模型是否正确导入）"""
    from app.models import (
        MetaFileBatch, DimStore, DimEmployee, DimRoom, DimProduct,
        DimPaymentMethod, FactBooking, FactRoom, FactSales
    )
    
    models_info = {
        "meta_tables": [
            {"name": "MetaFileBatch", "table": MetaFileBatch.__tablename__}
        ],
        "dim_tables": [
            {"name": "DimStore", "table": DimStore.__tablename__},
            {"name": "DimEmployee", "table": DimEmployee.__tablename__},
            {"name": "DimRoom", "table": DimRoom.__tablename__},
            {"name": "DimProduct", "table": DimProduct.__tablename__},
            {"name": "DimPaymentMethod", "table": DimPaymentMethod.__tablename__},
        ],
        "fact_tables": [
            {"name": "FactBooking", "table": FactBooking.__tablename__},
            {"name": "FactRoom", "table": FactRoom.__tablename__},
            {"name": "FactSales", "table": FactSales.__tablename__},
        ]
    }
    return {
        "success": True,
        "message": "模型导入成功",
        "data": models_info
    }
