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

## 🛠️ 交付部署（给运维/同事照做版）

### 前置要求

- [Docker](https://www.docker.com/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.0+)

### 0. 获取代码

```bash
git clone <YOUR_REPO_URL>
cd ktv-system-report
```

### 1. 配置环境变量（必须）

项目通过 `.env` 控制端口、数据库账号等配置：

```bash
cp env.example .env
```

按需修改 `.env`（推荐至少修改 `JWT_SECRET_KEY`、以及端口避免冲突）。

### 2. 启动服务（Docker Compose）

在项目根目录下执行：

```bash
# 首次启动 / 更新后启动（建议带 --build）
docker compose up -d --build

# 查看日志
docker compose logs -f
```

首次启动时：
- MySQL 会自动执行 `docker/mysql/init/01-init.sql`（创建数据库/基础结构）。
- **应用表结构以 Alembic 迁移为准**（见下一步）。

### 3. 初始化/升级数据库结构（Alembic）

```bash
docker compose exec backend alembic upgrade head
```

> 说明：`docker-compose.yml` 已挂载 `backend/alembic/` 与 `backend/alembic.ini` 到后端容器，方便在容器内直接执行迁移命令。

### 4. 访问系统

服务启动后，通过浏览器访问：

- **Web 界面**: [http://localhost:5173](http://localhost:5173)
- **API 文档 (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API 文档 (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

健康检查：
- `GET http://localhost:8000/health`
- `GET http://localhost:8000/health/detail`

### 5. 数据持久化与备份

数据持久化位置：
- **MySQL 数据**：Docker Volume `ktv-mysql-data`（见 `docker-compose.yml` 的 `volumes:mysql_data`）
- **上传文件**：`./data/uploads/`（挂载到后端容器 `/app/data/uploads`）

如需备份数据库（示例）：

```bash
# 导出 SQL（根据实际 root 密码修改）
docker compose exec mysql mysqldump -uroot -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}" > backup.sql
```

### 6. 日常运维命令

```bash
# 停止并移除容器（不删除 MySQL Volume）
docker compose down

# 重启
docker compose restart

# 更新版本（拉代码 + 重建 + 迁移）
git pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

### 7. 常见问题（Troubleshooting）

- **前端报错 “Failed to resolve import nprogress/nprogress.css”**：
  - 通常是容器未重建导致依赖未安装，执行：`docker compose up -d --build frontend`
- **端口冲突**：
  - 修改 `.env` 中的 `MYSQL_PORT` / `BACKEND_PORT` / `FRONTEND_PORT` 后重新 `docker compose up -d`

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
