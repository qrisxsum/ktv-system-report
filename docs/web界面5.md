# Web 界面与接口设计文档

## 文档说明

本文档基于《具体需求.md》《解析与清洗.md》《入库模型.md》《聚合.md》和《详细业务分析实现.md》的要求，详细设计 KTV 多门店报表自动化系统的 Web 界面与接口方案，包括后端 API 设计、前端界面设计、权限管理、审计日志等核心内容。

**版本号**: v1.0  
**生成日期**: 2025-12-03  
**技术栈**: FastAPI/Flask（后端）、React/Vue（前端）、ECharts（图表）

---

## 一、目标与范围

### 1.1 核心目标

1. **文件管理**：支持文件上传、历史记录查看、批次状态查询、重跑功能
2. **数据查询**：支持多维度筛选（门店/时间/员工/包厢/商品/渠道）、聚合查询、TopN 查询
3. **可视化展示**：指标看板（收入/实收/折扣/赠送/业绩/毛利）、数据表格、图表展示
4. **数据导出**：支持导出 CSV 格式的查询结果
5. **校验报告**：展示批次校验报告、异常明细、平衡校验结果
6. **权限管理**：基于角色的访问控制（老板/财务/门店经理），数据隔离

### 1.2 功能范围

根据《详细业务分析实现.md》的要求：

**后端功能**：
- 文件上传与存储
- 批次列表与状态查询
- 校验报告查询
- 聚合查询（日/周/月/自定义范围）
- 导出 CSV
- 健康检查与版本接口
- 权限验证与审计日志

**前端功能**：
- 文件上传界面
- 批次管理界面（列表、状态、重跑）
- 指标看板（收入、实收、折扣、赠送、业绩、毛利）
- 数据查询界面（筛选器、表格、图表）
- 校验报告查看界面
- 数据导出功能
- 登录与权限管理

### 1.3 技术约束

- **后端框架**：FastAPI（推荐）或 Flask
- **前端框架**：React 或 Vue（推荐 React）
- **图表库**：ECharts
- **数据库**：MySQL 5.7+（通过 SQLAlchemy ORM）
- **权限认证**：JWT Token 或 Session
- **文件存储**：本地文件系统或对象存储（OSS/S3）

---

## 二、后端 API 设计

### 2.1 API 设计原则

**RESTful 规范**：
- 使用标准 HTTP 方法（GET、POST、PUT、DELETE）
- 资源路径使用名词，避免动词
- 返回 JSON 格式数据
- 统一错误响应格式
- 支持分页、排序、过滤

**版本管理**：
- API 版本号：`/api/v1/`
- 支持多版本共存，便于平滑升级

**响应格式**：
- 成功响应：`{"code": 200, "message": "success", "data": {...}}`
- 错误响应：`{"code": 400, "message": "error message", "details": {...}}`

### 2.2 文件上传接口

#### 2.2.1 上传文件

**接口路径**：`POST /api/v1/files/upload`

**功能描述**：
- 接收上传的文件（CSV/xls/xlsx）
- 存储到指定目录（`/raw/{store}/{type}/`）
- 创建批次记录
- 触发解析任务（异步）

**请求参数**：
- `file`：文件（multipart/form-data）
- `store_name`：门店名称（可选，从文件名解析）
- `table_type`：表类型（可选，从文件名推断：booking_summary/beverage_sales/room_analysis）

**响应示例**：
```json
{
  "code": 200,
  "message": "文件上传成功",
  "data": {
    "batch_id": 123,
    "batch_no": "20251203_100000_空境·派对KTV（万象城店）_booking_summary",
    "file_name": "预订汇总2025-12-01 10_00_00至2025-12-03 10_00_00(空境·派对KTV（万象城店）).csv",
    "file_path": "/raw/空境·派对KTV（万象城店）/booking_summary/20251203_100000_预订汇总2025-12-01 10_00_00至2025-12-03 10_00_00(空境·派对KTV（万象城店）).csv",
    "file_size": 102400,
    "table_type": "booking_summary",
    "store_name": "空境·派对KTV（万象城店）",
    "status": "pending",
    "created_at": "2025-12-03T10:00:00Z"
  }
}
```

**错误响应**：
- `400`：文件格式不支持、文件大小超限、参数错误
- `401`：未授权（需要登录）
- `403`：权限不足（门店经理只能上传本门店文件）
- `500`：服务器错误

**实施细节**：
1. 文件大小限制：建议最大 100MB
2. 文件类型验证：检查文件扩展名和 MIME 类型
3. 文件存储：按门店和表类型组织目录结构
4. 异步处理：使用 Celery 或后台任务队列处理解析任务
5. 幂等性：检查文件校验和，避免重复上传

#### 2.2.2 批量上传

**接口路径**：`POST /api/v1/files/batch-upload`

**功能描述**：
- 支持一次上传多个文件
- 每个文件独立创建批次记录
- 返回所有批次信息

**请求参数**：
- `files`：文件列表（multipart/form-data，多个文件）

**响应示例**：
```json
{
  "code": 200,
  "message": "批量上传成功",
  "data": {
    "total": 3,
    "success": 3,
    "failed": 0,
    "batches": [
      {"batch_id": 123, "file_name": "file1.csv", "status": "pending"},
      {"batch_id": 124, "file_name": "file2.csv", "status": "pending"},
      {"batch_id": 125, "file_name": "file3.csv", "status": "pending"}
    ]
  }
}
```

### 2.3 批次管理接口

#### 2.3.1 批次列表查询

**接口路径**：`GET /api/v1/batches`

**功能描述**：
- 查询批次列表，支持分页、排序、过滤
- 支持按门店、表类型、状态、时间范围过滤

