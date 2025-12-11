# KTV 多门店报表自动化系统

基于 FastAPI + Vue 3 的现代化报表分析系统，专为 KTV 多门店经营分析设计。支持 Excel 数据自动解析、清洗、入库，并提供多维度的可视化数据看板。

## 🚀 系统特性

- **全流程自动化 ETL**: 拖拽上传 Excel (预订/开台/销售)，自动识别多级表头、动态清洗数据。
- **多维度可视化**:
  - **综合驾驶舱**: 实时展示营收、毛利、赠送率等核心 KPI。
  - **趋势分析**: 近30天营收趋势折线图。
  - **排行榜**: 门店、员工、商品 TopN 排名。
- **批次管理**: 支持查看上传历史，一键回滚（软删除）错误批次数据。
- **现代化架构**:
  - **后端**: Python 3.11 + FastAPI + SQLAlchemy 2.0 (Async) + Pandas
  - **前端**: Vue 3 + Vite + Element Plus + ECharts 5
  - **部署**: Docker Compose 一键编排，开箱即用。

---

## 🛠️ 快速开始 (部署流程)

### 前置要求

- [Docker](https://www.docker.com/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.0+)

### 1. 启动服务

在项目根目录下执行：

```bash
# 启动所有服务 (后台运行)
docker-compose up -d

# 查看日志
docker-compose logs -f
```

首次启动时，MySQL 容器会自动执行 `docker/mysql/init/01-init.sql` 初始化数据库结构。

### 2. 访问系统

服务启动后，通过浏览器访问：

- **Web 界面**: [http://localhost:5173](http://localhost:5173)
- **API 文档 (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API 文档 (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. 数据持久化

所有数据均持久化存储在 `data/` 目录下：
- `data/mysql/`: 数据库文件
- `data/uploads/`: 上传的原始 Excel 文件

---

## 💻 开发指南

### 目录结构

```text
ktv-system-report/
├── backend/                # 后端 (FastAPI)
│   ├── app/
│   │   ├── api/            # API 路由 (v1)
│   │   ├── core/           # 核心配置 (Config, DB)
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── schemas/        # Pydantic 数据契约
│   │   └── services/       # 业务逻辑 (ETL, Stats)
│   ├── alembic/            # 数据库迁移
│   └── requirements.txt    # Python 依赖
├── frontend/               # 前端 (Vue 3)
│   ├── src/
│   │   ├── api/            # Axios 请求封装
│   │   ├── components/     # 通用组件 (Charts)
│   │   ├── views/          # 页面视图 (Dashboard, Upload)
│   │   └── utils/          # 工具函数
│   └── package.json        # 前端依赖
├── docker/                 # Docker 配置
└── docker-compose.yml      # 容器编排
```

### 本地开发 (非 Docker)

如果你需要脱离 Docker 进行本地调试：

**后端**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端**:
```bash
cd frontend
npm install
npm run dev
```

**注意**: 本地开发时，需确保本地有可用的 MySQL 数据库，并在 `.env` 文件中配置 `DB_HOST` 等环境变量。

---

## 📅 开发阶段与进度

### Phase 1: 基础设施 (✅ 已完成)
- [x] 后端 API 路由层与 Pydantic Schemas 定义
- [x] 前端 Axios 封装与请求拦截器
- [x] Docker Compose 环境配置

### Phase 2: 核心业务 (✅ 已完成)
- [x] **上传模块**: 文件解析、预览、确认入库 UI
- [x] **批次管理**: 列表筛选、详情查看、回滚操作
- [x] **仪表盘**: 动态 ECharts 组件封装、KPI 计算逻辑接口

### Phase 3: 优化与完善 (✅ 已完成)
- [x] 全局加载进度条 (NProgress)
- [x] 404 错误页
- [x] 前端文件下载工具封装

### Next Steps (待接入)
- [ ] **Dev A**: 实现 `ImporterService` (真实入库) 和 `StatsService` (真实聚合查询)。
- [ ] **Dev B**: 实现 `ParserService` (Excel 解析) 和 `CleanerService` (数据清洗)。

---

## 📝 贡献指南

1.  **Branch**: 所有新功能在 `feature/xxx` 分支开发。
2.  **Commit**: 遵循 Conventional Commits 规范 (e.g. `feat: add chart component`).
3.  **Merge**: 开发完成后发起 Pull Request 合并至 `main`。

## 📄 License

MIT
