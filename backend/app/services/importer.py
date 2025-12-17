"""
数据入库服务

基础骨架：批次创建、数据入库、维度处理
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Tuple

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.meta import MetaFileBatch
from app.models.facts import FactBooking, FactRoom, FactSales
from app.models.dims import DimEmployee, DimProduct, DimRoom, DimStore, DimPaymentMethod


class DuplicateFileError(Exception):
    """上传文件与历史批次重复"""

    def __init__(self, batch: Optional[MetaFileBatch] = None, message: Optional[str] = None):
        self.batch = batch
        final_message = message or describe_duplicate_batch(batch)
        super().__init__(final_message)


def describe_duplicate_batch(batch: Optional[MetaFileBatch]) -> str:
    """构造重复文件的人类可读提示"""
    if batch and batch.created_at:
        timestamp = batch.created_at.strftime("%Y-%m-%d %H:%M")
    else:
        timestamp = "之前"

    batch_no = batch.batch_no if batch and batch.batch_no else "未知批次"
    return f"该文件已于 {timestamp} 导入 (批次 {batch_no})，无需重复上传"


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
        # 缓存模型列集合，避免重复解析
        self._model_columns_cache: Dict[type, Set[str]] = {}

    def generate_batch_no(self, store_id: int, table_type: str) -> str:
        """生成批次号: YYYYMMDDHHMMSS_StoreID_Type"""
        date_str = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{date_str}_{store_id}_{table_type}"

    def create_batch(
        self, file_name: str, store_id: int, table_type: str
    ) -> MetaFileBatch:
        """创建批次记录"""
        batch = MetaFileBatch(
            batch_no=self.generate_batch_no(store_id, table_type),
            file_name=file_name,
            store_id=store_id,
            table_type=table_type,
            status="pending",
        )
        self.db.add(batch)
        self.db.flush()  # 获取 ID，但不提交
        return batch

    def save_batch(
        self,
        batch_id: int,
        table_type: str,
        cleaned_data: List[Dict[str, Any]],
        overwrite: bool = True,
        file_hash: Optional[str] = None,
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
                self.db.execute(delete(model).where(model.batch_id == batch_id))

            # 批量插入新数据
            model_columns = self._get_model_columns(model)
            records = []
            for row in cleaned_data:
                prepared_row = self._prepare_record(model_columns, batch_id, row)
                records.append(model(**prepared_row))

            if records:
                self.db.bulk_save_objects(records)

            # 更新批次状态
            batch = (
                self.db.query(MetaFileBatch)
                .filter(MetaFileBatch.id == batch_id)
                .first()
            )
            if batch:
                batch.status = "success"
                batch.row_count = len(records)
                if file_hash:
                    batch.file_hash = file_hash

            # 提交事务
            self.db.commit()

            return len(records)

        except IntegrityError as exc:
            self.db.rollback()
            if file_hash and self._is_file_hash_constraint(exc):
                duplicate_batch = self._find_success_batch_by_hash(file_hash)
                raise DuplicateFileError(duplicate_batch)

            self._mark_batch_failed(batch_id, exc)
            raise

        except Exception as e:
            self.db.rollback()
            self._mark_batch_failed(batch_id, e)
            raise

    def _get_model_columns(self, model) -> Set[str]:
        """获取并缓存模型列名集合"""
        if model not in self._model_columns_cache:
            self._model_columns_cache[model] = {
                column.name for column in model.__table__.columns
            }
        return self._model_columns_cache[model]

    def _ensure_payment_methods(self) -> None:
        """
        初始化标准支付方式 (如果 DimPaymentMethod 为空)
        """
        if self.db.query(DimPaymentMethod).first():
            return

        default_methods = [
            {"code": "wechat", "name": "微信支付", "category": "income", "is_core": True, "sort_order": 1},
            {"code": "alipay", "name": "支付宝", "category": "income", "is_core": True, "sort_order": 2},
            {"code": "cash", "name": "现金", "category": "income", "is_core": True, "sort_order": 3},
            {"code": "pos", "name": "POS/银行卡", "category": "income", "is_core": True, "sort_order": 4},
            {"code": "douyin", "name": "抖音", "category": "income", "is_core": True, "sort_order": 5},
            {"code": "meituan", "name": "美团/团购", "category": "income", "is_core": True, "sort_order": 6},
            {"code": "member", "name": "会员支付", "category": "equity", "is_core": True, "sort_order": 10},
        ]

        for method in default_methods:
            self.db.add(DimPaymentMethod(is_active=True, **method))
        
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            pass

    def _prepare_record(
        self,
        model_columns: Set[str],
        batch_id: int,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        过滤无效字段，并将多余字段合并到 extra_info
        """
        row_with_batch = dict(row)
        row_with_batch["batch_id"] = batch_id

        filtered_row = {
            key: value for key, value in row_with_batch.items() if key in model_columns
        }

        if "extra_info" in model_columns:
            # 提取多余字段，并进行类型清洗（处理 numpy 类型）
            extra_fields = {
                key: self._sanitize_for_json(value)
                for key, value in row_with_batch.items()
                if key not in model_columns
            }
            if extra_fields:
                # 同样需要清洗可能已存在的 extra_info
                existing_extra = self._sanitize_for_json(filtered_row.get("extra_info"))
                filtered_row["extra_info"] = self._merge_extra_info(
                    existing_extra,
                    extra_fields,
                )

        return filtered_row

    @staticmethod
    def _sanitize_for_json(obj: Any) -> Any:
        """
        递归处理 JSON 序列化不支持的类型 (如 numpy 数据类型)
        """
        if obj is None:
            return None

        # 递归处理字典
        if isinstance(obj, dict):
            return {k: ImporterService._sanitize_for_json(v) for k, v in obj.items()}

        # 递归处理列表
        if isinstance(obj, list):
            return [ImporterService._sanitize_for_json(v) for v in obj]

        # 鸭子类型：处理 numpy 标量 (int64, float64 等具有 .item() 方法)
        if hasattr(obj, "item"):
            return obj.item()

        return obj

    @staticmethod
    def _merge_extra_info(
        existing_extra: Any,
        extra_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        将已有 extra_info 与新增字段合并，兼容非 Dict 类型
        """
        if existing_extra is None:
            return extra_fields

        if isinstance(existing_extra, dict):
            merged = dict(existing_extra)
            merged.update(extra_fields)
            return merged

        # 兜底：当历史 extra_info 不是 dict 时，统一包装为 dict
        merged = {"__value": existing_extra}
        merged.update(extra_fields)
        return merged

    def delete_batch(self, batch_id: int) -> bool:
        """删除批次及其关联数据"""
        try:
            batch = (
                self.db.query(MetaFileBatch)
                .filter(MetaFileBatch.id == batch_id)
                .first()
            )

            if not batch:
                return False

            model = self.TABLE_MODEL_MAP.get(batch.table_type)
            if model:
                self.db.execute(delete(model).where(model.batch_id == batch_id))

            self.db.delete(batch)
            self.db.commit()

            return True

        except Exception:
            self.db.rollback()
            raise

    def get_or_create_dimension(self, model_class, store_id: int, **kwargs) -> int:
        """获取或创建维度记录，返回ID"""
        query = self.db.query(model_class).filter(model_class.store_id == store_id)

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

    def _get_or_create_store(self, session: Session, store_name: str) -> int:
        """
        根据门店名称获取或创建 DimStore 记录，返回 store_id。
        """
        if not store_name:
            raise ValueError("store_name 不能为空")

        normalized_name = store_name.strip()
        if not normalized_name:
            raise ValueError("store_name 不能为空白字符串")

        existing = (
            session.query(DimStore)
            .filter(DimStore.store_name == normalized_name)
            .first()
        )
        if existing:
            return existing.id

        store_code = f"STORE-{uuid.uuid4().hex[:8].upper()}"
        new_store = DimStore(
            store_name=normalized_name,
            original_name=store_name.strip(),
            store_code=store_code,
            is_active=True,
        )
        session.add(new_store)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = (
                session.query(DimStore)
                .filter(DimStore.store_name == normalized_name)
                .first()
            )
            if existing:
                return existing.id
            raise

        session.refresh(new_store)
        return new_store.id

    def _sync_payment_methods(
        self,
        session: Session,
        payment_methods: Optional[List[Dict[str, Any]]],
    ) -> None:
        """
        根据 Cleaner 提供的 payment meta，同步 DimPaymentMethod。
        """
        if not payment_methods:
            return

        for meta in payment_methods:
            code_raw = meta.get("code")
            if not code_raw:
                continue
            code = str(code_raw).strip().lower()
            if not code:
                continue

            exists = (
                session.query(DimPaymentMethod.id)
                .filter(DimPaymentMethod.code == code)
                .first()
            )
            if exists:
                continue

            name = str(meta.get("name") or code)
            category = str(meta.get("category") or "other")
            is_core = bool(meta.get("is_core", False))

            sort_order_raw = meta.get("sort_order")
            try:
                sort_order = int(sort_order_raw)
            except (TypeError, ValueError):
                sort_order = 10 if is_core else 100

            record = DimPaymentMethod(
                code=code,
                name=name,
                category=category,
                is_core=is_core,
                sort_order=sort_order,
                is_active=True,
            )
            session.add(record)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                exists = (
                    session.query(DimPaymentMethod.id)
                    .filter(DimPaymentMethod.code == code)
                    .first()
                )
                if not exists:
                    raise

    # ============== 以下为 A5 需补充的方法骨架 ==============
    def process_upload(
        self,
        file_name: str,
        store_id: Optional[int],
        table_type: str,
        cleaned_data: List[Dict[str, Any]],
        biz_date: Optional[str] = None,
        store_name: Optional[str] = None,
        payment_methods: Optional[List[Dict[str, Any]]] = None,
        file_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        处理文件上传的完整流程
        """
        batch: Optional[MetaFileBatch] = None
        sales_total = 0.0
        actual_total = 0.0
        try:
            resolved_store_id = store_id
            
            # 如果指定了 store_id，先校验是否存在
            if resolved_store_id is not None:
                existing_store = self.db.query(DimStore).filter(DimStore.id == resolved_store_id).first()
                if not existing_store:
                    # 如果不存在，但提供了 store_name，尝试通过名字查找或创建
                    if store_name:
                        # 此时忽略传入的无效 store_id，改为根据名字处理
                        resolved_store_id = self._get_or_create_store(self.db, store_name)
                    else:
                        raise ValueError(f"指定的 store_id {resolved_store_id} 不存在，且未提供 store_name")
            
            # 如果没指定 store_id，通过 store_name 获取或创建
            elif store_name:
                resolved_store_id = self._get_or_create_store(self.db, store_name)
            
            if resolved_store_id is None:
                raise ValueError("store_id 或 store_name 必须提供其一")
            
            # 0. 确保支付方式维度已初始化
            self._ensure_payment_methods()
            if payment_methods:
                self._sync_payment_methods(self.db, payment_methods)

            if file_hash:
                duplicate_batch = self._find_success_batch_by_hash(file_hash)
                if duplicate_batch:
                    raise DuplicateFileError(duplicate_batch)

            # 1. 创建批次并标记处理中
            batch = self.create_batch(file_name, resolved_store_id, table_type)
            batch.status = "processing"
            self.db.commit()

            # 1.1 如指定 biz_date，先写入每一行
            if biz_date:
                for row in cleaned_data:
                    row["biz_date"] = biz_date

            # 2. 若指定日期，删除该日期旧数据（按门店+biz_date 覆盖）
            if biz_date:
                model = self.TABLE_MODEL_MAP[table_type]
                self.db.execute(
                    delete(model).where(
                        model.store_id == resolved_store_id, model.biz_date == biz_date
                    )
                )

            # 3. 处理维度，填充外键 ID
            processed_data = self._process_dimensions(
                table_type, resolved_store_id, cleaned_data
            )

            sales_total, actual_total = self._calculate_totals(processed_data)

            # 4. 入库（不再覆盖同批次，因为 batch_id 唯一）
            row_count = self.save_batch(
                batch.id,
                table_type,
                processed_data,
                overwrite=False,
                file_hash=file_hash,
            )

            return {
                "batch_id": batch.id,
                "batch_no": batch.batch_no,
                "row_count": row_count,
                "sales_total": sales_total,
                "actual_total": actual_total,
                "status": "success",
            }

        except DuplicateFileError:
            raise

        except Exception as e:
            return {
                "batch_id": batch.id if batch else None,
                "batch_no": batch.batch_no if batch else None,
                "row_count": 0,
                "sales_total": sales_total,
                "actual_total": actual_total,
                "status": "failed",
                "error": str(e),
            }

    def _process_dimensions(
        self, table_type: str, store_id: int, data: List[Dict[str, Any]]
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
                employee_name = row.get("employee_name")
                employee_id = self.get_or_create_dimension(
                    DimEmployee,
                    store_id,
                    name=employee_name,
                    department=row.get("department"),
                )
                row_copy["employee_id"] = employee_id
                row_copy.pop("employee_name", None)

                customer_name = row_copy.get("customer_name")
                if (
                    not customer_name
                    or (isinstance(customer_name, str) and not customer_name.strip())
                ):
                    fallback_name = employee_name
                    if isinstance(fallback_name, str):
                        fallback_name = fallback_name.strip()
                    if fallback_name:
                        row_copy["customer_name"] = fallback_name

            # room: 包厢维度
            if table_type == "room" and "room_no" in row:
                room_kwargs = {
                    "room_no": row.get("room_no"),
                    "room_type": row.get("room_type"),
                    "area_name": row.get("area_name"),
                }
                room_id = self.get_or_create_dimension(
                    DimRoom,
                    store_id,
                    **{k: v for k, v in room_kwargs.items() if v is not None},
                )
                row_copy["room_id"] = room_id
                row_copy.pop("room_no", None)
                row_copy.pop("room_type", None)
                row_copy.pop("area_name", None)

            # sales: 商品维度
            if table_type == "sales" and "product_name" in row:
                category_value = row.get("category_name")
                if category_value is None:
                    category_value = row.get("category")
                product_kwargs = {
                    "name": row.get("product_name"),
                    "category": category_value,
                }
                product_id = self.get_or_create_dimension(
                    DimProduct,
                    store_id,
                    **{k: v for k, v in product_kwargs.items() if v is not None},
                )
                row_copy["product_id"] = product_id
                # 兼容字段命名差异：category -> category_name
                if "category_name" not in row_copy and "category" in row_copy:
                    row_copy["category_name"] = row_copy.pop("category")
                else:
                    row_copy.pop("category", None)

            processed.append(row_copy)

        return processed

    @staticmethod
    def _calculate_totals(data: List[Dict[str, Any]]) -> Tuple[float, float]:
        """
        累加销售金额与实收金额，缺失字段按 0 处理
        """
        sales_total = 0.0
        actual_total = 0.0

        for row in data:
            sales_total += ImporterService._to_float(row.get("sales_amount", 0))
            actual_total += ImporterService._to_float(row.get("actual_amount", 0))

        return sales_total, actual_total

    @staticmethod
    def _to_float(value: Any) -> float:
        """安全地将输入转换为 float，无法转换则返回 0"""
        if value is None:
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, Decimal):
            return float(value)

        if hasattr(value, "item"):
            try:
                return float(value.item())
            except (TypeError, ValueError):
                return 0.0

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _find_success_batch_by_hash(self, file_hash: Optional[str]) -> Optional[MetaFileBatch]:
        if not file_hash:
            return None
        return (
            self.db.query(MetaFileBatch)
            .filter(
                MetaFileBatch.file_hash == file_hash,
                MetaFileBatch.status == "success",
            )
            .order_by(MetaFileBatch.created_at.desc())
            .first()
        )

    @staticmethod
    def _is_file_hash_constraint(error: IntegrityError) -> bool:
        message = ""
        if hasattr(error, "orig") and getattr(error.orig, "args", None):
            message = " ".join(str(arg) for arg in error.orig.args)
        elif error.args:
            message = " ".join(str(arg) for arg in error.args)

        message = message.lower()
        return "file_hash" in message or "uq_meta_file_batch_file_hash" in message

    def _mark_batch_failed(self, batch_id: int, error: Exception) -> None:
        try:
            batch = (
                self.db.query(MetaFileBatch)
                .filter(MetaFileBatch.id == batch_id)
                .first()
            )
            if batch:
                batch.status = "failed"
                batch.error_log = str(error)
                self.db.commit()
        except Exception:
            self.db.rollback()
