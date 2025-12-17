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
-- IMPORTANT (dev/prod):
-- 本项目使用 Alembic 管理表结构。
-- 这里仅创建数据库，不再预创建任何业务表，避免与 Alembic 初始迁移冲突。
-- 初始化完成后请执行：
--   docker compose exec backend alembic upgrade head
-- ========================================

SELECT '数据库初始化完成！请运行 Alembic 迁移创建表结构。' AS message;

