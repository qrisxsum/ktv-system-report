-- ========================================
-- KTV 报表系统 - 数据库初始化脚本
-- ========================================

-- 确保使用 UTF8MB4 编码
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ktv_report 
    DEFAULT CHARACTER SET utf8mb4 
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ktv_report;

-- ========================================
-- 1. 维度建模表结构 (Alembic迁移版本)
-- ========================================

-- ========================================
-- 用户表 (User Table)
-- ========================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    hashed_password VARCHAR(255) NOT NULL COMMENT '密码哈希',
    role VARCHAR(20) NOT NULL COMMENT '角色: admin/manager',
    store_id INT COMMENT '关联门店ID (管理员为NULL)',
    full_name VARCHAR(100) COMMENT '真实姓名',
    email VARCHAR(100) COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    last_login_at DATETIME COMMENT '最后登录时间',
    current_token VARCHAR(500) COMMENT '当前有效的token (用于单设备登录控制)',
    token_expires_at DATETIME COMMENT 'token过期时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

CREATE UNIQUE INDEX idx_username ON users (username);
CREATE INDEX idx_role ON users (role);
CREATE INDEX idx_store_id ON users (store_id);

-- 插入初始用户数据
-- 管理员用户 (可以访问所有门店)
INSERT INTO users (username, hashed_password, role, store_id, full_name, email, phone, is_active)
VALUES (
    'admin',
    '$pbkdf2-sha256$29000$.n8PgXDufa91zjlnbE3J.Q$P5vIMVWWgkxXfwVBC4vuSC2MTDk49w0ntDTlF8oMhso', -- 密码: admin123
    'admin',
    NULL,
    '系统管理员',
    'admin@ktv.com',
    '13800138000',
    TRUE
);

-- 店长用户 (只能访问门店1)
INSERT INTO users (username, hashed_password, role, store_id, full_name, email, phone, is_active)
VALUES (
    'manager',
    '$pbkdf2-sha256$29000$wxjjPAegtBYiZExpjRFibA$XXxQ9BL4LBGC0Hp7FOsmgVdTUYyksQEdsHRIlqGoeOU', -- 密码: manager123
    'manager',
    1,
    '门店店长',
    'manager@ktv.com',
    '13800138001',
    TRUE
);

-- ========================================
-- 维度表 (Dimension Tables)
-- ========================================