**查询参数**：
- `page`：页码（默认 1）
- `page_size`：每页数量（默认 20，最大 100）
- `store_id`：门店ID（可选）
- `table_type`：表类型（可选）
- `status`：状态（可选：pending/processing/success/failed/partial）
- `start_date`：开始日期（可选，格式：YYYY-MM-DD）
- `end_date`：结束日期（可选，格式：YYYY-MM-DD）
- `sort_by`：排序字段（可选：created_at/batch_no/status，默认 created_at）
- `sort_order`：排序方向（可选：asc/desc，默认 desc）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "batch_id": 123,
        "batch_no": "20251203_100000_空境·派对KTV（万象城店）_booking_summary",
        "file_name": "预订汇总2025-12-01 10_00_00至2025-12-03 10_00_00(空境·派对KTV（万象城店）).csv",
        "table_type": "booking_summary",
        "store_id": 1,
        "store_name": "空境·派对KTV（万象城店）",
        "date_range_start": "2025-12-01",
        "date_range_end": "2025-12-03",
        "import_status": "success",
        "total_rows": 100,
        "success_rows": 95,
        "failed_rows": 5,
        "created_at": "2025-12-03T10:00:00Z",
        "completed_at": "2025-12-03T10:05:00Z"
      }
    ]
  }
}
```

**权限控制**：
- 老板：可查看所有门店批次
- 财务：可查看所有门店批次
- 门店经理：只能查看本门店批次

#### 2.3.2 批次详情查询

**接口路径**：`GET /api/v1/batches/{batch_id}`

**功能描述**：
- 查询单个批次的详细信息
- 包含文件信息、导入状态、统计信息、错误信息

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "batch_id": 123,
    "batch_no": "20251203_100000_空境·派对KTV（万象城店）_booking_summary",
    "file_name": "预订汇总2025-12-01 10_00_00至2025-12-03 10_00_00(空境·派对KTV（万象城店）).csv",
    "file_path": "/raw/空境·派对KTV（万象城店）/booking_summary/20251203_100000_预订汇总2025-12-01 10_00_00至2025-12-03 10_00_00(空境·派对KTV（万象城店）).csv",
    "file_size": 102400,
    "file_checksum": "sha256:abc123...",
    "table_type": "booking_summary",
    "store_id": 1,
    "store_name": "空境·派对KTV（万象城店）",
    "date_range_start": "2025-12-01",
    "date_range_end": "2025-12-03",
    "import_status": "success",
    "total_rows": 100,
    "success_rows": 95,
    "failed_rows": 5,
    "error_message": null,
    "validation_report": {
      "balance_check": {
        "total_checked": 100,
        "passed": 95,
        "failed": 5,
        "total_diff_amount": 12.50
      },
      "anomaly_check": {
        "negative_amount": 2,
        "time_cross": 1,
        "missing_required": 2
      }
    },
    "created_at": "2025-12-03T10:00:00Z",
    "completed_at": "2025-12-03T10:05:00Z"
  }
}
```

#### 2.3.3 批次重跑

**接口路径**：`POST /api/v1/batches/{batch_id}/rerun`

**功能描述**：
- 重新执行批次导入流程
- 支持覆盖模式（删除旧数据后重新导入）或追加模式（跳过已存在数据）

**请求参数**：
- `mode`：重跑模式（可选：overwrite/append，默认 append）

**响应示例**：
```json
{
  "code": 200,
  "message": "批次重跑任务已提交",
  "data": {
    "batch_id": 123,
    "new_batch_id": 126,
    "mode": "append",
    "status": "pending"
  }
}
```

**权限控制**：
- 老板、财务：可重跑所有门店批次
- 门店经理：只能重跑本门店批次
- 记录审计日志：谁在什么时间重跑了哪个批次

### 2.4 校验报告接口

#### 2.4.1 批次校验报告查询

**接口路径**：`GET /api/v1/batches/{batch_id}/validation-report`

**功能描述**：
- 查询批次的详细校验报告
- 包含平衡校验、异常检测、会员支付去重校验结果

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "batch_id": 123,
    "batch_no": "20251203_100000_空境·派对KTV（万象城店）_booking_summary",
    "table_type": "booking_summary",
    "validation_summary": {
      "balance_check": {
        "total_checked": 100,
        "passed": 95,
        "failed": 5,
        "total_diff_amount": 12.50,
        "max_diff_amount": 5.00,
        "avg_diff_amount": 2.50
      },
      "anomaly_check": {
        "negative_amount": 2,
        "time_cross": 1,
        "missing_required": 2,
        "total_anomalies": 5
      },
      "member_payment_check": {
        "total_checked": 50,
        "passed": 48,
        "failed": 2,
        "total_diff_amount": 5.20
      }
    },
    "error_details": [
      {
        "row_number": 10,
        "error_type": "balance_check",
        "severity": "error",
        "message": "实收金额与支付方式合计不一致，差异：2.50元",
        "expected": 1000.00,
        "actual": 1002.50,
        "details": {
          "sales_amount": 1000.00,
          "deductions": 0.00,
          "payment_total": 1002.50
        }
      }
    ],
    "generated_at": "2025-12-03T10:05:00Z"
  }
}
```

#### 2.4.2 异常明细查询

**接口路径**：`GET /api/v1/batches/{batch_id}/validation-errors`

**功能描述**：
- 查询批次的异常明细列表
- 支持分页、按错误类型过滤

**查询参数**：
- `page`：页码（默认 1）
- `page_size`：每页数量（默认 50）
- `error_type`：错误类型（可选：balance_check/anomaly_check/member_payment_check）
- `severity`：严重程度（可选：error/warning/info）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 5,
    "page": 1,
    "page_size": 50,
    "items": [
      {
        "row_number": 10,
        "error_type": "balance_check",
        "severity": "error",
        "message": "实收金额与支付方式合计不一致，差异：2.50元",
        "expected": 1000.00,
        "actual": 1002.50,
        "details": {...}
      }
    ]
  }
}
```

### 2.5 聚合查询接口

#### 2.5.1 指标看板查询

**接口路径**：`GET /api/v1/dashboard/summary`

**功能描述**：
- 查询指标看板的核心指标汇总
- 支持按时间范围、门店、表类型聚合

