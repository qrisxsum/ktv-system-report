# Web 界面与接口设计文档 (Lite版)

## 文档说明

本文档基于《具体需求.md》和《简化.md》，设计**简化版**的 Web 界面与 API 接口。

**核心理念**：
1.  **前后端合并**：Vue 3 构建产物直接由 FastAPI 托管，去除 Nginx 依赖。
2.  **接口精简**：合并碎片化 API，提供通用的查询接口。
3.  **认证简化**：使用 Session/Cookie 替代 JWT，适合后台管理系统。

**版本号**: v2.2 (Lite - Final Aligned)  
**生成日期**: 2025-12-09  
**技术栈**: FastAPI + Vue 3 + Element Plus + ECharts

---

## 一、API 接口设计 (FastAPI)

### 1.1 认证模块 (Auth)

**简化点**：移除 Refresh Token，使用简单的 Cookie Session。

-   `POST /api/login`: 用户名密码登录，设置 HttpOnly Cookie。
-   `POST /api/logout`: 清除 Cookie。
-   `GET /api/me`: 获取当前用户信息（角色、门店权限）。

### 1.2 文件上传与管理 (Files)

**简化点**：同步返回上传结果（小文件），或简单的后台任务（大文件）。

-   `POST /api/upload`: 上传 Excel/CSV 文件。
    -   **Params**: `file`, `store_id` (可选), `date` (可选)
    -   **Response**:
        ```json
        {
          "batch_id": 123,
          "status": "success", // or "warning"
          "summary": {
            "row_count": 100,
            "sales_total": 50000.00,
            "actual_total": 48000.00,
            "balance_diff_count": 0 // 金额不平的行数
          }
        }
        ```
-   `GET /api/batches`: 获取上传批次历史。
    -   **Response**: list of `meta_file_batch` records.
-   `DELETE /api/batches/{id}`: 删除批次（回滚数据）。

### 1.3 数据查询与聚合 (Stats)

**简化点**：提供**单一入口**的通用聚合接口，替代繁琐的专用接口。

-   `GET /api/stats/query`
    -   **Query Params**:
        -   `table`: `booking` | `room` | `sales` (查询哪张事实表)
        -   `start_date`: `2025-01-01`
        -   `end_date`: `2025-01-31`
        -   `store_id`: 可选
        -   `dimension`: `date` | `store` | `employee` | `product` | `room` | `room_type` (聚合维度)
        -   `granularity`: `day` | `week` | `month` (时间粒度，仅当 dimension=date 时有效，默认 day)
    -   **Response**:
        ```json
        {
          "data": [
            {
              "dimension_key": "2025-01",  // 月度聚合示例
              "sales": 30000.00,
              "actual": 27000.00,
              "profit": 15000.00,      // 毛利
              "cost": 12000.00,        // 成本 (用于计算利润率)
              "gift_qty": 300,         // 赠送数量
              "gift_amount": 6000.00   // 赠送金额
            }
          ],
          "meta": {
            "total_sales": 30000.00,
            "total_profit": 15000.00
          }
        }
        ```

-   `GET /api/dashboard/summary`: 首页看板汇总数据（昨日营收、本月累计等）。

### 1.4 基础数据 (Meta)

-   `GET /api/stores`: 获取门店列表。
-   `GET /api/employees`: 获取员工列表（用于筛选）。
-   `GET /api/rooms`: 获取包厢列表（用于筛选）。

---

## 二、前端界面设计 (Vue 3)

### 2.1 整体布局 (Layout)
-   **侧边栏**: 仪表盘、数据上传、报表查询、批次管理、系统设置。
-   **顶部栏**: 面包屑、当前用户、退出登录。

### 2.2 核心页面

#### 2.2.1 仪表盘 (Dashboard)
-   **核心卡片**: 昨日实收、本月实收、开台率、毛利率、**赠送率**。
-   **趋势图**: 近 30 天营收折线图 (ECharts)。
-   **排行**: Top 5 门店/员工/商品。

#### 2.2.2 数据上传 (Upload)
-   **上传组件**: 支持拖拽，自动识别文件类型。
-   **实时反馈**: 上传进度条 -> 解析中 -> 成功/失败。
-   **结果展示**: 上传成功后，弹出对话框显示校验报告（如：导入 100 行，实收 5000 元，**0 行金额不平**）。

#### 2.2.3 报表查询 (Report)
-   **通用筛选栏**:
    -   **时间范围**: 日期选择器 (YYYY-MM-DD)。
    -   **时间粒度**: 下拉框 (按日 / 按周 / 按月)。
    -   **门店**: 下拉框 (支持多选或单选)。
    -   **统计维度**: 按钮组 (按时间 / 按门店 / 按员工 / **按包厢** / **按商品**)。
-   **动态表格**:
    -   根据选择的维度，动态展示列。
    -   **关键列**: 销售额、实收额、**成本**、**毛利**、**赠送金额**。
    -   支持前端排序、分页。
-   **导出按钮**: "导出 Excel"，直接调用后端流式下载接口。

#### 2.2.4 批次管理 (Batch)
-   **列表**: 展示所有上传记录（文件名、上传人、时间、状态）。
-   **操作**: "删除" 按钮，点击后二次确认，调用 API 回滚该批次数据。

---

## 三、权限控制 (RBAC Lite)

**角色**:
1.  **Admin (老板/超管)**: 查看所有门店，管理所有数据。
2.  **Manager (店长)**: 只能上传/查看**自己门店**的数据（后端 API 根据 session 中的 `store_id` 强制过滤）。

---

## 四、部署与工程结构

### 4.1 目录结构
```
/frontend
  /src
    /api        # Axios 封装
    /components # Upload, Chart, Table
    /views      # Dashboard, Report, Login
    /layout     # MainLayout
```

### 4.2 构建流程
1.  `cd frontend && npm run build` -> 生成 `dist/` 目录。
2.  后端 `FastAPI` 配置：
    ```python
    app.mount("/static", StaticFiles(directory="frontend/dist/assets"), name="static")
    
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        return FileResponse("frontend/dist/index.html")
    ```
3.  启动 `uvicorn`，访问 `http://localhost:8000` 即可看到完整应用。

---

## 五、总结

Lite 版界面设计砍掉了复杂的审批流、多级菜单和自定义报表，专注于**“传文件 -> 看报表”**这一核心链路。对于 KTV 业务场景，这样的设计交互路径最短，用户体验最好。