-- 员工维度表
CREATE TABLE IF NOT EXISTS dim_employee (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '代理键',
    store_id INT NOT NULL COMMENT '关联门店',
    name VARCHAR(50) NOT NULL COMMENT '员工姓名',
    department VARCHAR(50) COMMENT '部门',
    position VARCHAR(50) COMMENT '职位',
    is_active BOOLEAN COMMENT '是否在职',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工维度表';

CREATE INDEX idx_store_name ON dim_employee (store_id, name);
CREATE INDEX ix_dim_employee_store_id ON dim_employee (store_id);

-- 支付方式维度表
CREATE TABLE IF NOT EXISTS dim_payment_method (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '代理键',
    code VARCHAR(50) NOT NULL UNIQUE COMMENT '支付方式代码',
    name VARCHAR(50) NOT NULL COMMENT '支付方式名称',
    category VARCHAR(20) NOT NULL COMMENT '分类: income/equity/cost',
    is_core BOOLEAN COMMENT '是否核心字段(独立建列)',
    sort_order INT COMMENT '排序顺序',
    is_active BOOLEAN COMMENT '是否启用'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='支付方式维度表';

CREATE INDEX idx_category ON dim_payment_method (category);
CREATE UNIQUE INDEX idx_code ON dim_payment_method (code);

-- 商品维度表
CREATE TABLE IF NOT EXISTS dim_product (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '代理键',
    store_id INT NOT NULL COMMENT '关联门店',
    name VARCHAR(100) NOT NULL COMMENT '商品名称',
    category VARCHAR(50) COMMENT '商品分类',
    unit VARCHAR(20) COMMENT '单位',
    price INT COMMENT '单价(分)',
    cost INT COMMENT '成本(分)',
    is_active BOOLEAN COMMENT '是否在售',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品维度表';

CREATE INDEX idx_category ON dim_product (category);
CREATE INDEX idx_store_product ON dim_product (store_id, name);
CREATE INDEX ix_dim_product_store_id ON dim_product (store_id);

-- 包厢维度表
CREATE TABLE IF NOT EXISTS dim_room (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '代理键',
    store_id INT NOT NULL COMMENT '关联门店',
    room_no VARCHAR(50) NOT NULL COMMENT '包厢号',
    room_name VARCHAR(50) COMMENT '包厢名称',
    room_type VARCHAR(50) COMMENT '包厢类型',
    area_name VARCHAR(50) COMMENT '区域名称',
    capacity INT COMMENT '容纳人数',
    is_active BOOLEAN COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='包厢维度表';

CREATE INDEX idx_room_type ON dim_room (room_type);
CREATE UNIQUE INDEX idx_store_room ON dim_room (store_id, room_no);
CREATE INDEX ix_dim_room_store_id ON dim_room (store_id);

-- 门店维度表
CREATE TABLE IF NOT EXISTS dim_store (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '代理键',
    store_code VARCHAR(20) UNIQUE COMMENT '门店编码',
    store_name VARCHAR(100) NOT NULL UNIQUE COMMENT '门店名(标准化)',
    original_name VARCHAR(100) COMMENT '原始门店名(用于匹配)',
    region VARCHAR(50) COMMENT '所属区域/城市',
    address VARCHAR(200) COMMENT '门店地址',
    is_active BOOLEAN COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='门店维度表';

CREATE INDEX idx_store_code ON dim_store (store_code);
CREATE UNIQUE INDEX idx_store_name ON dim_store (store_name);

-- ========================================
-- 事实表 (Fact Tables)
-- ========================================

-- 预订汇总事实表
CREATE TABLE IF NOT EXISTS fact_booking (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    batch_id BIGINT NOT NULL COMMENT '关联批次',
    biz_date DATE NOT NULL COMMENT '营业日期',
    store_id INT NOT NULL COMMENT '关联门店',
    employee_id INT COMMENT '关联员工(订位人)',
    department VARCHAR(50) COMMENT '部门(冗余)',
    customer_name VARCHAR(50) COMMENT '订位人/客户名',
    booking_qty INT DEFAULT 0 COMMENT '订台数',
    sales_amount DECIMAL(12,2) DEFAULT 0 COMMENT '销售金额(应收)',
    actual_amount DECIMAL(12,2) DEFAULT 0 COMMENT '实收金额',
    base_performance DECIMAL(12,2) DEFAULT 0 COMMENT '基本业绩',
    service_fee DECIMAL(12,2) DEFAULT 0 COMMENT '服务费',
    auto_deduction DECIMAL(12,2) DEFAULT 0 COMMENT '自动扣减',
    gift_amount DECIMAL(12,2) DEFAULT 0 COMMENT '赠送金额',
    discount_amount DECIMAL(12,2) DEFAULT 0 COMMENT '折扣金额',
    free_amount DECIMAL(12,2) DEFAULT 0 COMMENT '免单金额',
    credit_amount DECIMAL(12,2) DEFAULT 0 COMMENT '挂账金额',
    round_off_amount DECIMAL(12,2) DEFAULT 0 COMMENT '抹零金额',
    adjustment_amount DECIMAL(12,2) DEFAULT 0 COMMENT '调整金额',
    pay_wechat DECIMAL(12,2) DEFAULT 0 COMMENT '微信支付',
    pay_alipay DECIMAL(12,2) DEFAULT 0 COMMENT '支付宝',
    pay_cash DECIMAL(12,2) DEFAULT 0 COMMENT '现金',
    pay_pos DECIMAL(12,2) DEFAULT 0 COMMENT 'POS/银行卡',
    pay_member DECIMAL(12,2) DEFAULT 0 COMMENT '会员支付',
    pay_douyin DECIMAL(12,2) DEFAULT 0 COMMENT '抖音',
    pay_meituan DECIMAL(12,2) DEFAULT 0 COMMENT '美团/团购',
    extra_payments JSON COMMENT '其他支付方式(JSON)',
    extra_info JSON COMMENT '其他扩展信息(JSON)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预订汇总事实表';

CREATE INDEX idx_batch ON fact_booking (batch_id);
CREATE INDEX idx_date_store ON fact_booking (biz_date, store_id);
CREATE INDEX idx_date_store_employee ON fact_booking (biz_date, store_id, employee_id);
CREATE INDEX idx_employee ON fact_booking (employee_id);
CREATE INDEX ix_fact_booking_batch_id ON fact_booking (batch_id);

-- 包厢开台事实表
CREATE TABLE IF NOT EXISTS fact_room (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    batch_id BIGINT NOT NULL COMMENT '关联批次',
    biz_date DATE NOT NULL COMMENT '营业日期',
    store_id INT NOT NULL COMMENT '关联门店',
    room_id INT COMMENT '关联包厢',
    order_no VARCHAR(50) NOT NULL UNIQUE COMMENT '开台单号(业务主键)',
    billing_mode VARCHAR(100) COMMENT '开房计费模式',
    open_time DATETIME COMMENT '开房时间',
    close_time DATETIME COMMENT '关房时间',
    clean_time DATETIME COMMENT '清洁时间',
    duration_min INT DEFAULT 0 COMMENT '时长(分钟)',
    time_slot VARCHAR(20) COMMENT '时段',
    booker VARCHAR(50) COMMENT '订房人',
    booker_dept VARCHAR(50) COMMENT '订房人部门',
    sales_manager VARCHAR(50) COMMENT '销售经理',
    bill_total DECIMAL(12,2) DEFAULT 0 COMMENT '账单合计',
    receivable_amount DECIMAL(12,2) DEFAULT 0 COMMENT '应收金额',
    actual_amount DECIMAL(12,2) DEFAULT 0 COMMENT '实收金额',
    base_performance DECIMAL(12,2) DEFAULT 0 COMMENT '基本业绩',
    min_consumption DECIMAL(12,2) DEFAULT 0 COMMENT '低消费',
    min_consumption_diff DECIMAL(12,2) DEFAULT 0 COMMENT '低消差额',
    gift_amount DECIMAL(12,2) DEFAULT 0 COMMENT '赠送金额',
    room_discount DECIMAL(12,2) DEFAULT 0 COMMENT '房费折扣',
    beverage_discount DECIMAL(12,2) DEFAULT 0 COMMENT '酒水折扣',
    free_amount DECIMAL(12,2) DEFAULT 0 COMMENT '免单金额',
    credit_amount DECIMAL(12,2) DEFAULT 0 COMMENT '挂账金额',
    round_off_amount DECIMAL(12,2) DEFAULT 0 COMMENT '抹零金额',
    adjustment_amount DECIMAL(12,2) DEFAULT 0 COMMENT '调整金额',
    pay_wechat DECIMAL(12,2) DEFAULT 0 COMMENT '微信支付',
    pay_alipay DECIMAL(12,2) DEFAULT 0 COMMENT '支付宝',
    pay_cash DECIMAL(12,2) DEFAULT 0 COMMENT '现金',
    pay_pos DECIMAL(12,2) DEFAULT 0 COMMENT 'POS/银行卡',
    pay_member DECIMAL(12,2) DEFAULT 0 COMMENT '会员支付',
    pay_douyin DECIMAL(12,2) DEFAULT 0 COMMENT '抖音',
    pay_meituan DECIMAL(12,2) DEFAULT 0 COMMENT '美团/团购',
    extra_payments JSON COMMENT '其他支付方式(JSON)',
    extra_info JSON COMMENT '其他扩展信息(JSON)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='包厢开台事实表';

CREATE INDEX idx_batch ON fact_room (batch_id);
CREATE INDEX idx_date_store ON fact_room (biz_date, store_id);
CREATE INDEX idx_date_store_room ON fact_room (biz_date, store_id, room_id);
CREATE UNIQUE INDEX idx_order_no ON fact_room (order_no);
CREATE INDEX idx_room ON fact_room (room_id);
CREATE INDEX ix_fact_room_batch_id ON fact_room (batch_id);

-- 酒水销售事实表
CREATE TABLE IF NOT EXISTS fact_sales (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    batch_id BIGINT NOT NULL COMMENT '关联批次',
    biz_date DATE NOT NULL COMMENT '营业日期',
    store_id INT NOT NULL COMMENT '关联门店',
    product_id INT COMMENT '关联商品',
    product_name VARCHAR(100) COMMENT '商品名称',
    category_name VARCHAR(50) COMMENT '类别名称',
    unit VARCHAR(20) COMMENT '单位',
    area VARCHAR(50) COMMENT '区域',
    sales_qty INT DEFAULT 0 COMMENT '销售数量',
    sales_amount DECIMAL(12,2) DEFAULT 0 COMMENT '销售金额',
    sales_qty_pure INT DEFAULT 0 COMMENT '纯销售数量',
    sales_qty_package INT DEFAULT 0 COMMENT '套餐子物品数量',
    sales_qty_example INT DEFAULT 0 COMMENT '例送子物品数量',
    sales_amount_pure DECIMAL(12,2) DEFAULT 0 COMMENT '纯销售金额',
    sales_amount_package DECIMAL(12,2) DEFAULT 0 COMMENT '套餐子物品金额',
    gift_qty INT DEFAULT 0 COMMENT '赠送数量',
    gift_amount DECIMAL(12,2) DEFAULT 0 COMMENT '赠送金额',
    gift_qty_pure INT DEFAULT 0 COMMENT '纯赠送数量',
    gift_qty_package INT DEFAULT 0 COMMENT '套餐赠送数量',
    cost_total DECIMAL(12,2) DEFAULT 0 COMMENT '成本小计',
    cost_sales DECIMAL(12,2) DEFAULT 0 COMMENT '销售成本',
    cost_gift DECIMAL(12,2) DEFAULT 0 COMMENT '赠送成本',
    profit DECIMAL(12,2) DEFAULT 0 COMMENT '毛利',
    profit_rate DECIMAL(8,2) DEFAULT 0 COMMENT '毛利率(%)',
    extra_info JSON COMMENT '其他扩展信息(JSON)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='酒水销售事实表';

CREATE INDEX idx_batch ON fact_sales (batch_id);
CREATE INDEX idx_category ON fact_sales (category_name);
CREATE INDEX idx_date_store ON fact_sales (biz_date, store_id);
CREATE INDEX idx_date_store_product ON fact_sales (biz_date, store_id, product_id);
CREATE INDEX idx_product ON fact_sales (product_id);
CREATE INDEX ix_fact_sales_batch_id ON fact_sales (batch_id);

-- ========================================
-- 元数据表 (Meta Tables)
-- ========================================

-- 文件导入批次管理表
CREATE TABLE IF NOT EXISTS meta_file_batch (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    batch_no VARCHAR(50) NOT NULL UNIQUE COMMENT '唯一批次号 (YYYYMMDD_Store_Type)',
    file_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_path VARCHAR(500) COMMENT '文件存储路径',
    file_hash VARCHAR(64) COMMENT '文件MD5哈希(防重复)',
    store_id INT NOT NULL COMMENT '关联门店ID',
    table_type VARCHAR(50) NOT NULL COMMENT '表类型: booking/room/sales',
    data_start_date DATETIME COMMENT '数据开始日期',
    data_end_date DATETIME COMMENT '数据结束日期',
    status VARCHAR(20) COMMENT '状态: pending/processing/success/failed',
    row_count INT DEFAULT 0 COMMENT '导入行数',
    error_count INT DEFAULT 0 COMMENT '错误行数',
    error_log TEXT COMMENT '错误日志(JSON格式)',
    upload_user VARCHAR(50) COMMENT '上传人',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件导入批次管理表';

CREATE UNIQUE INDEX idx_batch_no ON meta_file_batch (batch_no);
CREATE INDEX idx_file_hash ON meta_file_batch (file_hash);
CREATE INDEX idx_status ON meta_file_batch (status);
CREATE INDEX idx_store_date ON meta_file_batch (store_id, created_at);
CREATE INDEX ix_meta_file_batch_store_id ON meta_file_batch (store_id);

-- 完成
SELECT '数据库初始化完成！完整的维度建模表结构已创建。' AS message;