**查询参数**：
- `start_date`：开始日期（必填，格式：YYYY-MM-DD）
- `end_date`：结束日期（必填，格式：YYYY-MM-DD）
- `store_id`：门店ID（可选，不传则查询所有门店）
- `table_type`：表类型（可选：booking_summary/room_analysis/beverage_sales，不传则查询所有类型）
- `granularity`：聚合粒度（可选：day/week/month，默认 day）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "period": {
      "start_date": "2025-12-01",
      "end_date": "2025-12-03",
      "granularity": "day"
    },
    "summary": {
      "booking_summary": {
        "total_sales_amount": 100000.00,
        "total_actual_received": 95000.00,
        "total_base_performance": 80000.00,
        "total_discount_amount": 3000.00,
        "total_gift_amount": 2000.00,
        "total_booking_count": 500,
        "discount_rate": 3.00,
        "gift_rate": 2.00,
        "actual_received_rate": 95.00
      },
      "room_analysis": {
        "total_bill_total": 150000.00,
        "total_actual_received": 145000.00,
        "total_base_performance": 120000.00,
        "total_order_count": 300,
        "avg_bill_amount": 500.00,
        "avg_duration_minutes": 180
      },
      "beverage_sales": {
        "total_sales_amount": 50000.00,
        "total_cost_total": 30000.00,
        "total_profit": 20000.00,
        "total_sales_qty": 1000,
        "avg_profit_rate": 66.67
      }
    }
  }
}
```

#### 2.5.2 预订汇总聚合查询

**接口路径**：`GET /api/v1/aggregations/booking-summary`

**功能描述**：
- 查询预订汇总表的聚合数据
- 支持按门店、员工、部门、时间维度聚合

**查询参数**：
- `start_date`：开始日期（必填）
- `end_date`：结束日期（必填）
- `store_id`：门店ID（可选）
- `employee_id`：员工ID（可选）
- `department`：部门（可选）
- `granularity`：聚合粒度（可选：day/week/month，默认 day）
- `group_by`：分组字段（可选：store/employee/department，默认 store）
- `page`：页码（默认 1）
- `page_size`：每页数量（默认 50）
- `sort_by`：排序字段（可选：actual_received/base_performance/sales_amount，默认 actual_received）
- `sort_order`：排序方向（可选：asc/desc，默认 desc）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 50,
    "items": [
      {
        "business_date": "2025-12-01",
        "store_id": 1,
        "store_name": "空境·派对KTV（万象城店）",
        "employee_id": 5,
        "employee_name": "申海宁",
        "department": "销售经理",
        "total_booking_count": 10,
        "total_sales_amount": 10000.00,
        "total_actual_received": 9500.00,
        "total_base_performance": 8000.00,
        "total_discount_amount": 300.00,
        "total_gift_amount": 200.00,
        "discount_rate": 3.00,
        "gift_rate": 2.00
      }
    ]
  }
}
```

#### 2.5.3 包厢开台聚合查询

**接口路径**：`GET /api/v1/aggregations/room-analysis`

**功能描述**：
- 查询包厢开台分析表的聚合数据
- 支持按门店、包厢、包厢类型、区域维度聚合

**查询参数**：
- `start_date`：开始日期（必填）
- `end_date`：结束日期（必填）
- `store_id`：门店ID（可选）
- `room_id`：包厢ID（可选）
- `room_type`：包厢类型（可选）
- `area_name`：区域名称（可选）
- `granularity`：聚合粒度（可选：day/week/month，默认 day）
- `group_by`：分组字段（可选：store/room/room_type/area，默认 store）
- `page`：页码（默认 1）
- `page_size`：每页数量（默认 50）
- `sort_by`：排序字段（可选：actual_received/bill_total/order_count，默认 actual_received）
- `sort_order`：排序方向（可选：asc/desc，默认 desc）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 50,
    "items": [
      {
        "business_date": "2025-12-01",
        "store_id": 1,
        "store_name": "空境·派对KTV（万象城店）",
        "room_id": 10,
        "room_name": "K01",
        "room_type": "电音中包",
        "area_name": "KTV区",
        "total_order_count": 5,
        "total_bill_total": 5000.00,
        "total_actual_received": 4800.00,
        "total_base_performance": 4000.00,
        "total_duration_minutes": 900,
        "avg_duration_minutes": 180.00,
        "avg_bill_amount": 1000.00
      }
    ]
  }
}
```

#### 2.5.4 酒水销售聚合查询

**接口路径**：`GET /api/v1/aggregations/beverage-sales`

**功能描述**：
- 查询酒水销售分析表的聚合数据
- 支持按门店、商品、商品类别、区域维度聚合

**查询参数**：
- `start_date`：开始日期（必填）
- `end_date`：结束日期（必填）
- `store_id`：门店ID（可选）
- `product_id`：商品ID（可选）
- `category_name`：类别名称（可选）
- `area`：区域（可选）
- `granularity`：聚合粒度（可选：day/week/month，默认 day）
- `group_by`：分组字段（可选：store/product/category/area，默认 store）
- `page`：页码（默认 1）
- `page_size`：每页数量（默认 50）
- `sort_by`：排序字段（可选：sales_amount/profit/profit_rate，默认 sales_amount）
- `sort_order`：排序方向（可选：asc/desc，默认 desc）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 10,
    "page": 1,
    "page_size": 50,
    "items": [
      {
        "business_date": "2025-12-01",
        "store_id": 1,
        "store_name": "空境·派对KTV（万象城店）",
        "product_id": 20,
        "beverage_name": "百威啤酒",
        "category_name": "啤酒",
        "unit": "瓶",
        "area": "KTV区",
        "total_sales_qty": 100,
        "total_sales_amount": 5000.00,
        "total_cost_total": 3000.00,
        "total_profit": 2000.00,
        "avg_profit_rate": 66.67,
        "sales_amount_per_qty": 50.00
      }
    ]
  }
}
```

#### 2.5.5 TopN 查询

**接口路径**：`GET /api/v1/aggregations/topn`

**功能描述**：
- 查询 TopN 结果（如 TopN 员工、TopN 商品、TopN 包厢）

