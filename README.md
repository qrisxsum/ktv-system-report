# KTV 多门店报表自动化系统

基于 FastAPI + Vue 3 的报表分析系统，支持 Excel 数据自动解析、清洗、入库，并提供多维度可视化数据看板。

## ✨ 功能特性

- 🔐 **用户认证**: 支持管理员和店长角色登录
- 📊 **综合驾驶舱**: 实时查看营业数据、趋势分析和关键指标
- 📤 **数据上传**: 支持Excel文件上传和批量数据处理
- 📋 **批次管理**: 管理数据导入批次，查看处理状态和错误日志
- 🔍 **专项分析**: 人员风云榜、商品销售分析、包厢效能分析
- 🏪 **门店管理**: 支持多门店数据隔离和权限控制

## 🚀 快速启动

### 前置要求

- [Docker](https://www.docker.com/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.0+)

### 启动服务

```bash
# 1. 克隆代码
git clone <YOUR_REPO_URL>
cd ktv-system-report

# 2. 配置环境变量
cp env.example .env

# 3. 启动
docker compose up -d --build

# 4. 初始化数据库
docker compose exec backend alembic upgrade head

# 5. 访问
# 前端: http://localhost:5173
# API: http://localhost:8000/docs
```

### 日常命令

```bash
docker compose up -d        # 启动
docker compose down         # 停止
docker compose logs -f      # 查看日志
docker compose restart      # 重启
```

---

## 👤 用户账号

系统提供以下测试账号：

### 管理员账号
- **用户名**: `admin`
- **密码**: `admin123`
- **权限**: 可访问所有门店数据，管理所有功能

### 店长账号
- **用户名**: `manager`
- **密码**: `manager123`
- **权限**: 仅可访问门店ID为1的数据

---

## ⚠️ 页面空白？

容器重建后首次访问如果出现白屏，**浏览器硬刷新一次**即可：
- **Chrome/Edge**: `Ctrl+Shift+R` (Mac: `Cmd+Shift+R`)
- **Safari**: `Cmd+Option+R`

---

## 📁 目录结构

```
ktv-system-report/
├── backend/                # FastAPI 后端
│   ├── app/                # 业务代码（热重载）
│   └── alembic/            # 数据库迁移
├── frontend/               # Vue 3 前端
│   └── src/                # 业务代码（热重载）
├── docker/                 # Docker 配置
└── docker-compose.yml      # 容器编排
```

---

## 🔧 常见问题

**后端无响应**: `docker compose logs backend` 查看错误

**端口冲突**: 修改 `.env` 中的端口配置后 `docker compose up -d`

**完全重置**: `docker compose down -v` (⚠️ 会删除数据库)

---

## 📄 License

MIT
