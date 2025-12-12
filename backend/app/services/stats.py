"""
统计聚合服务

根据表类型、时间范围、维度和粒度进行实时聚合
"""
from datetime import date
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.facts import FactBooking, FactRoom, FactSales


class StatsService:
    """统计聚合服务"""

    TABLE_MAP = {
        "booking": FactBooking,
        "room": FactRoom,
        "sales": FactSales,
    }

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
        elif dimension == "room":
            if hasattr(model, "room_id"):
                return model.room_id.label("dimension_key")
        elif dimension == "room_type":
            if hasattr(model, "room_id"):
                # room_type 在 fact_room 中可作为冗余来源（若有）
                if hasattr(model, "room_type"):
                    return model.room_type.label("dimension_key")
        raise ValueError(f"不支持的维度: {dimension}  或该表缺少对应字段")

    def _get_metrics_exprs(self, model) -> List[Tuple[str, Any]]:
        """根据表类型生成常用指标表达式"""
        if model is FactBooking:
            return [
                ("sales", func.sum(model.sales_amount)),
                ("actual", func.sum(model.actual_amount)),
                ("performance", func.sum(model.base_performance)),
                ("gift_amount", func.sum(model.gift_amount)),
                ("discount_amount", func.sum(model.discount_amount)),
                ("orders", func.count()),
            ]
        if model is FactRoom:
            return [
                ("gmv", func.sum(model.receivable_amount)),
                ("actual", func.sum(model.actual_amount)),
                ("gift_amount", func.sum(model.gift_amount)),
                ("room_discount", func.sum(model.room_discount)),
                ("beverage_discount", func.sum(model.beverage_discount)),
                ("orders", func.count(model.order_no)),
            ]
        if model is FactSales:
            return [
                ("sales_qty", func.sum(model.sales_qty)),
                ("sales_amount", func.sum(model.sales_amount)),
                ("gift_qty", func.sum(model.gift_qty)),
                ("gift_amount", func.sum(model.gift_amount)),
                ("cost_total", func.sum(model.cost_total)),
                ("profit", func.sum(model.profit)),
            ]
        raise ValueError("未知表类型")

    def query_stats(
        self,
        table: str,
        start_date: date,
        end_date: date,
        store_id: Optional[int] = None,
        dimension: str = "date",
        granularity: str = "day",
    ) -> Dict[str, Any]:
        """
        通用聚合查询
        """
        if table not in self.TABLE_MAP:
            raise ValueError(f"不支持的表类型: {table}")

        model = self.TABLE_MAP[table]
        dim_expr = self._get_dimension_expr(model, dimension, granularity)
        metrics = self._get_metrics_exprs(model)

        selects = [dim_expr] + [expr.label(name) for name, expr in metrics]

        stmt = (
            select(*selects)
            .where(model.biz_date.between(start_date, end_date))
            .group_by(dim_expr)
            .order_by(dim_expr)
        )

        if store_id is not None:
            stmt = stmt.where(model.store_id == store_id)

        rows = self.db.execute(stmt).all()

        data: List[Dict[str, Any]] = []
        for row in rows:
            record = {"dimension_key": row[0]}
            for idx, (name, _) in enumerate(metrics, start=1):
                record[name] = row[idx]
            data.append(record)

        return {
            "data": data,
            "meta": {
                "table": table,
                "dimension": dimension,
                "granularity": granularity if dimension == "date" else None,
                "store_id": store_id,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "count": len(data),
            },
        }

    def get_aggregated_stats(
        self,
        metrics: List[str],
        group_by: str,
        filters: Dict[str, Any]
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

        # 调用现有的 query_stats 方法
        result = self.query_stats(
            table=table,
            start_date=start_date,
            end_date=end_date,
            store_id=store_id,
            dimension=group_by,
            granularity=granularity
        )

        return result["data"]