**查询参数**：
- `table_type`：表类型（必填：booking_summary/room_analysis/beverage_sales）
- `dimension`：维度（必填：employee/product/room/department/category）
- `metric`：指标（必填：actual_received/base_performance/sales_amount/profit）
- `start_date`：开始日期（必填）
- `end_date`：结束日期（必填）
- `store_id`：门店ID（可选）
- `top_n`：TopN 数量（可选，默认 10，最大 100）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "table_type": "booking_summary",
    "dimension": "employee",
    "metric": "actual_received",
    "top_n": 10,
    "items": [
      {
        "employee_id": 5,
        "employee_name": "申海宁",
        "department": "销售经理",
        "store_id": 1,
        "store_name": "空境·派对KTV（万象城店）",
        "value": 50000.00,
        "rank": 1
      }
    ]
  }
}
```

### 2.6 数据导出接口

#### 2.6.1 导出 CSV

**接口路径**：`GET /api/v1/export/csv`

**功能描述**：
- 导出查询结果为 CSV 格式
- 支持导出聚合查询结果、批次明细、异常明细

**查询参数**：
- `export_type`：导出类型（必填：aggregation/batch-detail/validation-errors）
- 其他参数与对应查询接口相同（如 start_date、end_date、store_id 等）

**响应**：
- Content-Type: `text/csv; charset=utf-8`
- Content-Disposition: `attachment; filename="export_YYYYMMDD_HHMMSS.csv"`
- 返回 CSV 文件内容

**实施细节**：
1. 使用 pandas 生成 CSV
2. 支持大数据量导出（使用流式响应）
3. 文件名包含时间戳和查询条件
4. 记录导出操作到审计日志

### 2.7 维度数据接口

#### 2.7.1 门店列表

**接口路径**：`GET /api/v1/dimensions/stores`

**功能描述**：
- 查询门店列表（用于筛选器）

**查询参数**：
- `is_active`：是否启用（可选，默认 true）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "store_id": 1,
      "store_code": "STORE_001",
      "store_name": "空境·派对KTV（万象城店）",
      "region": "万象城",
      "city": "成都",
      "is_active": true
    }
  ]
}
```

#### 2.7.2 员工列表

**接口路径**：`GET /api/v1/dimensions/employees`

**功能描述**：
- 查询员工列表（用于筛选器）

**查询参数**：
- `store_id`：门店ID（可选）
- `department`：部门（可选）
- `is_active`：是否在职（可选，默认 true）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "employee_id": 5,
      "employee_code": "EMP_005",
      "employee_name": "申海宁",
      "department": "销售经理",
      "store_id": 1,
      "store_name": "空境·派对KTV（万象城店）",
      "is_active": true
    }
  ]
}
```

#### 2.7.3 包厢列表

**接口路径**：`GET /api/v1/dimensions/rooms`

**功能描述**：
- 查询包厢列表（用于筛选器）

**查询参数**：
- `store_id`：门店ID（可选）
- `room_type`：包厢类型（可选）
- `area_name`：区域名称（可选）
- `is_active`：是否启用（可选，默认 true）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "room_id": 10,
      "room_code": "K01",
      "room_name": "K01",
      "room_type": "电音中包",
      "area_name": "KTV区",
      "store_id": 1,
      "store_name": "空境·派对KTV（万象城店）",
      "is_active": true
    }
  ]
}
```

#### 2.7.4 商品列表

**接口路径**：`GET /api/v1/dimensions/products`

**功能描述**：
- 查询商品列表（用于筛选器）

**查询参数**：
- `store_id`：门店ID（可选）
- `category_name`：类别名称（可选）
- `area`：区域（可选）
- `is_active`：是否启用（可选，默认 true）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "product_id": 20,
      "product_code": "PROD_020",
      "product_name": "百威啤酒",
      "category_name": "啤酒",
      "unit": "瓶",
      "area": "KTV区",
      "is_active": true
    }
  ]
}
```

### 2.8 系统接口

#### 2.8.1 健康检查

**接口路径**：`GET /api/v1/health`

**功能描述**：
- 检查系统健康状态
- 检查数据库连接、文件系统可用性

**响应示例**：
```json
{
  "code": 200,
  "message": "healthy",
  "data": {
    "status": "healthy",
    "database": "connected",
    "file_system": "available",
    "timestamp": "2025-12-03T10:00:00Z"
  }
}
```

#### 2.8.2 版本信息

**接口路径**：`GET /api/v1/version`

**功能描述**：
- 返回 API 版本信息

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "version": "v1.0",
    "build_date": "2025-12-03",
    "api_version": "v1"
  }
}
```

---

## 三、前端界面设计

### 3.1 前端架构设计

**技术栈选择**：
- **框架**：React（推荐）或 Vue
- **UI 组件库**：Ant Design（React）或 Element UI（Vue）
- **图表库**：ECharts
- **状态管理**：Redux（React）或 Vuex（Vue）
- **路由**：React Router 或 Vue Router
- **HTTP 客户端**：Axios
- **构建工具**：Vite 或 Create React App

**项目结构**：
```
frontend/
├── src/
│   ├── components/          # 公共组件
│   │   ├── Layout/          # 布局组件
│   │   ├── Table/           # 表格组件
│   │   ├── Chart/           # 图表组件
│   │   ├── Filter/          # 筛选器组件
│   │   └── Upload/          # 上传组件
│   ├── pages/               # 页面组件
│   │   ├── Login/           # 登录页
│   │   ├── Dashboard/      # 指标看板
│   │   ├── BatchManagement/ # 批次管理
│   │   ├── DataQuery/       # 数据查询
│   │   └── ValidationReport/ # 校验报告
│   ├── services/            # API 服务
│   ├── store/               # 状态管理
│   ├── utils/               # 工具函数
│   ├── hooks/               # 自定义 Hooks
│   └── App.jsx              # 根组件
├── public/                  # 静态资源
└── package.json
```

### 3.2 登录与权限管理

#### 3.2.1 登录页面

**功能描述**：
- 用户登录界面
- 支持用户名/密码登录
- 登录成功后保存 Token 到 localStorage

