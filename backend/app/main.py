"""
KTV 多店经营分析系统 - 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 创建应用实例
app = FastAPI(
    title="KTV 经营分析系统 API",
    description="KTV 多店经营分析系统后端服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS - 开发环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径 - 健康检查"""
    return {
        "message": "KTV 经营分析系统 API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


@app.get("/api/test")
async def test_api():
    """测试接口"""
    return {
        "success": True,
        "message": "后端服务正常运行！",
        "data": {
            "framework": "FastAPI",
            "database": "MySQL 8.0",
            "hot_reload": True
        }
    }


# TODO: 后续添加路由
# from app.api import upload, dashboard, chart, stores
# app.include_router(upload.router, prefix="/api/upload", tags=["文件上传"])
# app.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
# app.include_router(chart.router, prefix="/api/chart", tags=["图表数据"])
# app.include_router(stores.router, prefix="/api/stores", tags=["门店管理"])

