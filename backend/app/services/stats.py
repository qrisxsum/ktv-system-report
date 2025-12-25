"""
统计聚合服务

根据表类型、时间范围、维度和粒度进行实时聚合
"""

from datetime import date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import func, select, case
from sqlalchemy.orm import Session

from app.models.facts import FactBooking, FactRoom, FactSales, FactMemberChange
from app.models.dims import DimStore, DimEmployee, DimProduct, DimRoom


class StatsService:
    """统计聚合服务"""

    GRANULARITY_ORDER = ["day", "week", "month"]
    MAX_SERIES_POINTS = 400
    MAX_DAY_SPAN = 365
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 200
    DEFAULT_TOP_N = 50
    MAX_TOP_N = 200

    TABLE_MAP = {
        "booking": FactBooking,
        "room": FactRoom,
        "sales": FactSales,
        "member_change": FactMemberChange,
    }

    @staticmethod
    def _safe_sum(expr):
        """统一为 SUM 结果提供 0 兜底，避免返回 NULL"""
        return func.coalesce(func.sum(expr), 0)

    def __init__(self, db: Session):
        self.db = db

    def _get_dimension_expr(self, model, dimension: str, granularity: str):
        """根据维度和粒度返回分组表达式和标签"""
        if dimension == "date":
            col = model.biz_date
            if granularity == "month":
                expr = func.date_format(col, "%Y-%m")
            elif granularity == "week":
                expr = func.date_format(col, "%Y-%u")
            else:
                expr = col
            return expr.label("dimension_key")
        elif dimension == "store":
            return model.store_id.label("dimension_key")
        elif dimension == "employee":
            if hasattr(model, "employee_id"):
                return model.employee_id.label("dimension_key")
        elif dimension == "product":
            if hasattr(model, "product_id"):
                return model.product_id.label("dimension_key")
        elif dimension == "category":
            if model is FactSales:
                return DimProduct.category.label("dimension_key")
        elif dimension == "room":
            if hasattr(model, "room_id"):
                return model.room_id.label("dimension_key")
        elif dimension == "room_type":
            if model is FactRoom:
                return DimRoom.room_type.label("dimension_key")
        raise ValueError(f"不支持的维度: {dimension}  或该表缺少对应字段")

    @staticmethod
    def _normalize_payment_amount(value: Any) -> float:
        """将任意数值类型归一为 float"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _merge_payment_payload(
        self,
        target: Dict[str, float],
        payload: Optional[Dict[str, Any]],
        only_prefixed: bool,
    ):
        """将 payload 中的支付金额累加到 target"""
        if not isinstance(payload, dict):
            return
        for key, raw_value in payload.items():
            if not isinstance(key, str):
                continue
            if only_prefixed and not key.startswith("pay_"):
                continue
            normalized_key = key if key.startswith("pay_") else f"pay_{key}"
            amount = self._normalize_payment_amount(raw_value)
            if amount == 0:
                continue
            target[normalized_key] = target.get(normalized_key, 0.0) + amount

    def _aggregate_extra_payments(
        self,
        model,
        dimension: str,
        granularity: str,
        start_date: date,
        end_date: date,
        store_id: Optional[int],
    ) -> Dict[Any, Dict[str, float]]:
        """
        聚合 extra_payments / extra_info 中的动态支付方式
        """
        if not hasattr(model, "extra_payments"):
            return {}

        dim_expr = self._get_dimension_expr(model, dimension, granularity)
        query = self.db.query(
            dim_expr.label("dimension_key"),
            model.extra_payments,
            model.extra_info,
        ).filter(model.biz_date.between(start_date, end_date))
        if store_id is not None:
            query = query.filter(model.store_id == store_id)

        aggregates: Dict[Any, Dict[str, float]] = {}
        for dimension_key, extra_payments, extra_info in query:
            bucket = aggregates.setdefault(dimension_key, {})
            self._merge_payment_payload(bucket, extra_payments, only_prefixed=False)
            self._merge_payment_payload(bucket, extra_info, only_prefixed=True)

        return aggregates

    @staticmethod
    def _inject_extra_payments(
        records: List[Dict[str, Any]], aggregates: Dict[Any, Dict[str, float]]
    ):
        """将聚合好的支付方式注入结果行"""
        if not records or not aggregates:
            return
        for record in records:
            key = record.get("dimension_key")
            if key not in aggregates:
                continue
            combined = dict(record.get("extra_payments") or {})
            for pay_key, amount in aggregates[key].items():
                combined[pay_key] = combined.get(pay_key, 0.0) + amount
            record["extra_payments"] = combined

    def _get_metrics_exprs(self, model) -> List[Tuple[str, Any]]:
        """根据表类型生成常用指标表达式"""
        if model is FactBooking:
            return [
                ("sales_amount", self._safe_sum(model.sales_amount)),
                ("actual", self._safe_sum(model.actual_amount)),
                ("performance", self._safe_sum(model.base_performance)),
                ("gift_amount", self._safe_sum(model.gift_amount)),
                ("discount_amount", self._safe_sum(model.discount_amount)),
                ("credit_amount", self._safe_sum(model.credit_amount)),
                ("free_amount", self._safe_sum(model.free_amount)),
                ("round_off_amount", self._safe_sum(model.round_off_amount)),
                ("service_fee", self._safe_sum(model.service_fee)),
                ("adjustment_amount", self._safe_sum(model.adjustment_amount)),
                ("pay_wechat", self._safe_sum(model.pay_wechat)),
                ("pay_alipay", self._safe_sum(model.pay_alipay)),
                ("pay_cash", self._safe_sum(model.pay_cash)),
                ("pay_pos", self._safe_sum(model.pay_pos)),
                ("pay_member", self._safe_sum(model.pay_member)),
                ("pay_douyin", self._safe_sum(model.pay_douyin)),
                ("pay_meituan", self._safe_sum(model.pay_meituan)),
                ("pay_scan", self._safe_sum(model.pay_scan)),
                ("pay_deposit", self._safe_sum(model.pay_deposit)),
                ("orders", self._safe_sum(model.booking_qty)),
            ]
        if model is FactRoom:
            return [
                ("gmv", self._safe_sum(model.receivable_amount)),
                ("actual", self._safe_sum(model.actual_amount)),
                ("gift_amount", self._safe_sum(model.gift_amount)),
                ("room_discount", self._safe_sum(model.room_discount)),
                ("beverage_discount", self._safe_sum(model.beverage_discount)),
                ("duration", self._safe_sum(model.duration_min)),
                ("orders", func.count(model.id)),
            ]
        if model is FactSales:
            return [
                ("sales_qty", func.sum(model.sales_qty)),
                ("sales_amount", func.sum(model.sales_amount)),
                ("gift_qty", func.sum(model.gift_qty)),
                ("gift_amount", func.sum(model.gift_amount)),
                ("cost_total", func.sum(model.cost_total)),
                ("cost", func.sum(model.cost_total)),
                ("profit", func.sum(model.profit)),
                ("profit_rate", func.avg(model.profit_rate)),  # 利润率取平均值
            ]
        if model is FactMemberChange:
            return [
                ("recharge_real_income", self._safe_sum(model.recharge_real_income)),
                ("room_amount_principal", self._safe_sum(model.room_amount_principal)),
                (
                    "drink_amount_principal",
                    self._safe_sum(model.drink_amount_principal),
                ),
                ("room_amount_gift", self._safe_sum(model.room_amount_gift)),
                ("drink_amount_gift", self._safe_sum(model.drink_amount_gift)),
                ("balance_total", self._safe_sum(model.balance_total)),
                ("points_delta", self._safe_sum(model.points_delta)),
                ("growth_delta", self._safe_sum(model.growth_delta)),
                # 使用 CASE WHEN 替代 FILTER，兼容 MySQL
                (
                    "recharge_count",
                    func.sum(case((model.change_type.like("%充值%"), 1), else_=0)),
                ),
            ]
        raise ValueError("未知表类型")

    def _validate_pagination(self, page: int, page_size: int):
        if page < 1:
            raise ValueError("page 必须 >= 1")
        if page_size < 1:
            raise ValueError("page_size 必须 >= 1")
        if page_size > self.MAX_PAGE_SIZE:
            raise ValueError(f"page_size 不能超过 {self.MAX_PAGE_SIZE}")

    def _clamp_top_n(self, top_n: int) -> int:
        if top_n < 1:
            raise ValueError("top_n 必须 >= 1")
        return min(top_n, self.MAX_TOP_N)

    def _get_dimension_join_config(self, model, dimension: str):
        if dimension == "store":
            return (
                DimStore,
                model.store_id == DimStore.id,
                DimStore.store_name.label("dimension_label"),
                [],
            )
        if dimension == "employee" and hasattr(model, "employee_id"):
            return (
                DimEmployee,
                model.employee_id == DimEmployee.id,
                DimEmployee.name.label("dimension_label"),
                [],
            )
        if dimension == "product" and hasattr(model, "product_id"):
            extra_columns = [DimProduct.category.label("dimension_category")]
            return (
                DimProduct,
                model.product_id == DimProduct.id,
                DimProduct.name.label("dimension_label"),
                extra_columns,
            )
        if dimension == "category" and hasattr(model, "product_id"):
            return (
                DimProduct,
                model.product_id == DimProduct.id,
                DimProduct.category.label("dimension_label"),
                [],
            )
        if dimension == "room" and hasattr(model, "room_id"):
            return (
                DimRoom,
                model.room_id == DimRoom.id,
                DimRoom.room_no.label("dimension_label"),
                [],
            )
        if dimension == "room_type":
            if model is not FactRoom:
                raise ValueError("room_type 仅支持 room 表")
            return (
                DimRoom,
                model.room_id == DimRoom.id,
                DimRoom.room_type.label("dimension_label"),
                [],
            )
        return (None, None, None, [])

    def _build_group_stmt(
        self,
        model,
        dimension: str,
        granularity: str,
        metrics: List[Tuple[str, Any]],
        start_date: date,
        end_date: date,
        store_id: Optional[int],
    ):
        dim_expr = self._get_dimension_expr(model, dimension, granularity)
        metric_columns: Dict[str, Any] = {}
        select_columns = [dim_expr]
        for name, expr in metrics:
            labeled = expr.label(name)
            metric_columns[name] = labeled
            select_columns.append(labeled)

        (
            join_model,
            join_condition,
            dim_label_expr,
            extra_columns,
        ) = self._get_dimension_join_config(model, dimension)
        if dim_label_expr is not None:
            select_columns.append(dim_label_expr)
        extra_column_names: List[str] = []
        for extra_col in extra_columns:
            select_columns.append(extra_col)
            extra_column_names.append(extra_col.key)

        stmt = select(*select_columns)
        if join_model is not None:
            stmt = stmt.join(join_model, join_condition)
        stmt = stmt.where(model.biz_date.between(start_date, end_date))
        if store_id is not None:
            stmt = stmt.where(model.store_id == store_id)
        stmt = stmt.group_by(dim_expr)
        if dim_label_expr is not None:
            stmt = stmt.group_by(dim_label_expr)
        for extra_col in extra_columns:
            stmt = stmt.group_by(extra_col)
        stmt = stmt.order_by(dim_expr)
        return (
            stmt,
            dim_expr,
            dim_label_expr is not None,
            metric_columns,
            extra_column_names,
        )

    def _count_group_rows(self, stmt):
        subquery = stmt.order_by(None).subquery()
        return self.db.execute(select(func.count()).select_from(subquery)).scalar() or 0

    def _fetch_rows(
        self,
        stmt,
        metrics: List[Tuple[str, Any]],
        has_label: bool,
        extra_column_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        rows = self.db.execute(stmt).all()
        result: List[Dict[str, Any]] = []
        extra_column_names = extra_column_names or []
        for row in rows:
            mapping = row._mapping
            record = {"dimension_key": mapping["dimension_key"]}
            for name, _ in metrics:
                record[name] = mapping.get(name)
            if has_label and "dimension_label" in mapping:
                record["dimension_label"] = mapping["dimension_label"]
            else:
                record["dimension_label"] = str(mapping["dimension_key"])
            for extra_name in extra_column_names:
                if extra_name in mapping:
                    record[extra_name] = mapping.get(extra_name)
            result.append(record)
        return result

    def _estimate_bucket_count(
        self, start_date: date, end_date: date, granularity: str
    ) -> int:
        days = (end_date - start_date).days + 1
        if granularity == "day":
            return max(days, 0)
        if granularity == "week":
            return max((days + 6) // 7, 0)
        if granularity == "month":
            return (
                (end_date.year - start_date.year) * 12
                + (end_date.month - start_date.month)
                + 1
            )
        return days

    def _next_granularity(self, granularity: str) -> Optional[str]:
        try:
            idx = self.GRANULARITY_ORDER.index(granularity)
        except ValueError:
            return None
        if idx + 1 >= len(self.GRANULARITY_ORDER):
            return None
        return self.GRANULARITY_ORDER[idx + 1]

    def _determine_primary_metric(self, metric_columns: Dict[str, Any]) -> str:
        preferred = ["sales_amount", "actual", "gmv", "profit", "orders"]
        for name in preferred:
            if name in metric_columns:
                return name
        return next(iter(metric_columns.keys()))

    def query_stats(
        self,
        table: str,
        start_date: date,
        end_date: date,
        store_id: Optional[int] = None,
        dimension: str = "date",
        granularity: str = "day",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        top_n: int = DEFAULT_TOP_N,
    ) -> Dict[str, Any]:
        """
        通用聚合查询
        """
        if table not in self.TABLE_MAP:
            raise ValueError(f"不支持的表类型: {table}")

        model = self.TABLE_MAP[table]
        if granularity not in self.GRANULARITY_ORDER:
            raise ValueError(f"不支持的粒度: {granularity}")

        self._validate_pagination(page, page_size)
        top_n = self._clamp_top_n(top_n)

        metrics = self._get_metrics_exprs(model)

        rows_stmt, _, has_label_rows, _, extra_column_names = self._build_group_stmt(
            model=model,
            dimension=dimension,
            granularity=granularity,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
        )

        total = self._count_group_rows(rows_stmt)
        offset = (page - 1) * page_size
        paginated_stmt = rows_stmt.offset(offset).limit(page_size)
        rows = self._fetch_rows(
            paginated_stmt, metrics, has_label_rows, extra_column_names
        )

        series_granularity = granularity
        auto_adjusted = False
        is_truncated = False
        suggestions: List[str] = []

        if dimension == "date":
            bucket_count = self._estimate_bucket_count(
                start_date, end_date, series_granularity
            )
            while bucket_count > self.MAX_SERIES_POINTS:
                next_gran = self._next_granularity(series_granularity)
                if not next_gran:
                    raise ValueError("时间跨度过大，请提升粒度或缩小时间范围")
                series_granularity = next_gran
                bucket_count = self._estimate_bucket_count(
                    start_date, end_date, series_granularity
                )
                auto_adjusted = True
            if (
                granularity == "day"
                and (end_date - start_date).days + 1 > self.MAX_DAY_SPAN
                and not auto_adjusted
            ):
                raise ValueError(
                    "按日查询跨度超过 365 天，请改为按周/按月或缩小时间范围"
                )
            if auto_adjusted:
                suggestions.append(
                    f"数据点过多，已自动调整为按 {series_granularity} 聚合"
                )

            (
                series_stmt,
                _,
                has_label_series,
                _,
                extra_column_names_series,
            ) = self._build_group_stmt(
                model=model,
                dimension=dimension,
                granularity=series_granularity,
                metrics=metrics,
                start_date=start_date,
                end_date=end_date,
                store_id=store_id,
            )
            series_rows = self._fetch_rows(
                series_stmt, metrics, has_label_series, extra_column_names_series
            )
        else:
            (
                series_stmt,
                dim_expr_series,
                has_label_series,
                metric_columns,
                extra_column_names_series,
            ) = self._build_group_stmt(
                model=model,
                dimension=dimension,
                granularity=granularity,
                metrics=metrics,
                start_date=start_date,
                end_date=end_date,
                store_id=store_id,
            )
            primary_metric_name = self._determine_primary_metric(metric_columns)
            primary_metric_expr = metric_columns[primary_metric_name]
            series_stmt = series_stmt.order_by(None).order_by(
                primary_metric_expr.desc(), dim_expr_series
            )
            series_stmt = series_stmt.limit(top_n)
            series_rows = self._fetch_rows(
                series_stmt, metrics, has_label_series, extra_column_names_series
            )
            if total > len(series_rows):
                is_truncated = True
                suggestions.append(
                    f"已限制为前 {top_n} 项，建议缩小筛选范围或调大 top_n"
                )

        extra_rows_map = self._aggregate_extra_payments(
            model=model,
            dimension=dimension,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
        )
        if extra_rows_map:
            self._inject_extra_payments(rows, extra_rows_map)

        series_granularity_for_extra = series_granularity
        if dimension != "date":
            series_granularity_for_extra = granularity
        extra_series_map = (
            extra_rows_map
            if series_granularity_for_extra == granularity
            else self._aggregate_extra_payments(
                model=model,
                dimension=dimension,
                granularity=series_granularity_for_extra,
                start_date=start_date,
                end_date=end_date,
                store_id=store_id,
            )
        )
        if extra_series_map:
            self._inject_extra_payments(series_rows, extra_series_map)

        # 计算全局汇总 (Grand Total)
        summary_selects = [expr.label(name) for name, expr in metrics]
        summary_stmt = select(*summary_selects).where(
            model.biz_date.between(start_date, end_date)
        )
        if store_id is not None:
            summary_stmt = summary_stmt.where(model.store_id == store_id)

        summary_row = self.db.execute(summary_stmt).one_or_none()
        summary_data = {}
        if summary_row:
            summary_mapping = summary_row._mapping
            for name, _ in metrics:
                summary_data[name] = summary_mapping.get(name) or 0

        # 处理动态支付方式的全局汇总
        if extra_rows_map:
            global_extra = {}
            for bucket in extra_rows_map.values():
                for k, v in bucket.items():
                    global_extra[k] = global_extra.get(k, 0.0) + v
            summary_data["extra_payments"] = global_extra

        return {
            "rows": rows,
            "series_rows": series_rows,
            "summary": summary_data,  # 返回全局汇总数据
            "total": total,
            "meta": {
                "table": table,
                "dimension": dimension,
                "granularity": granularity if dimension == "date" else None,
                "series_granularity": (
                    series_granularity if dimension == "date" else None
                ),
                "store_id": store_id,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "count": total,
                "is_truncated": is_truncated,
                "auto_adjusted": auto_adjusted,
                "suggestions": suggestions,
            },
        }

    def get_aggregated_stats(
        self, metrics: List[str], group_by: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        通用聚合方法 (兼容任务分配要求)

        Args:
            metrics: 指标列表，如 ["sales", "actual", "profit"]
            group_by: 分组维度，如 "date", "store", "employee"
            filters: 过滤条件，如 {"table": "sales", "start_date": date(2025,1,1), ...}

        Returns:
            聚合结果列表
        """
        # 转换参数格式以调用 query_stats
        table = filters.get("table")
        if not table:
            raise ValueError("filters 必须包含 'table'")

        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        if not start_date or not end_date:
            raise ValueError("filters 必须包含 'start_date' 和 'end_date'")

        store_id = filters.get("store_id")
        granularity = filters.get("granularity", "day")
        page_size = filters.get("page_size", self.DEFAULT_PAGE_SIZE)
        top_n = filters.get("top_n", self.DEFAULT_TOP_N)

        # 调用现有的 query_stats 方法
        result = self.query_stats(
            table=table,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            dimension=group_by,
            granularity=granularity,
            page=1,
            page_size=page_size,
            top_n=top_n,
        )

        return result["series_rows"]

    def get_top_items(
        self,
        table: str,
        metric: str,
        dimension: str,
        limit: int = 5,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        store_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取排行榜数据

        Args:
            table: 表类型 ('booking' | 'room' | 'sales')
            metric: 指标 ('actual' | 'sales' | 'profit' | 'qty')
            dimension: 维度 ('store' | 'employee' | 'product' | 'room')
            limit: 返回数量
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            store_id: 门店ID（可选，仅当 dimension != 'store' 时有效）

        Returns:
            [
                {
                    "dimension_key": "1",
                    "dimension_label": "万象城店",
                    "metric_value": 156000.0
                },
                ...
            ]
        """
        if table not in self.TABLE_MAP:
            raise ValueError(f"不支持的表类型: {table}")

        model = self.TABLE_MAP[table]

        # ===== booking 表的排行榜 =====
        if table == "booking":
            if dimension == "store":
                query = (
                    self.db.query(
                        DimStore.id.label("dimension_key"),
                        DimStore.store_name.label("dimension_label"),
                        func.sum(model.actual_amount).label("metric_value"),
                    )
                    .join(DimStore, model.store_id == DimStore.id)
                    .group_by(model.store_id, DimStore.id, DimStore.store_name)
                    .order_by(func.sum(model.actual_amount).desc())
                )

            elif dimension == "employee":
                query = (
                    self.db.query(
                        DimEmployee.id.label("dimension_key"),
                        DimEmployee.name.label("dimension_label"),
                        func.sum(model.actual_amount).label("metric_value"),
                    )
                    .join(DimEmployee, model.employee_id == DimEmployee.id)
                    .group_by(model.employee_id, DimEmployee.id, DimEmployee.name)
                    .order_by(func.sum(model.actual_amount).desc())
                )

            elif dimension == "room":
                query = (
                    self.db.query(
                        DimRoom.id.label("dimension_key"),
                        DimRoom.room_no.label("dimension_label"),
                        func.sum(model.actual_amount).label("metric_value"),
                    )
                    .join(DimRoom, model.room_id == DimRoom.id)
                    .group_by(model.room_id, DimRoom.id, DimRoom.room_no)
                    .order_by(func.sum(model.actual_amount).desc())
                )
            else:
                raise ValueError(f"booking 表不支持的维度: {dimension}")

        # ===== room 表的排行榜 =====
        elif table == "room":
            if dimension == "room":
                query = (
                    self.db.query(
                        DimRoom.id.label("dimension_key"),
                        DimRoom.room_no.label("dimension_label"),
                        func.sum(model.actual_amount).label("metric_value"),
                    )
                    .join(DimRoom, model.room_id == DimRoom.id)
                    .group_by(model.room_id, DimRoom.id, DimRoom.room_no)
                    .order_by(func.sum(model.actual_amount).desc())
                )
            elif dimension == "store":
                query = (
                    self.db.query(
                        DimStore.id.label("dimension_key"),
                        DimStore.store_name.label("dimension_label"),
                        func.sum(model.actual_amount).label("metric_value"),
                    )
                    .join(DimStore, model.store_id == DimStore.id)
                    .group_by(model.store_id, DimStore.id, DimStore.store_name)
                    .order_by(func.sum(model.actual_amount).desc())
                )
            else:
                raise ValueError(f"room 表不支持的维度: {dimension}")

        # ===== sales 表的排行榜 =====
        elif table == "sales":
            if dimension == "product":
                # 根据 metric 选择字段
                if metric == "sales":
                    sum_field = model.sales_amount
                elif metric == "profit":
                    sum_field = model.profit
                elif metric == "qty":
                    sum_field = model.sales_qty
                else:
                    sum_field = model.sales_amount

                query = (
                    self.db.query(
                        DimProduct.id.label("dimension_key"),
                        DimProduct.name.label("dimension_label"),
                        func.sum(sum_field).label("metric_value"),
                    )
                    .join(DimProduct, model.product_id == DimProduct.id)
                    .group_by(model.product_id, DimProduct.id, DimProduct.name)
                    .order_by(func.sum(sum_field).desc())
                )
            elif dimension == "store":
                if metric == "sales":
                    sum_field = model.sales_amount
                elif metric == "profit":
                    sum_field = model.profit
                elif metric == "qty":
                    sum_field = model.sales_qty
                else:
                    sum_field = model.sales_amount

                query = (
                    self.db.query(
                        DimStore.id.label("dimension_key"),
                        DimStore.store_name.label("dimension_label"),
                        func.sum(sum_field).label("metric_value"),
                    )
                    .join(DimStore, model.store_id == DimStore.id)
                    .group_by(model.store_id, DimStore.id, DimStore.store_name)
                    .order_by(func.sum(sum_field).desc())
                )
            else:
                raise ValueError(f"sales 表不支持的维度: {dimension}")

        # 应用时间过滤
        if start_date and end_date:
            query = query.filter(model.biz_date.between(start_date, end_date))

        # 应用门店过滤
        if store_id is not None and dimension != "store":
            query = query.filter(model.store_id == store_id)

        # 应用 limit
        query = query.limit(limit)

        # 执行查询并转换为字典列表
        rows = query.all()
        result = []
        for row in rows:
            result.append(
                {
                    "dimension_key": str(row.dimension_key),
                    "dimension_label": str(row.dimension_label),
                    "metric_value": (
                        float(row.metric_value) if row.metric_value else 0.0
                    ),
                }
            )

        return result

    def get_room_efficiency_stats(
        self,
        store_id: Optional[int],
        start_date: date,
        end_date: date,
    ) -> Dict[str, float]:
        """
        计算包厢利用率与平均消费时长

        Args:
            store_id: 门店 ID (None 表示全门店汇总)
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {
                "total_orders": int,
                "avg_duration": float,
                "turnover_rate": float,
            }
        """

        total_orders = 0
        total_duration = 0.0
        room_count = 0

        # 聚合 FactRoom 的开台次数与总时长
        room_stmt = self.db.query(
            func.count(FactRoom.id).label("total_orders"),
            self._safe_sum(FactRoom.duration_min).label("total_duration"),
        ).filter(FactRoom.biz_date.between(start_date, end_date))
        if store_id is not None:
            room_stmt = room_stmt.filter(FactRoom.store_id == store_id)

        row = room_stmt.one_or_none()
        if row:
            total_orders = int(row.total_orders or 0)
            total_duration = float(row.total_duration or 0.0)

        # 统计包厢数量 (DimRoom)
        room_count_stmt = self.db.query(func.count(DimRoom.id))
        if store_id is not None:
            room_count_stmt = room_count_stmt.filter(DimRoom.store_id == store_id)
        room_count_stmt = room_count_stmt.filter(DimRoom.is_active.is_(True))
        room_count = int(room_count_stmt.scalar() or 0)

        avg_duration = total_duration / total_orders if total_orders > 0 else 0.0
        turnover_rate = total_orders / room_count if room_count > 0 else 0.0

        return {
            "total_orders": total_orders,
            "avg_duration": round(avg_duration, 2),
            "turnover_rate": round(turnover_rate, 4),
        }