**界面元素**：
- 用户名输入框
- 密码输入框
- 登录按钮
- 记住我选项（可选）

**实施细节**：
1. 调用登录 API：`POST /api/v1/auth/login`
2. 保存 Token 和用户信息到 localStorage
3. 跳转到首页或之前访问的页面
4. 设置 Token 到 Axios 请求头

#### 3.2.2 权限控制

**角色定义**：
- **老板**：可查看所有门店数据，可上传、重跑所有批次
- **财务**：可查看所有门店数据，可上传、重跑所有批次
- **门店经理**：只能查看本门店数据，只能上传、重跑本门店批次

**权限实现**：
1. 路由守卫：检查用户角色和权限
2. 组件级权限：根据角色显示/隐藏功能按钮
3. API 请求拦截：在请求头中添加门店过滤条件（门店经理）

### 3.3 文件上传界面

#### 3.3.1 上传页面

**功能描述**：
- 文件上传界面
- 支持单文件上传和批量上传
- 显示上传进度
- 上传成功后显示批次信息

**界面元素**：
- 文件选择按钮（支持拖拽上传）
- 文件列表（显示已选择的文件）
- 门店选择下拉框（可选，从文件名解析）
- 表类型选择下拉框（可选，从文件名推断）
- 上传按钮
- 上传进度条
- 批次信息卡片（上传成功后显示）

**实施细节**：
1. 使用 Ant Design Upload 组件或自定义上传组件
2. 支持文件类型验证（CSV/xls/xlsx）
3. 支持文件大小限制（100MB）
4. 显示上传进度（使用 axios 的 onUploadProgress）
5. 上传成功后跳转到批次详情页或显示批次信息

### 3.4 批次管理界面

#### 3.4.1 批次列表页面

**功能描述**：
- 显示批次列表
- 支持筛选、排序、分页
- 支持批次状态查看、重跑操作

**界面元素**：
- 筛选器：
  - 门店选择（下拉框）
  - 表类型选择（下拉框）
  - 状态选择（下拉框）
  - 时间范围选择（日期选择器）
- 批次列表表格：
  - 批次号
  - 文件名
  - 门店名称
  - 表类型
  - 时间范围
  - 状态（带状态标签）
  - 统计信息（总行数、成功行数、失败行数）
  - 创建时间
  - 操作按钮（查看详情、重跑）
- 分页组件

**实施细节**：
1. 使用 Ant Design Table 组件
2. 状态标签使用不同颜色（成功-绿色、失败-红色、处理中-蓝色）
3. 点击批次号或文件名跳转到批次详情页
4. 重跑操作需要确认对话框

#### 3.4.2 批次详情页面

**功能描述**：
- 显示批次详细信息
- 显示校验报告
- 显示异常明细

**界面元素**：
- 批次基本信息卡片：
  - 批次号、文件名、文件路径、文件大小
  - 门店、表类型、时间范围
  - 状态、统计信息
  - 创建时间、完成时间
- 校验报告卡片：
  - 平衡校验结果（通过率、差异金额）
  - 异常检测结果（异常数量、类型）
  - 会员支付去重校验结果
- 异常明细表格：
  - 行号、错误类型、严重程度、错误消息
  - 支持分页、按错误类型过滤
- 操作按钮：
  - 重跑批次
  - 导出异常明细

**实施细节**：
1. 使用 Tabs 组件切换基本信息、校验报告、异常明细
2. 校验报告使用卡片和统计图表展示
3. 异常明细表格支持排序和过滤

### 3.5 指标看板界面

#### 3.5.1 看板页面

**功能描述**：
- 展示核心指标汇总
- 支持时间范围、门店筛选
- 使用图表可视化展示趋势

**界面元素**：
- 筛选器：
  - 时间范围选择（日期选择器，默认最近7天）
  - 门店选择（下拉框，多选）
  - 表类型选择（下拉框，多选）
  - 聚合粒度选择（日/周/月）
- 核心指标卡片：
  - 预订汇总指标：
    - 销售金额、实收金额、基本业绩
    - 折扣金额、赠送金额、订台数
    - 折扣率、赠送率、实收率
  - 包厢开台指标：
    - 账单合计、实收金额、基本业绩
    - 开台单数、平均账单金额、平均消费时长
  - 酒水销售指标：
    - 销售金额、成本小计、利润
    - 销售数量、平均利润率
- 趋势图表：
  - 实收金额趋势图（折线图）
  - 销售金额 vs 实收金额对比图（柱状图）
  - 折扣率趋势图（折线图）
  - 利润率趋势图（折线图）
- 明细表格：
  - 按时间粒度展示明细数据
  - 支持排序、导出

**实施细节**：
1. 使用 ECharts 绘制图表
2. 指标卡片使用数字动画效果（countUp.js）
3. 图表支持时间范围切换（日/周/月）
4. 图表支持数据钻取（点击图表跳转到明细页）

### 3.6 数据查询界面

#### 3.6.1 查询页面

**功能描述**：
- 支持多维度数据查询
- 支持聚合查询和 TopN 查询
- 支持数据表格和图表展示

**界面元素**：
- 查询筛选器：
  - 表类型选择（单选：预订汇总/包厢开台/酒水销售）
  - 时间范围选择（日期选择器）
  - 门店选择（下拉框，多选）
  - 员工选择（下拉框，多选，仅预订汇总）
  - 包厢选择（下拉框，多选，仅包厢开台）
  - 商品选择（下拉框，多选，仅酒水销售）
  - 聚合粒度选择（日/周/月）
  - 分组字段选择（门店/员工/包厢/商品等）
- 查询结果：
  - 数据表格：
    - 支持排序、分页
    - 支持列筛选
    - 支持导出 CSV
  - 图表展示：
    - 柱状图（按维度对比）
    - 折线图（趋势分析）
    - 饼图（占比分析）
- TopN 查询：
  - 维度选择（员工/商品/包厢等）
  - 指标选择（实收金额/基本业绩/销售金额等）
  - TopN 数量选择（10/20/50）
  - TopN 排行榜表格和图表

