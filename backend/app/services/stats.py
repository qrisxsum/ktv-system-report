"""
统计聚合服务

根据表类型、时间范围、维度和粒度进行实时聚合
"""
from datetime import date
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.facts import FactBooking, FactRoom, FactSales
from app.models.dims import DimStore, DimEmployee, DimProduct, DimRoom


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

        # 构建基础 SELECT 列表
        selects = [dim_expr] + [expr.label(name) for name, expr in metrics]
        
        # 如果是非日期维度，需要 JOIN 维度表获取标签
        dim_label_expr = None
        stmt = select(*selects)
        
        if dimension == "store":
            dim_label_expr = DimStore.store_name.label("dimension_label")
            stmt = stmt.add_columns(dim_label_expr).join(
                DimStore, model.store_id == DimStore.id
            )
        elif dimension == "employee":
            if hasattr(model, "employee_id"):
                dim_label_expr = DimEmployee.name.label("dimension_label")
                stmt = stmt.add_columns(dim_label_expr).join(
                    DimEmployee, model.employee_id == DimEmployee.id
                )
        elif dimension == "product":
            if hasattr(model, "product_id"):
                dim_label_expr = DimProduct.name.label("dimension_label")
                stmt = stmt.add_columns(dim_label_expr).join(
                    DimProduct, model.product_id == DimProduct.id
                )
        elif dimension == "room":
            if hasattr(model, "room_id"):
                dim_label_expr = DimRoom.room_no.label("dimension_label")
                stmt = stmt.add_columns(dim_label_expr).join(
                    DimRoom, model.room_id == DimRoom.id
                )
        
        stmt = (
            stmt
            .where(model.biz_date.between(start_date, end_date))
            .group_by(dim_expr)
        )
        
        # 如果有维度标签，也需要加入 GROUP BY
        if dim_label_expr is not None:
            stmt = stmt.group_by(dim_label_expr)
        
        stmt = stmt.order_by(dim_expr)

        if store_id is not None:
            stmt = stmt.where(model.store_id == store_id)

        rows = self.db.execute(stmt).all()

        data: List[Dict[str, Any]] = []
        num_metrics = len(metrics)
        
        for row in rows:
            record = {"dimension_key": row[0]}
            
            # 添加指标
            for idx, (name, _) in enumerate(metrics, start=1):
                record[name] = row[idx]
            
            # 添加维度标签（如果有）
            if dim_label_expr is not None:
                record["dimension_label"] = row[num_metrics + 1]
            else:
                # 对于日期维度，直接使用日期作为标签
                record["dimension_label"] = str(row[0])
            
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
                query = self.db.query(
                    DimStore.id.label("dimension_key"),
                    DimStore.store_name.label("dimension_label"),
                    func.sum(model.actual_amount).label("metric_value"),
                ).join(
                    DimStore, model.store_id == DimStore.id
                ).group_by(
                    model.store_id, DimStore.id, DimStore.store_name
                ).order_by(
                    func.sum(model.actual_amount).desc()
                )

            elif dimension == "employee":
                query = self.db.query(
                    DimEmployee.id.label("dimension_key"),
                    DimEmployee.name.label("dimension_label"),
                    func.sum(model.actual_amount).label("metric_value"),
                ).join(
                    DimEmployee, model.employee_id == DimEmployee.id
                ).group_by(
                    model.employee_id, DimEmployee.id, DimEmployee.name
                ).order_by(
                    func.sum(model.actual_amount).desc()
                )

            elif dimension == "room":
                query = self.db.query(
                    DimRoom.id.label("dimension_key"),
                    DimRoom.room_no.label("dimension_label"),
                    func.sum(model.actual_amount).label("metric_value"),
                ).join(
                    DimRoom, model.room_id == DimRoom.id
                ).group_by(
                    model.room_id, DimRoom.id, DimRoom.room_no
                ).order_by(
                    func.sum(model.actual_amount).desc()
                )
            else:
                raise ValueError(f"booking 表不支持的维度: {dimension}")

        # ===== room 表的排行榜 =====
        elif table == "room":
            if dimension == "room":
                query = self.db.query(
                    DimRoom.id.label("dimension_key"),
                    DimRoom.room_no.label("dimension_label"),
                    func.sum(model.actual_amount).label("metric_value"),
                ).join(
                    DimRoom, model.room_id == DimRoom.id
                ).group_by(
                    model.room_id, DimRoom.id, DimRoom.room_no
                ).order_by(
                    func.sum(model.actual_amount).desc()
                )
            elif dimension == "store":
                query = self.db.query(
                    DimStore.id.label("dimension_key"),
                    DimStore.store_name.label("dimension_label"),
                    func.sum(model.actual_amount).label("metric_value"),
                ).join(
                    DimStore, model.store_id == DimStore.id
                ).group_by(
                    model.store_id, DimStore.id, DimStore.store_name
                ).order_by(
                    func.sum(model.actual_amount).desc()
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

                query = self.db.query(
                    DimProduct.id.label("dimension_key"),
                    DimProduct.name.label("dimension_label"),
                    func.sum(sum_field).label("metric_value"),
                ).join(
                    DimProduct, model.product_id == DimProduct.id
                ).group_by(
                    model.product_id, DimProduct.id, DimProduct.name
                ).order_by(
                    func.sum(sum_field).desc()
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

                query = self.db.query(
                    DimStore.id.label("dimension_key"),
                    DimStore.store_name.label("dimension_label"),
                    func.sum(sum_field).label("metric_value"),
                ).join(
                    DimStore, model.store_id == DimStore.id
                ).group_by(
                    model.store_id, DimStore.id, DimStore.store_name
                ).order_by(
                    func.sum(sum_field).desc()
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
            result.append({
                "dimension_key": str(row.dimension_key),
                "dimension_label": str(row.dimension_label),
                "metric_value": float(row.metric_value) if row.metric_value else 0.0,
            })

        return result

