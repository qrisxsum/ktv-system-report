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
-- 1. 系统管理表
-- ========================================

-- 门店表
CREATE TABLE IF NOT EXISTS sys_store (
    id INT PRIMARY KEY AUTO_INCREMENT,
    store_code VARCHAR(20) NOT NULL UNIQUE COMMENT '门店编码',
    store_name VARCHAR(100) NOT NULL COMMENT '门店名称',
    region VARCHAR(50) COMMENT '所属区域/城市',
    address VARCHAR(200) COMMENT '门店地址',
    status TINYINT DEFAULT 1 COMMENT '状态: 1-启用, 0-停用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='门店信息表';

-- 上传日志表
CREATE TABLE IF NOT EXISTS sys_upload_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    store_id INT NOT NULL COMMENT '门店ID',
    file_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_type ENUM('room_analysis', 'beverage_sales', 'booking_summary') NOT NULL COMMENT '文件类型',
    file_hash VARCHAR(64) NOT NULL COMMENT '文件MD5哈希(防重复)',
    data_start_date DATE NOT NULL COMMENT '数据开始日期',
    data_end_date DATE NOT NULL COMMENT '数据结束日期',
    data_month VARCHAR(7) NOT NULL COMMENT '数据所属月份(YYYY-MM)',
    row_count INT NOT NULL COMMENT '数据行数',
    upload_user VARCHAR(50) NOT NULL COMMENT '上传人',
    upload_status ENUM('pending', 'processing', 'success', 'failed') DEFAULT 'pending' COMMENT '上传状态',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_store_month (store_id, data_month),
    INDEX idx_file_hash (file_hash),
    INDEX idx_status (upload_status),
    FOREIGN KEY (store_id) REFERENCES sys_store(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件上传日志表';

-- ========================================
-- 2. 业务事实表
-- ========================================

-- 包厢开台分析表
CREATE TABLE IF NOT EXISTS fact_room_analysis (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    upload_log_id BIGINT NOT NULL COMMENT '关联上传日志',
    store_id INT NOT NULL COMMENT '门店ID',
    
    -- 包厢信息
    room_name VARCHAR(20) NOT NULL COMMENT '包厢名称',
    room_type VARCHAR(20) NOT NULL COMMENT '包厢类型',
    area_name VARCHAR(20) COMMENT '区域名称',
    
    -- 订单信息
    order_no VARCHAR(30) NOT NULL COMMENT '开台单号',
    billing_mode VARCHAR(100) COMMENT '开房计费模式',
    
    -- 时间信息
    open_time DATETIME NOT NULL COMMENT '开房时间',
    close_time DATETIME COMMENT '关房时间',
    clean_time DATETIME COMMENT '清洁时间',
    business_date DATE NOT NULL COMMENT '营业日',
    
    -- 人员信息
    booker VARCHAR(50) COMMENT '订房人',
    booker_dept VARCHAR(50) COMMENT '订房人部门',
    returner VARCHAR(50) COMMENT '返房人',
    rotator VARCHAR(50) COMMENT '轮房人',
    
    -- 消费信息
    duration_minutes INT COMMENT '消费时长(分钟)',
    time_slot VARCHAR(20) COMMENT '时段',
    open_tag VARCHAR(50) COMMENT '开房标签',
    booking_channel VARCHAR(50) COMMENT '预订渠道',
    bill_remark VARCHAR(200) COMMENT '账单备注',
    
    -- 金额信息
    total_amount DECIMAL(12,2) DEFAULT 0 COMMENT '账单合计',
    receivable_amount DECIMAL(12,2) DEFAULT 0 COMMENT '应收金额',
    received_amount DECIMAL(12,2) DEFAULT 0 COMMENT '实收金额',
    gift_amount DECIMAL(12,2) DEFAULT 0 COMMENT '赠送金额',
    round_off_amount DECIMAL(12,2) DEFAULT 0 COMMENT '抹零金额',
    adjust_amount DECIMAL(12,2) DEFAULT 0 COMMENT '调整金额',
    pending_amount DECIMAL(12,2) DEFAULT 0 COMMENT '挂账金额',
    free_amount DECIMAL(12,2) DEFAULT 0 COMMENT '免单金额',
    room_discount DECIMAL(12,2) DEFAULT 0 COMMENT '房费折扣金额',
    beverage_discount DECIMAL(12,2) DEFAULT 0 COMMENT '酒水折扣金额',
    
    -- 业绩信息
    base_performance DECIMAL(12,2) DEFAULT 0 COMMENT '基本业绩',
    min_consumption DECIMAL(12,2) DEFAULT 0 COMMENT '低消费',
    min_consumption_diff DECIMAL(12,2) DEFAULT 0 COMMENT '低消差额',
    counted_min_amount DECIMAL(12,2) DEFAULT 0 COMMENT '计入低消金额',
    uncounted_min_amount DECIMAL(12,2) DEFAULT 0 COMMENT '不计入低消金额',
    special_drink_amount DECIMAL(12,2) DEFAULT 0 COMMENT '特饮金额',
    
    -- 人员提成
    sales_manager VARCHAR(50) COMMENT '销售经理',
    marketing_manager VARCHAR(50) COMMENT '营销经理',
    
    -- 支付方式明细 (JSON存储)
    payment_details JSON COMMENT '支付方式明细',
    
    -- 计算字段
    row_hash VARCHAR(64) COMMENT '行哈希(去重)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_store_date (store_id, business_date),
    INDEX idx_room (room_name, room_type),
    INDEX idx_order (order_no),
    INDEX idx_row_hash (row_hash),
    FOREIGN KEY (upload_log_id) REFERENCES sys_upload_log(id),
    FOREIGN KEY (store_id) REFERENCES sys_store(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='包厢开台分析事实表';

-- 酒水销售分析表
CREATE TABLE IF NOT EXISTS fact_beverage_sales (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    upload_log_id BIGINT NOT NULL COMMENT '关联上传日志',
    store_id INT NOT NULL COMMENT '门店ID',
    data_month VARCHAR(7) NOT NULL COMMENT '数据月份',
    
    -- 商品信息
    product_name VARCHAR(100) NOT NULL COMMENT '酒水名称',
    category_name VARCHAR(50) NOT NULL COMMENT '类别名称',
    unit VARCHAR(10) COMMENT '单位',
    area VARCHAR(20) COMMENT '区域',
    
    -- 成本信息
    cost_total DECIMAL(12,4) DEFAULT 0 COMMENT '成本-小计',
    cost_sales DECIMAL(12,4) DEFAULT 0 COMMENT '成本-销售',
    cost_gift DECIMAL(12,4) DEFAULT 0 COMMENT '成本-赠送',
    
    -- 利润信息
    profit DECIMAL(12,4) DEFAULT 0 COMMENT '利润',
    profit_rate DECIMAL(8,2) DEFAULT 0 COMMENT '利润率(%)',
    
    -- 合计
    total_qty INT DEFAULT 0 COMMENT '合计-数量',
    total_amount DECIMAL(12,4) DEFAULT 0 COMMENT '合计-金额',
    
    -- 销售数量
    sales_qty_subtotal INT DEFAULT 0 COMMENT '销售数量-小计',
    sales_qty_pure INT DEFAULT 0 COMMENT '销售数量-销售',
    sales_qty_package INT DEFAULT 0 COMMENT '销售数量-套餐子物品',
    sales_qty_example INT DEFAULT 0 COMMENT '销售数量-例送子物品',
    
    -- 销售金额
    sales_amount_subtotal DECIMAL(12,4) DEFAULT 0 COMMENT '销售金额-小计',
    sales_amount_pure DECIMAL(12,4) DEFAULT 0 COMMENT '销售金额-销售',
    sales_amount_package DECIMAL(12,4) DEFAULT 0 COMMENT '销售金额-套餐子物品',
    sales_amount_example DECIMAL(12,4) DEFAULT 0 COMMENT '销售金额-例送子物品',
    
    -- 赠送数量
    gift_qty_subtotal INT DEFAULT 0 COMMENT '赠送数量-小计',
    gift_qty_pure INT DEFAULT 0 COMMENT '赠送数量-赠送',
    gift_qty_package INT DEFAULT 0 COMMENT '赠送数量-套餐子物品',
    
    -- 赠送金额
    gift_amount_subtotal DECIMAL(12,4) DEFAULT 0 COMMENT '赠送金额-小计',
    gift_amount_pure DECIMAL(12,4) DEFAULT 0 COMMENT '赠送金额-赠送',
    gift_amount_package DECIMAL(12,4) DEFAULT 0 COMMENT '赠送金额-套餐子物品',
    
    -- 计算字段
    row_hash VARCHAR(64) COMMENT '行哈希(去重)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_store_month (store_id, data_month),
    INDEX idx_category (category_name),
    INDEX idx_product (product_name),
    INDEX idx_row_hash (row_hash),
    FOREIGN KEY (upload_log_id) REFERENCES sys_upload_log(id),
    FOREIGN KEY (store_id) REFERENCES sys_store(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='酒水销售分析事实表';

-- 人员绩效表
CREATE TABLE IF NOT EXISTS fact_staff_kpi (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    upload_log_id BIGINT NOT NULL COMMENT '关联上传日志',
    store_id INT NOT NULL COMMENT '门店ID',
    data_month VARCHAR(7) NOT NULL COMMENT '数据月份',
    
    -- 人员信息
    department VARCHAR(20) NOT NULL COMMENT '部门/角色',
    staff_name VARCHAR(50) NOT NULL COMMENT '订位人姓名',
    
    -- 业绩信息
    booking_count INT DEFAULT 0 COMMENT '订台数',
    sales_amount DECIMAL(12,2) DEFAULT 0 COMMENT '销售金额',
    service_fee DECIMAL(12,2) DEFAULT 0 COMMENT '服务费',
    auto_deduction DECIMAL(12,2) DEFAULT 0 COMMENT '自动扣减',
    base_performance DECIMAL(12,2) DEFAULT 0 COMMENT '基本业绩',
    free_amount DECIMAL(12,2) DEFAULT 0 COMMENT '免单金额',
    pending_amount DECIMAL(12,2) DEFAULT 0 COMMENT '挂账金额',
    adjust_amount DECIMAL(12,2) DEFAULT 0 COMMENT '调整金额',
    discount_amount DECIMAL(12,2) DEFAULT 0 COMMENT '折扣金额',
    round_off_amount DECIMAL(12,2) DEFAULT 0 COMMENT '抹零金额',
    gift_amount DECIMAL(12,2) DEFAULT 0 COMMENT '赠送金额',
    receivable_amount DECIMAL(12,2) DEFAULT 0 COMMENT '应收金额',
    received_amount DECIMAL(12,2) DEFAULT 0 COMMENT '实收金额',
    
    -- 支付方式明细 (JSON存储)
    payment_details JSON COMMENT '支付方式明细',
    
    -- 酒水类别金额
    beverage_category_amount DECIMAL(12,2) DEFAULT 0 COMMENT '酒水类别金额-小计',
    
    -- 计算字段
    row_hash VARCHAR(64) COMMENT '行哈希(去重)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_store_month (store_id, data_month),
    INDEX idx_staff (staff_name, department),
    INDEX idx_row_hash (row_hash),
    FOREIGN KEY (upload_log_id) REFERENCES sys_upload_log(id),
    FOREIGN KEY (store_id) REFERENCES sys_store(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人员绩效事实表';

-- ========================================
-- 3. 初始化数据
-- ========================================

-- 插入门店数据
INSERT INTO sys_store (store_code, store_name, region, address, status) VALUES
('WXC', '空境·派对KTV（万象城店）', '南宁', '南宁市青秀区万象城', 1),
('QNL', '空境·派对KTV（青年路店）', '南宁', '南宁市青秀区青年路', 1)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- 完成
SELECT '数据库初始化完成！' AS message;