**实施细节**：
1. 使用 Tabs 组件切换不同表类型的查询
2. 筛选器组件支持联动（选择表类型后，显示对应的筛选字段）
3. 查询结果支持表格和图表两种视图切换
4. 图表类型根据数据特点自动选择（时间序列用折线图，分类对比用柱状图）

### 3.7 校验报告界面

#### 3.7.1 报告查看页面

**功能描述**：
- 查看批次校验报告
- 查看异常明细
- 支持报告导出

**界面元素**：
- 批次选择（下拉框或搜索框）
- 校验报告概览：
  - 平衡校验统计（通过率、失败数、差异金额）
  - 异常检测统计（异常数量、类型分布）
  - 会员支付去重校验统计
- 异常明细表格：
  - 行号、错误类型、严重程度、错误消息
  - 预期值、实际值、差异
  - 支持分页、排序、过滤
- 图表展示：
  - 错误类型分布（饼图）
  - 严重程度分布（柱状图）
  - 差异金额分布（直方图）
- 操作按钮：
  - 导出报告（PDF/Excel）
  - 导出异常明细（CSV）

**实施细节**：
1. 校验报告使用卡片和统计图表展示
2. 异常明细表格支持按错误类型、严重程度过滤
3. 支持报告导出功能（使用 jsPDF 或后端生成）

### 3.8 数据导出功能

#### 3.8.1 导出实现

**功能描述**：
- 支持导出查询结果为 CSV
- 支持导出批次明细
- 支持导出异常明细

**实施细节**：
1. 调用导出 API：`GET /api/v1/export/csv`
2. 使用 `Blob` 和 `URL.createObjectURL` 下载文件
3. 文件名包含时间戳和查询条件
4. 大数据量导出显示进度条（使用流式下载）

---

## 四、权限与安全

### 4.1 权限模型设计

#### 4.1.1 角色定义

**角色类型**：
- **老板（owner）**：
  - 可查看所有门店数据
  - 可上传所有门店文件
  - 可重跑所有批次
  - 可查看所有校验报告
  - 可导出所有数据
  
- **财务（finance）**：
  - 可查看所有门店数据
  - 可上传所有门店文件
  - 可重跑所有批次
  - 可查看所有校验报告
  - 可导出所有数据
  
- **门店经理（store_manager）**：
  - 只能查看本门店数据
  - 只能上传本门店文件
  - 只能重跑本门店批次
  - 只能查看本门店校验报告
  - 只能导出本门店数据

#### 4.1.2 权限实现

**后端权限控制**：
1. **JWT Token 认证**：
   - 登录后生成 JWT Token
   - Token 包含用户ID、角色、门店ID（门店经理）
   - 每个 API 请求携带 Token
   - 后端验证 Token 有效性

2. **角色权限中间件**：
   - 检查用户角色
   - 门店经理自动过滤门店ID
   - 记录操作日志

3. **数据隔离**：
   - 门店经理查询自动添加 `store_id` 过滤条件
   - 文件上传验证门店权限
   - 批次重跑验证门店权限

**前端权限控制**：
1. **路由守卫**：
   - 检查用户登录状态
   - 检查用户角色权限
   - 无权限跳转到403页面

2. **组件级权限**：
   - 根据角色显示/隐藏功能按钮
   - 根据角色禁用/启用筛选器选项

### 4.2 审计日志

#### 4.2.1 日志记录内容

**记录的操作**：
- 文件上传：用户、文件名、门店、时间
- 批次重跑：用户、批次ID、重跑模式、时间
- 数据查询：用户、查询条件、查询时间
- 数据导出：用户、导出类型、导出条件、时间
- 登录/登出：用户、IP地址、时间

**日志表结构**（参考《入库模型.md》）：
- `id`：日志ID
- `user_id`：用户ID
- `user_name`：用户名
- `user_role`：用户角色
- `action_type`：操作类型（upload/rerun/query/export/login/logout）
- `resource_type`：资源类型（file/batch/query/export）
- `resource_id`：资源ID（批次ID、查询ID等）
- `details`：详细信息（JSON格式）
- `ip_address`：IP地址
- `created_at`：创建时间

#### 4.2.2 日志查询接口

**接口路径**：`GET /api/v1/audit-logs`

**查询参数**：
- `user_id`：用户ID（可选）
- `action_type`：操作类型（可选）
- `start_date`：开始日期（可选）
- `end_date`：结束日期（可选）
- `page`：页码（默认 1）
- `page_size`：每页数量（默认 50）

**权限控制**：
- 老板、财务：可查看所有日志
- 门店经理：只能查看自己的日志

### 4.3 安全措施

#### 4.3.1 认证安全

1. **密码加密**：
   - 使用 bcrypt 加密存储密码
   - 密码强度要求（至少8位，包含字母和数字）

2. **Token 安全**：
   - Token 设置过期时间（如24小时）
   - Token 刷新机制（使用 refresh token）
   - Token 存储在 httpOnly cookie 或 localStorage

3. **防止暴力破解**：
   - 登录失败次数限制（5次失败锁定30分钟）
   - 验证码（可选，登录失败3次后显示）

#### 4.3.2 数据安全

1. **SQL 注入防护**：
   - 使用 SQLAlchemy ORM，避免直接拼接 SQL
   - 参数化查询

2. **XSS 防护**：
   - 前端输入验证和转义
   - 使用 React/Vue 的自动转义机制

3. **CSRF 防护**：
   - 使用 CSRF Token
   - 同源策略

4. **文件上传安全**：
   - 文件类型验证（白名单）
   - 文件大小限制
   - 文件名清理（防止路径遍历）
   - 病毒扫描（可选）

---

## 五、实施步骤与方法

### 5.1 第一阶段：后端 API 基础框架

#### 5.1.1 项目初始化

**步骤**：
1. 创建 FastAPI 项目结构
2. 配置数据库连接（SQLAlchemy）
3. 配置日志系统
4. 配置环境变量（.env）

