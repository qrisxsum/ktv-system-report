# KTV 多店经营分析系统 (BI Lite)

一套轻量级 BI 系统，用于 KTV 连锁门店的经营数据分析。

**核心功能**：上传 Excel → 清洗入库 → 老板看图

## 🚀 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+

### 一键启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd ktv-system-report

# 2. 复制环境配置
cp env.example .env

# 3. 启动所有服务
docker compose up -d

# 4. 查看日志
docker compose logs -f
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:5173 | 数据上传、驾驶舱 |
| 后端 API | http://localhost:8000 | FastAPI 服务 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| 数据库 | localhost:3306 | MySQL 8.0 |

## 📁 项目结构

```
ktv-system-report/
├── docker-compose.yml      # Docker 编排配置
├── .env.example            # 环境变量示例
│
├── backend/                # 后端服务 (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py         # 应用入口
│       ├── config.py       # 配置管理
│       ├── api/            # API 路由
│       ├── models/         # 数据模型
│       ├── services/       # 业务逻辑
│       └── core/           # 核心模块 (ETL)
│
├── frontend/               # 前端应用 (Vue 3)
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── views/          # 页面组件
│       ├── layouts/        # 布局组件
│       └── router/         # 路由配置
│
├── docker/                 # Docker 配置
│   └── mysql/
│       ├── init/           # 数据库初始化脚本
│       └── conf.d/         # MySQL 配置
│
├── data/                   # 数据目录
│   ├── uploads/            # 上传文件
│   └── raw/                # 原始数据
│
└── docs/                   # 项目文档
    ├── 项目实施方案.md
    └── *.csv               # 样例数据
```

## 🛠️ 开发指南

### 热重载开发

项目已配置热重载，修改代码后自动刷新：

- **后端**：修改 `backend/app/` 下的文件，uvicorn 自动重载
- **前端**：修改 `frontend/src/` 下的文件，Vite HMR 自动更新

### 常用命令

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose down

# 查看日志
docker compose logs -f backend    # 后端日志
docker compose logs -f frontend   # 前端日志
docker compose logs -f mysql      # 数据库日志

# 重启单个服务
docker compose restart backend

# 重建镜像（依赖更新后）
docker compose build --no-cache backend
docker compose build --no-cache frontend

# 进入容器
docker compose exec backend bash
docker compose exec mysql mysql -uroot -p

# 清理数据（谨慎使用）
docker compose down -v  # 删除数据卷
```

### 数据库操作

```bash
# 连接数据库
docker compose exec mysql mysql -uktv_user -pktv123456 ktv_report

# 导出数据
docker compose exec mysql mysqldump -uroot -proot123456 ktv_report > backup.sql

# 导入数据
docker compose exec -T mysql mysql -uroot -proot123456 ktv_report < backup.sql
```

## 🔧 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.109 |
| 数据处理 | Pandas | 2.1 |
| 数据库 | MySQL | 8.0 |
| ORM | SQLAlchemy | 2.0 |
| 前端框架 | Vue | 3.4 |
| UI 组件 | Element Plus | 2.5 |
| 图表库 | ECharts | 5.4 |
| 容器化 | Docker | 20.10+ |

## 📊 功能模块

### 1. 数据上传中心
- 拖拽上传 CSV/Excel 文件
- 智能识别文件类型（包厢/酒水/预订）
- 解析预览，确认后入库

### 2. 综合驾驶舱
- KPI 卡片：营收、增长率、毛利率、开台数
- 业绩趋势图（折线图）
- 收入构成（饼图）
- 员工/商品 TOP5 排行

### 3. 专项分析
- 人员风云榜：员工业绩排名
- 商品销售：销量、利润分析
- 包厢效能：开台次数、平均消费

## 📝 License

MIT

