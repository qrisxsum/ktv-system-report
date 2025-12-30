"""
统计聚合服务

根据表类型、时间范围、维度和粒度进行实时聚合
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import func, select, case, or_, and_, literal_column, over
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

    MAX_HOURLY_UTILIZATION_DAY_SPAN = 62

    @staticmethod
    def _safe_sum(expr):
        """统一为 SUM 结果提供 0 兜底，避免返回 NULL"""
        return func.coalesce(func.sum(expr), 0)

    def __init__(self, db: Session):
        self.db = db

    def _build_room_time_expr(self, model):
        """生成用于包厢时段计算的时间表达式"""
        if model is not FactRoom:
            raise ValueError("仅支持 FactRoom 生成时段时间表达式")
        return func.coalesce(model.open_time, model.close_time)

    def _build_room_hour_expr(self, model):
        """基于开房/关房时间推断小时"""
        time_expr = self._build_room_time_expr(model)
        return func.hour(time_expr)

    def _build_room_open_hour_expr(self, model):
        """用于 24 小时分布的小时表达式（0-23）"""
        if model is not FactRoom:
            raise ValueError("仅支持 FactRoom 生成小时表达式")
        return self._build_room_hour_expr(model)

    def _build_room_slot_expr(self, model):
        """将包厢开房时间映射为业务时段标签"""
        if model is not FactRoom:
            raise ValueError("仅支持 FactRoom 生成时段标签")
        hour_expr = self._build_room_hour_expr(model)
        return case(
            (and_(hour_expr >= 6, hour_expr < 12), "上午场"),
            (and_(hour_expr >= 12, hour_expr < 18), "下午场"),
            (and_(hour_expr >= 18, hour_expr < 24), "晚场"),
            (and_(hour_expr >= 0, hour_expr < 6), "凌晨场"),
            else_="凌晨场",
        )

    def _get_dimension_expr(
        self, model, dimension: str, granularity: str, store_id: Optional[int] = None
    ):
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
                # 全部门店视角：按商品名称聚合，避免同名商品重复
                if store_id is None and model is FactSales:
                    return DimProduct.name.label("dimension_key")
                # 单门店视角：按商品ID分组
                return model.product_id.label("dimension_key")
        elif dimension == "category":
            if model is FactSales:
                return DimProduct.category.label("dimension_key")
        elif dimension == "room":
            if hasattr(model, "room_id"):
                return model.room_id.label("dimension_key")
        elif dimension == "sales_manager":
            if hasattr(model, "sales_manager"):
                return model.sales_manager.label("dimension_key")
        elif dimension == "booker":
            if hasattr(model, "booker"):
                return func.coalesce(model.booker, "散户").label("dimension_key")
        elif dimension == "time_slot":
            if model is FactRoom:
                return self._build_room_slot_expr(model).label("dimension_key")
            if hasattr(model, "time_slot"):
                return model.time_slot.label("dimension_key")
        elif dimension == "hour":
            # 仅对 room 表开放：用于 24 小时开台负荷/利用率分析
            if model is FactRoom:
                return self._build_room_open_hour_expr(model).label("dimension_key")
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

        dim_expr = self._get_dimension_expr(model, dimension, granularity, store_id)
        # 关键修复：
        # dim_expr 可能来自维表字段（如 room_type => DimRoom.room_type、category => DimProduct.category）。
        # 如果不 join 维表，SQLAlchemy 往往会生成无条件的 FROM (model, dim_table) 笛卡尔积，
        # 在数据量稍大时会导致查询极慢甚至拖垮后续请求。
        join_model, join_condition, _, _ = self._get_dimension_join_config(
            model, dimension
        )

        query = self.db.query(
            dim_expr.label("dimension_key"),
            model.extra_payments,
            model.extra_info,
        ).select_from(model)
        if join_model is not None and join_condition is not None:
            query = query.join(join_model, join_condition)

        query = query.filter(model.biz_date.between(start_date, end_date))
        if store_id is not None:
            query = query.filter(model.store_id == store_id)
        # 仅扫描确实包含动态支付信息的记录，避免无意义全表扫描
        query = query.filter(
            or_(model.extra_payments.isnot(None), model.extra_info.isnot(None))
        )

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
            actual_sum = self._safe_sum(model.actual_amount)
            orders_sum = self._safe_sum(model.booking_qty)
            sales_sum = self._safe_sum(model.sales_amount)
            credit_sum = self._safe_sum(model.credit_amount)
            return [
                ("sales_amount", sales_sum),
                ("actual", actual_sum),
                ("performance", self._safe_sum(model.base_performance)),
                ("gift_amount", self._safe_sum(model.gift_amount)),
                ("discount_amount", self._safe_sum(model.discount_amount)),
                ("credit_amount", credit_sum),
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
                ("orders", orders_sum),
                # 派生字段：单均消费 = 实收 / 订单数
                (
                    "avg_order_amount",
                    case((orders_sum > 0, actual_sum * 1.0 / orders_sum), else_=0),
                ),
                # 派生字段：挂账率 = 挂账金额 / 实收
                (
                    "credit_rate",
                    case((actual_sum > 0, credit_sum * 1.0 / actual_sum), else_=0),
                ),
                # 派生字段：实收转化率 = 实收 / 销售金额
                (
                    "actual_rate",
                    case((sales_sum > 0, actual_sum * 1.0 / sales_sum), else_=0),
                ),
                # 注意：contribution_pct 需要在查询结果后处理中添加，因为需要全局汇总
            ]
        if model is FactRoom:
            min_minus_bill = func.coalesce(model.min_consumption, 0) - func.coalesce(
                model.bill_total, 0
            )
            min_consumption_diff_expr = case(
                (min_minus_bill > 0, min_minus_bill),
                else_=0,
            )
            bill_total_sum = self._safe_sum(model.bill_total)
            min_consumption_sum = self._safe_sum(model.min_consumption)
            gift_amount_sum = self._safe_sum(model.gift_amount)
            return [
                ("gmv", self._safe_sum(model.receivable_amount)),
                ("bill_total", bill_total_sum),
                ("actual", self._safe_sum(model.actual_amount)),
                ("min_consumption", self._safe_sum(model.min_consumption)),
                ("min_consumption_diff", self._safe_sum(model.min_consumption_diff)),
                ("gift_amount", self._safe_sum(model.gift_amount)),
                ("free_amount", self._safe_sum(model.free_amount)),
                ("credit_amount", self._safe_sum(model.credit_amount)),
                ("room_discount", self._safe_sum(model.room_discount)),
                ("beverage_discount", self._safe_sum(model.beverage_discount)),
                ("duration", self._safe_sum(model.duration_min)),
                ("orders", func.count(model.id)),
                # 派生字段：低消达成率 = 平均(单次账单合计 / 单次最低消费)
                # 先计算每次开台的达成率，再取平均值，确保在最低消费标准不一致时也能准确反映达成情况
                (
                    "low_consume_rate",
                    func.avg(
                        case(
                            (
                                model.min_consumption > 0,
                                model.bill_total * 1.0 / model.min_consumption,
                            ),
                            else_=None,
                        )
                    ),
                ),
                # 派生字段：赠送比例 = 赠送金额 / 账单合计
                (
                    "gift_ratio",
                    case(
                        (bill_total_sum > 0, gift_amount_sum * 1.0 / bill_total_sum),
                        else_=0,
                    ),
                ),
            ]
        if model is FactSales:
            total_qty = func.sum(model.sales_qty) + func.sum(model.gift_qty)
            sales_qty_sum = func.sum(model.sales_qty)
            profit_sum = func.sum(model.profit)
            cost_sum = func.sum(model.cost_total)
            return [
                ("sales_qty", sales_qty_sum),
                ("sales_amount", func.sum(model.sales_amount)),
                ("gift_qty", func.sum(model.gift_qty)),
                ("gift_amount", func.sum(model.gift_amount)),
                ("cost_total", cost_sum),
                ("cost", cost_sum),
                ("profit", profit_sum),
                ("profit_rate", func.avg(model.profit_rate)),  # 利润率取平均值
                # 派生字段：赠送率 = 赠送数量 / (销售数量 + 赠送数量)
                (
                    "gift_rate",
                    case(
                        (total_qty > 0, func.sum(model.gift_qty) * 1.0 / total_qty),
                        else_=0,
                    ),
                ),
                # 派生字段：单品毛利 = 利润 / 销量
                (
                    "unit_profit",
                    case(
                        (sales_qty_sum > 0, profit_sum * 1.0 / sales_qty_sum), else_=0
                    ),
                ),
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
            # 获取门店名称的子查询，避免多重 join 逻辑复杂化
            store_name_subquery = (
                select(DimStore.store_name)
                .where(DimStore.id == DimEmployee.store_id)
                .scalar_subquery()
                .label("store_name")
            )
            extra_columns = [
                store_name_subquery,
                DimEmployee.store_id.label("store_id"),
            ]
            return (
                DimEmployee,
                model.employee_id == DimEmployee.id,
                DimEmployee.name.label("dimension_label"),
                extra_columns,
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
            # 获取所属门店名称的子查询
            store_name_subquery = (
                select(DimStore.store_name)
                .where(DimStore.id == DimRoom.store_id)
                .scalar_subquery()
                .label("store_name")
            )
            return (
                DimRoom,
                model.room_id == DimRoom.id,
                DimRoom.room_no.label("dimension_label"),
                [store_name_subquery],
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
        if dimension == "booker":
            label_expr = (
                func.coalesce(model.booker, "散户").label("dimension_label")
                if hasattr(model, "booker")
                else None
            )
            return (None, None, label_expr, [])
        if dimension == "time_slot":
            if model is FactRoom:
                slot_label = self._build_room_slot_expr(model).label("dimension_label")
                return (None, None, slot_label, [])
            if hasattr(model, "time_slot"):
                return (None, None, model.time_slot.label("dimension_label"), [])
        if dimension == "hour":
            # hour 直接使用 dimension_key 作为 label
            return (None, None, None, [])
        return (None, None, None, [])

    def _get_active_room_count(self, store_id: Optional[int]) -> int:
        stmt = self.db.query(func.count(DimRoom.id)).filter(DimRoom.is_active.is_(True))
        if store_id is not None:
            stmt = stmt.filter(DimRoom.store_id == store_id)
        return int(stmt.scalar() or 0)

    @staticmethod
    def _coalesce_dt(*values: Any) -> Optional[datetime]:
        for val in values:
            if isinstance(val, datetime):
                return val
        return None

    def _query_room_hourly_utilization(
        self,
        start_date: date,
        end_date: date,
        store_id: Optional[int],
    ) -> Dict[str, Any]:
        """
        24 小时开台负荷/利用率（按小时）：
        - orders：以开房时间（缺失则用关房时间）所在小时计数
        - gmv：同上小时归属汇总
        - occupied_minutes：基于 open_time/close_time（或 duration_min 兜底）将占用分钟按小时切片分摊
        """
        day_span = (end_date - start_date).days + 1
        if day_span > self.MAX_HOURLY_UTILIZATION_DAY_SPAN:
            raise ValueError(
                f"小时利用率计算跨度过大（{day_span} 天），请缩小到 {self.MAX_HOURLY_UTILIZATION_DAY_SPAN} 天以内"
            )

        # 初始化 0-23 桶
        buckets: Dict[int, Dict[str, float]] = {
            h: {"orders": 0.0, "gmv": 0.0, "occupied_minutes": 0.0} for h in range(24)
        }

        # 1) orders / gmv：按“开房(或关房)时间所在小时”归属
        hour_expr = func.hour(func.coalesce(FactRoom.open_time, FactRoom.close_time))
        agg_stmt = self.db.query(
            hour_expr.label("hour"),
            func.count(FactRoom.id).label("orders"),
            self._safe_sum(FactRoom.receivable_amount).label("gmv"),
        ).filter(FactRoom.biz_date.between(start_date, end_date))
        if store_id is not None:
            agg_stmt = agg_stmt.filter(FactRoom.store_id == store_id)
        agg_stmt = agg_stmt.group_by(hour_expr)
        for row in agg_stmt.all():
            hour = int(row.hour) if row.hour is not None else None
            if hour is None or hour < 0 or hour > 23:
                continue
            buckets[hour]["orders"] = float(row.orders or 0)
            buckets[hour]["gmv"] = float(row.gmv or 0.0)

        # 2) occupied_minutes：按小时切片分摊
        raw_stmt = self.db.query(
            FactRoom.open_time, FactRoom.close_time, FactRoom.duration_min
        ).filter(FactRoom.biz_date.between(start_date, end_date))
        if store_id is not None:
            raw_stmt = raw_stmt.filter(FactRoom.store_id == store_id)

        def add_overlap_minutes(start_dt: datetime, end_dt: datetime):
            if end_dt <= start_dt:
                return
            cursor = start_dt
            # 从开始时间所在小时的整点开始切片
            while cursor < end_dt:
                hour_start = cursor.replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                overlap_start = max(start_dt, hour_start)
                overlap_end = min(end_dt, hour_end)
                if overlap_end > overlap_start:
                    minutes = (overlap_end - overlap_start).total_seconds() / 60.0
                    buckets[hour_start.hour]["occupied_minutes"] += float(minutes)
                cursor = hour_end

        for open_time, close_time, duration_min in raw_stmt.all():
            start_dt = self._coalesce_dt(open_time, close_time)
            if start_dt is None:
                continue
            end_dt = self._coalesce_dt(close_time)
            if end_dt is None:
                try:
                    dur = int(duration_min or 0)
                except (TypeError, ValueError):
                    dur = 0
                end_dt = start_dt + timedelta(minutes=max(dur, 0))
            # 防御：异常数据导致关房早于开房时，直接跳过或兜底
            if end_dt < start_dt:
                continue
            add_overlap_minutes(start_dt, end_dt)

        rows: List[Dict[str, Any]] = []
        for h in range(24):
            rows.append(
                {
                    "dimension_key": h,
                    "dimension_label": f"{h:02d}:00",
                    "orders": int(round(buckets[h]["orders"])),
                    "gmv": round(buckets[h]["gmv"], 2),
                    "occupied_minutes": round(buckets[h]["occupied_minutes"], 2),
                }
            )

        active_room_count = self._get_active_room_count(store_id)
        return {
            "rows": rows,
            "series_rows": rows,
            "summary": {
                "orders": int(sum(r["orders"] for r in rows)),
                "gmv": round(sum(float(r["gmv"] or 0) for r in rows), 2),
                "occupied_minutes": round(
                    sum(float(r["occupied_minutes"] or 0) for r in rows), 2
                ),
                "active_room_count": active_room_count,
            },
            "total": 24,
            "meta": {
                "table": "room",
                "dimension": "hour",
                "granularity": None,
                "series_granularity": None,
                "store_id": store_id,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "count": 24,
                "active_room_count": active_room_count,
                "is_truncated": False,
                "auto_adjusted": False,
                "suggestions": [],
            },
        }

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
        dim_expr = self._get_dimension_expr(model, dimension, granularity, store_id)
        metric_columns: Dict[str, Any] = {}
        select_columns = [dim_expr]
        # 保存原始聚合表达式，用于窗口函数
        original_metrics: Dict[str, Any] = {}
        for name, expr in metrics:
            labeled = expr.label(name)
            metric_columns[name] = labeled
            original_metrics[name] = expr  # 保存原始表达式
            select_columns.append(labeled)

        (
            join_model,
            join_condition,
            dim_label_expr,
            extra_columns,
        ) = self._get_dimension_join_config(model, dimension)
        # 当按商品名称分组时（全部门店），dim_expr 已经是 DimProduct.name
        # 此时 dim_label_expr 也是 DimProduct.name，使用 dim_expr 作为 label 即可
        if dim_label_expr is not None:
            # 如果 dim_expr 已经是商品名称（全部门店按名称分组），则使用 dim_expr 作为 label
            if dimension == "product" and store_id is None and model is FactSales:
                # dim_expr 已经是 DimProduct.name，直接使用它作为 label
                dim_label_expr = dim_expr.label("dimension_label")
            select_columns.append(dim_label_expr)
        extra_column_names: List[str] = []
        for extra_col in extra_columns:
            select_columns.append(extra_col)
            extra_column_names.append(extra_col.key)

        # 对于 booking 表的员工维度，添加 contribution_pct 字段（使用窗口函数）
        # 注意：窗口函数需要在聚合之后计算，使用原始聚合表达式
        if (
            model is FactBooking
            and dimension == "employee"
            and "actual" in original_metrics
        ):
            actual_expr = original_metrics["actual"]
            # 使用窗口函数计算总实收（在所有分组上求和）
            # 窗口函数中使用原始聚合表达式
            total_actual_window = func.sum(actual_expr).over()
            # 计算贡献占比 = (当前实收 / 总实收) * 100
            contribution_pct_expr = case(
                (total_actual_window > 0, actual_expr * 100.0 / total_actual_window),
                else_=0,
            ).label("contribution_pct")
            select_columns.append(contribution_pct_expr)
            metric_columns["contribution_pct"] = contribution_pct_expr

        stmt = select(*select_columns)
        if join_model is not None:
            stmt = stmt.join(join_model, join_condition)
        stmt = stmt.where(model.biz_date.between(start_date, end_date))
        if store_id is not None:
            stmt = stmt.where(model.store_id == store_id)
        stmt = stmt.group_by(dim_expr)
        # 如果 dim_label_expr 和 dim_expr 引用同一个字段，不需要重复分组
        if dim_label_expr is not None:
            # 检查 dim_expr 和 dim_label_expr 是否引用同一个字段
            # 当按商品名称分组时（全部门店），它们引用同一个字段 DimProduct.name
            if dimension == "product" and store_id is None and model is FactSales:
                # 已经按 dim_expr 分组，dim_label_expr 是同一个字段，不需要重复分组
                pass
            else:
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
        metric_columns: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        rows = self.db.execute(stmt).all()
        result: List[Dict[str, Any]] = []
        extra_column_names = extra_column_names or []
        # 获取所有指标字段名（包括派生字段如 contribution_pct）
        metric_names = [name for name, _ in metrics]
        if metric_columns:
            # 添加不在 metrics 中的额外字段（如 contribution_pct）
            for name in metric_columns.keys():
                if name not in metric_names:
                    metric_names.append(name)
        for row in rows:
            mapping = row._mapping
            record = {"dimension_key": mapping["dimension_key"]}
            for name in metric_names:
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
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        通用聚合查询
        """
        if table not in self.TABLE_MAP:
            raise ValueError(f"不支持的表类型: {table}")

        model = self.TABLE_MAP[table]
        if granularity not in self.GRANULARITY_ORDER:
            raise ValueError(f"不支持的粒度: {granularity}")

        # 特殊：room + hour 用于 24 小时负荷/利用率（需要按小时切片分摊占用分钟）
        if table == "room" and dimension == "hour":
            return self._query_room_hourly_utilization(
                start_date=start_date, end_date=end_date, store_id=store_id
            )

        self._validate_pagination(page, page_size)
        top_n = self._clamp_top_n(top_n)

        metrics = self._get_metrics_exprs(model)

        rows_stmt, dim_expr, has_label_rows, metric_columns_rows, extra_column_names = (
            self._build_group_stmt(
                model=model,
                dimension=dimension,
                granularity=granularity,
                metrics=metrics,
                start_date=start_date,
                end_date=end_date,
                store_id=store_id,
            )
        )

        # 应用自定义排序
        if sort_by and sort_by in metric_columns_rows:
            # 直接使用表达式对象排序
            sort_col_expr = metric_columns_rows[sort_by]
            rows_stmt = rows_stmt.order_by(None)  # 清除默认排序
            if sort_order == "asc":
                rows_stmt = rows_stmt.order_by(sort_col_expr.asc(), dim_expr)
            else:
                rows_stmt = rows_stmt.order_by(sort_col_expr.desc(), dim_expr)
        elif sort_by == "dimension_value" or sort_by == "dimension_key":
            # 按维度值排序
            rows_stmt = rows_stmt.order_by(None)
            if sort_order == "asc":
                rows_stmt = rows_stmt.order_by(dim_expr.asc())
            else:
                rows_stmt = rows_stmt.order_by(dim_expr.desc())

        total = self._count_group_rows(rows_stmt)
        offset = (page - 1) * page_size
        paginated_stmt = rows_stmt.offset(offset).limit(page_size)
        rows = self._fetch_rows(
            paginated_stmt,
            metrics,
            has_label_rows,
            extra_column_names,
            metric_columns_rows,
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
                metric_columns_series,
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
                series_stmt,
                metrics,
                has_label_series,
                extra_column_names_series,
                metric_columns_series,
            )
        else:
            (
                series_stmt,
                dim_expr_series,
                has_label_series,
                metric_columns_series,
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
            primary_metric_name = self._determine_primary_metric(metric_columns_series)
            primary_metric_expr = metric_columns_series[primary_metric_name]
            series_stmt = series_stmt.order_by(None).order_by(
                primary_metric_expr.desc(), dim_expr_series
            )
            series_stmt = series_stmt.limit(top_n)
            series_rows = self._fetch_rows(
                series_stmt,
                metrics,
                has_label_series,
                extra_column_names_series,
                metric_columns_series,
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

        # 补充：room 表提供活跃包厢数，便于前端计算翻台率/利用率
        if table == "room":
            summary_data["active_room_count"] = self._get_active_room_count(store_id)

        # 注意：contribution_pct 现在在 SQL 层面使用窗口函数计算，无需后处理

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
                "active_room_count": (
                    summary_data.get("active_room_count") if table == "room" else None
                ),
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
                        DimStore.store_name.label("store_label"),
                        func.sum(model.actual_amount).label("metric_value"),
                    )
                    .join(DimEmployee, model.employee_id == DimEmployee.id)
                    .join(DimStore, DimEmployee.store_id == DimStore.id)
                    .group_by(
                        model.employee_id,
                        DimEmployee.id,
                        DimEmployee.name,
                        DimStore.store_name,
                    )
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

                if store_id is None:
                    # 全部门店视角：按商品名称聚合，忽略具体的 product_id
                    query = (
                        self.db.query(
                            DimProduct.name.label("dimension_key"),
                            DimProduct.name.label("dimension_label"),
                            func.sum(sum_field).label("metric_value"),
                        )
                        .join(DimProduct, model.product_id == DimProduct.id)
                        .group_by(DimProduct.name)
                        .order_by(func.sum(sum_field).desc())
                    )
                else:
                    # 单门店视角：保留原有的按 ID 分组逻辑
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
            item = {
                "dimension_key": str(row.dimension_key),
                "dimension_label": str(row.dimension_label),
                "metric_value": (float(row.metric_value) if row.metric_value else 0.0),
            }
            # 如果查询结果中包含 store_label，也一并返回
            if hasattr(row, "store_label"):
                item["store_label"] = str(row.store_label)
            result.append(item)

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