**项目结构**：
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置文件
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 模型
│   ├── schemas/             # Pydantic 模型
│   ├── api/                 # API 路由
│   │   ├── __init__.py
│   │   ├── auth.py          # 认证相关
│   │   ├── files.py          # 文件上传
│   │   ├── batches.py        # 批次管理
│   │   ├── aggregations.py   # 聚合查询
│   │   └── export.py         # 数据导出
│   ├── services/            # 业务逻辑
│   │   ├── file_service.py
│   │   ├── batch_service.py
│   │   └── aggregation_service.py
│   └── utils/               # 工具函数
│       ├── auth.py          # 认证工具
│       └── validators.py    # 验证工具
├── alembic/                 # 数据库迁移
├── tests/                   # 测试文件
├── requirements.txt
└── .env
```

#### 5.1.2 实现认证与权限

**步骤**：
1. 实现 JWT Token 生成和验证
2. 实现用户登录接口
3. 实现权限中间件
4. 实现角色权限装饰器

**接口**：
- `POST /api/v1/auth/login`：登录
- `POST /api/v1/auth/logout`：登出
- `GET /api/v1/auth/me`：获取当前用户信息

#### 5.1.3 实现文件上传接口

**步骤**：
1. 实现文件上传接口（单文件、批量）
2. 实现文件存储逻辑（本地文件系统）
3. 实现文件类型和大小验证
4. 实现批次记录创建
5. 实现异步解析任务触发（Celery 或后台任务）

**接口**：
- `POST /api/v1/files/upload`：单文件上传
- `POST /api/v1/files/batch-upload`：批量上传

### 5.2 第二阶段：批次管理与校验报告

#### 5.2.1 实现批次管理接口

**步骤**：
1. 实现批次列表查询接口（支持分页、排序、过滤）
2. 实现批次详情查询接口
3. 实现批次重跑接口
4. 实现权限控制（门店经理只能操作本门店）

**接口**：
- `GET /api/v1/batches`：批次列表
- `GET /api/v1/batches/{batch_id}`：批次详情
- `POST /api/v1/batches/{batch_id}/rerun`：批次重跑

#### 5.2.2 实现校验报告接口

**步骤**：
1. 实现校验报告查询接口
2. 实现异常明细查询接口（支持分页、过滤）
3. 实现报告数据格式化

**接口**：
- `GET /api/v1/batches/{batch_id}/validation-report`：校验报告
- `GET /api/v1/batches/{batch_id}/validation-errors`：异常明细

### 5.3 第三阶段：聚合查询接口

#### 5.3.1 实现指标看板接口

**步骤**：
1. 实现指标看板汇总查询接口
2. 实现多表类型聚合逻辑
3. 实现时间粒度聚合（日/周/月）

**接口**：
- `GET /api/v1/dashboard/summary`：指标看板

#### 5.3.2 实现聚合查询接口

**步骤**：
1. 实现预订汇总聚合查询接口
2. 实现包厢开台聚合查询接口
3. 实现酒水销售聚合查询接口
4. 实现 TopN 查询接口
5. 实现权限控制（门店经理自动过滤）

**接口**：
- `GET /api/v1/aggregations/booking-summary`：预订汇总聚合
- `GET /api/v1/aggregations/room-analysis`：包厢开台聚合
- `GET /api/v1/aggregations/beverage-sales`：酒水销售聚合
- `GET /api/v1/aggregations/topn`：TopN 查询

#### 5.3.3 实现维度数据接口

**步骤**：
1. 实现门店列表接口
2. 实现员工列表接口
3. 实现包厢列表接口
4. 实现商品列表接口
5. 实现权限控制（门店经理只能查看本门店数据）

**接口**：
- `GET /api/v1/dimensions/stores`：门店列表
- `GET /api/v1/dimensions/employees`：员工列表
- `GET /api/v1/dimensions/rooms`：包厢列表
- `GET /api/v1/dimensions/products`：商品列表

### 5.4 第四阶段：数据导出接口

#### 5.4.1 实现导出接口

**步骤**：
1. 实现 CSV 导出接口
2. 实现流式响应（大数据量）
3. 实现文件名生成逻辑
4. 实现审计日志记录

**接口**：
- `GET /api/v1/export/csv`：导出 CSV

### 5.5 第五阶段：前端基础框架

#### 5.5.1 项目初始化

**步骤**：
1. 创建 React/Vue 项目
2. 配置路由（React Router/Vue Router）
3. 配置状态管理（Redux/Vuex）
4. 配置 Axios（HTTP 客户端）
5. 配置 UI 组件库（Ant Design/Element UI）
6. 配置 ECharts

**项目结构**：
```
frontend/
├── src/
│   ├── components/          # 公共组件
│   ├── pages/               # 页面组件
│   ├── services/            # API 服务
│   ├── store/               # 状态管理
│   ├── utils/               # 工具函数
│   ├── hooks/               # 自定义 Hooks
│   └── App.jsx
├── public/
└── package.json
```

#### 5.5.2 实现登录与权限

**步骤**：
1. 实现登录页面
2. 实现 Token 管理（localStorage）
3. 实现路由守卫
4. 实现权限控制组件

### 5.6 第六阶段：文件上传与批次管理界面

#### 5.6.1 实现文件上传界面

**步骤**：
1. 实现文件上传组件
2. 实现上传进度显示
3. 实现批次信息展示
4. 实现错误处理

#### 5.6.2 实现批次管理界面

**步骤**：
1. 实现批次列表页面
2. 实现批次详情页面
3. 实现批次重跑功能
4. 实现筛选和排序功能

### 5.7 第七阶段：指标看板与数据查询界面

#### 5.7.1 实现指标看板界面

**步骤**：
1. 实现指标卡片组件
2. 实现趋势图表组件（ECharts）
3. 实现筛选器组件
4. 实现数据钻取功能

#### 5.7.2 实现数据查询界面

**步骤**：
1. 实现查询筛选器组件
2. 实现数据表格组件
3. 实现图表展示组件
4. 实现 TopN 查询界面

### 5.8 第八阶段：校验报告与导出功能

#### 5.8.1 实现校验报告界面

**步骤**：
1. 实现校验报告展示组件
2. 实现异常明细表格组件
3. 实现报告图表组件
4. 实现报告导出功能

#### 5.8.2 实现数据导出功能

**步骤**：
1. 实现导出按钮组件
2. 实现导出进度显示
3. 实现文件下载功能

### 5.9 第九阶段：审计日志与安全加固

#### 5.9.1 实现审计日志

**步骤**：
1. 实现审计日志记录中间件
2. 实现审计日志查询接口
3. 实现审计日志查看界面（可选）

#### 5.9.2 安全加固

**步骤**：
1. 实现密码加密
2. 实现 Token 刷新机制
3. 实现登录失败限制
4. 实现文件上传安全验证
5. 实现 XSS/CSRF 防护

---

## 六、测试策略

### 6.1 后端 API 测试

#### 6.1.1 单元测试

**测试内容**：
- 认证与权限函数测试
- 文件上传逻辑测试
- 聚合查询逻辑测试
- 数据导出逻辑测试

**测试框架**：pytest

#### 6.1.2 集成测试

**测试内容**：
- 文件上传端到端测试
- 批次管理流程测试
- 聚合查询流程测试
- 权限控制测试

**测试框架**：pytest + FastAPI TestClient

### 6.2 前端测试

#### 6.2.1 组件测试

**测试内容**：
- 组件渲染测试
- 用户交互测试
- 权限控制测试

**测试框架**：Jest + React Testing Library（React）或 Jest + Vue Test Utils（Vue）

#### 6.2.2 E2E 测试

**测试内容**：
- 登录流程测试
- 文件上传流程测试
- 数据查询流程测试
- 数据导出流程测试

**测试框架**：Cypress 或 Playwright

### 6.3 性能测试

#### 6.3.1 API 性能测试

**测试内容**：
- 接口响应时间测试
- 并发请求测试
- 大数据量查询测试

**测试工具**：Locust 或 Apache JMeter

#### 6.3.2 前端性能测试

**测试内容**：
- 页面加载时间测试
- 图表渲染性能测试
- 大数据量表格性能测试

**测试工具**：Lighthouse、WebPageTest

---

## 七、部署与运维

### 7.1 部署方案

#### 7.1.1 后端部署

**部署方式**：
- **开发环境**：本地运行（`uvicorn app.main:app --reload`）
- **生产环境**：Docker 容器 + Nginx 反向代理

**Dockerfile 示例**：
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 7.1.2 前端部署

**部署方式**：
- **开发环境**：本地运行（`npm run dev`）
- **生产环境**：构建静态文件 + Nginx 部署

**构建命令**：
```bash
npm run build
```

**Nginx 配置**：
- 静态文件服务
- API 请求代理到后端

### 7.2 监控与告警

#### 7.2.1 监控指标

**后端监控**：
- API 响应时间
- API 错误率
- 数据库连接数
- 文件上传成功率

**前端监控**：
- 页面加载时间
- JavaScript 错误率
- API 请求失败率

**监控工具**：
- Prometheus + Grafana（后端）
- Sentry（错误监控）

#### 7.2.2 告警规则

**告警条件**：
- API 响应时间 > 5秒
- API 错误率 > 5%
- 数据库连接数 > 80%
- 文件上传失败率 > 10%

**告警渠道**：
- 邮件
- 企业微信/钉钉
- 短信（紧急告警）

---

## 八、总结

### 8.1 核心要点

1. **API 设计**：遵循 RESTful 规范，支持分页、排序、过滤
2. **权限控制**：基于角色的访问控制，数据隔离
3. **前端界面**：响应式设计，支持多维度查询和可视化
4. **安全措施**：JWT 认证、权限验证、审计日志
5. **性能优化**：分页查询、索引优化、缓存策略

### 8.2 后续工作

1. **实施开发**：按照实施步骤，逐步实现 Web 界面与接口功能
2. **测试验证**：完成单元测试、集成测试、E2E 测试
3. **性能优化**：根据实际使用情况，优化查询性能和用户体验
4. **功能扩展**：支持更多查询维度、更多图表类型、更多导出格式

---

## 附录

### A. API 接口清单

**认证相关**：
- `POST /api/v1/auth/login`：登录
- `POST /api/v1/auth/logout`：登出
- `GET /api/v1/auth/me`：获取当前用户信息

**文件管理**：
- `POST /api/v1/files/upload`：单文件上传
- `POST /api/v1/files/batch-upload`：批量上传

**批次管理**：
- `GET /api/v1/batches`：批次列表
- `GET /api/v1/batches/{batch_id}`：批次详情
- `POST /api/v1/batches/{batch_id}/rerun`：批次重跑

**校验报告**：
- `GET /api/v1/batches/{batch_id}/validation-report`：校验报告
- `GET /api/v1/batches/{batch_id}/validation-errors`：异常明细

**聚合查询**：
- `GET /api/v1/dashboard/summary`：指标看板
- `GET /api/v1/aggregations/booking-summary`：预订汇总聚合
- `GET /api/v1/aggregations/room-analysis`：包厢开台聚合
- `GET /api/v1/aggregations/beverage-sales`：酒水销售聚合
- `GET /api/v1/aggregations/topn`：TopN 查询

**维度数据**：
- `GET /api/v1/dimensions/stores`：门店列表
- `GET /api/v1/dimensions/employees`：员工列表
- `GET /api/v1/dimensions/rooms`：包厢列表
- `GET /api/v1/dimensions/products`：商品列表

**数据导出**：
- `GET /api/v1/export/csv`：导出 CSV

**系统接口**：
- `GET /api/v1/health`：健康检查
- `GET /api/v1/version`：版本信息

### B. 参考文档

- 《具体需求.md》：业务需求说明
- 《解析与清洗.md》：数据解析与清洗规范
- 《入库模型.md》：数据库入库模型设计
- 《聚合.md》：聚合与口径计算设计
- 《详细业务分析实现.md》：整体技术方案

### C. 版本历史

- **v1.0**（2025-12-03）：初始版本，完成 Web 界面与接口设计文档

---

**文档结束**

