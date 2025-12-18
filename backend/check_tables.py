#!/usr/bin/env python3
"""
检查数据库表
"""
from app.core.database import engine, Base
from sqlalchemy import inspect

# 创建检查器
inspector = inspect(engine)

# 获取所有表名
tables = inspector.get_table_names()
print("数据库中的表:")
for table in sorted(tables):
    print(f"  - {table}")

# 检查是否有users表
if 'users' in tables:
    print("\n✅ users表存在")
else:
    print("\n❌ users表不存在")

# 检查users表的结构（如果存在）
if 'users' in tables:
    columns = inspector.get_columns('users')
    print("\nusers表结构:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
