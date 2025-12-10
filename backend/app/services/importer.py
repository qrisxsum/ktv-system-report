"""
数据入库服务

基础骨架：批次创建、数据入库、维度处理
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.models.meta import MetaFileBatch
from app.models.facts import FactBooking, FactRoom, FactSales
from app.models.dims import DimEmployee, DimProduct, DimRoom


class ImporterService:
    """数据入库服务类"""

    # 表类型映射到模型
    TABLE_MODEL_MAP = {
        "booking": FactBooking,
        "room": FactRoom,
        "sales": FactSales,
    }

    def __init__(self, db: Session):
        self.db = db

    def generate_batch_no(self, store_id: int, table_type: str) -> str:
        """生成批次号: YYYYMMDDHHMMSS_StoreID_Type"""
        date_str = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{date_str}_{store_id}_{table_type}"

    def create_batch(
        self,
        file_name: str,
        store_id: int,
        table_type: str
    ) -> MetaFileBatch:
        """创建批次记录"""
        batch = MetaFileBatch(
            batch_no=self.generate_batch_no(store_id, table_type),
            file_name=file_name,
            store_id=store_id,
            table_type=table_type,
            status="pending"
        )
        self.db.add(batch)
        self.db.flush()  # 获取 ID，但不提交
        return batch

    def save_batch(
        self,
        batch_id: int,
        table_type: str,
        cleaned_data: List[Dict[str, Any]],
        overwrite: bool = True
    ) -> int:
        """
        保存数据到事实表

        Args:
            batch_id: 批次ID
            table_type: 表类型 (booking/room/sales)
            cleaned_data: 清洗后的数据 (List[Dict])
            overwrite: 是否覆盖同批次旧数据

        Returns:
            int: 插入的行数

        Raises:
            ValueError: 表类型不支持
            Exception: 数据库错误
        """
        if table_type not in self.TABLE_MODEL_MAP:
            raise ValueError(f"不支持的表类型: {table_type}")

        model = self.TABLE_MODEL_MAP[table_type]

        try:
            # 如果需要覆盖，先删除旧数据
            if overwrite:
                self.db.execute(
                    delete(model).where(model.batch_id == batch_id)
                )

            # 批量插入新数据
            records = []
            for row in cleaned_data:
                row["batch_id"] = batch_id
                records.append(model(**row))

            if records:
                self.db.bulk_save_objects(records)

            # 更新批次状态
            batch = self.db.query(MetaFileBatch).filter(
                MetaFileBatch.id == batch_id
            ).first()
            if batch:
                batch.status = "success"
                batch.row_count = len(records)

            # 提交事务
            self.db.commit()

            return len(records)

        except Exception as e:
            # 回滚事务
            self.db.rollback()

            # 更新批次状态为失败
            try:
                batch = self.db.query(MetaFileBatch).filter(
                    MetaFileBatch.id == batch_id
                ).first()
                if batch:
                    batch.status = "failed"
                    batch.error_log = str(e)
                    self.db.commit()
            except:  # noqa: E722 - 保底不影响原始异常
                pass

            raise

    def delete_batch(self, batch_id: int) -> bool:
        """删除批次及其关联数据"""
        try:
            batch = self.db.query(MetaFileBatch).filter(
                MetaFileBatch.id == batch_id
            ).first()

            if not batch:
                return False

            model = self.TABLE_MODEL_MAP.get(batch.table_type)
            if model:
                self.db.execute(
                    delete(model).where(model.batch_id == batch_id)
                )

            self.db.delete(batch)
            self.db.commit()

            return True

        except Exception:
            self.db.rollback()
            raise

    def get_or_create_dimension(
        self,
        model_class,
        store_id: int,
        **kwargs
    ) -> int:
        """获取或创建维度记录，返回ID"""
        query = self.db.query(model_class).filter(
            model_class.store_id == store_id
        )

        for key, value in kwargs.items():
            if hasattr(model_class, key):
                query = query.filter(getattr(model_class, key) == value)

        record = query.first()
        if record:
            return record.id

        new_record = model_class(store_id=store_id, **kwargs)
        self.db.add(new_record)
        self.db.flush()
        return new_record.id

    # ============== 以下为 A5 需补充的方法骨架 ==============
    def process_upload(
        self,
        file_name: str,
        store_id: int,
        table_type: str,
        cleaned_data: List[Dict[str, Any]],
        biz_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理文件上传的完整流程
        """
        try:
            # 1. 创建批次并标记处理中
            batch = self.create_batch(file_name, store_id, table_type)
            batch.status = "processing"
            self.db.commit()

            # 2. 若指定日期，删除该日期旧数据（按门店+biz_date 覆盖）
            if biz_date:
                model = self.TABLE_MODEL_MAP[table_type]
                self.db.execute(
                    delete(model).where(
                        model.store_id == store_id,
                        model.biz_date == biz_date
                    )
                )

            # 3. 处理维度，填充外键 ID
            processed_data = self._process_dimensions(
                table_type, store_id, cleaned_data
            )

            # 4. 入库（不再覆盖同批次，因为 batch_id 唯一）
            row_count = self.save_batch(
                batch.id, table_type, processed_data, overwrite=False
            )

            return {
                "batch_id": batch.id,
                "batch_no": batch.batch_no,
                "row_count": row_count,
                "status": "success"
            }

        except Exception as e:
            return {
                "batch_id": batch.id if "batch" in locals() else None,
                "row_count": 0,
                "status": "failed",
                "error": str(e)
            }

    def _process_dimensions(
        self,
        table_type: str,
        store_id: int,
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        处理维度数据，获取或创建维度ID
        """
        processed: List[Dict[str, Any]] = []

        for row in data:
            row_copy = {k: v for k, v in row.items()}
            row_copy["store_id"] = store_id

            # booking: 员工维度
            if table_type == "booking" and "employee_name" in row:
                employee_id = self.get_or_create_dimension(
                    DimEmployee,
                    store_id,
                    name=row.get("employee_name"),
                    department=row.get("department")
                )
                row_copy["employee_id"] = employee_id
                row_copy.pop("employee_name", None)

            # room: 包厢维度
            if table_type == "room" and "room_no" in row:
                room_id = self.get_or_create_dimension(
                    DimRoom,
                    store_id,
                    room_no=row.get("room_no"),
                    room_type=row.get("room_type")
                )
                row_copy["room_id"] = room_id
                row_copy.pop("room_no", None)
                row_copy.pop("room_type", None)

            # sales: 商品维度
            if table_type == "sales" and "product_name" in row:
                product_id = self.get_or_create_dimension(
                    DimProduct,
                    store_id,
                    name=row.get("product_name"),
                    category=row.get("category")
                )
                row_copy["product_id"] = product_id
                row_copy.pop("product_name", None)
                # 兼容字段命名差异：category -> category_name
                if "category_name" not in row_copy and "category" in row_copy:
                    row_copy["category_name"] = row_copy.pop("category")

            processed.append(row_copy)

        return processed

