"""
数据健康度接口

提供数据完整度/健康度查询功能
"""

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from fastapi import APIRouter, Query, Depends, HTTPException

from app.core.database import get_db
from app.core.security import get_current_manager
from app.models.meta import MetaFileBatch
from app.models.dims import DimStore
from app.models.facts import FactBooking, FactRoom, FactSales, FactMemberChange
from app.schemas import TableType

router = APIRouter()

# 表类型映射
TABLE_TYPE_MAP = {
    TableType.BOOKING: {
        "name": "预订汇总",
        "model": FactBooking,
        "table_name": "fact_booking"
    },
    TableType.ROOM: {
        "name": "包厢开台分析",
        "model": FactRoom,
        "table_name": "fact_room"
    },
    TableType.SALES: {
        "name": "酒水销售分析",
        "model": FactSales,
        "table_name": "fact_sales"
    },
    TableType.MEMBER_CHANGE: {
        "name": "连锁会员变动明细",
        "model": FactMemberChange,
        "table_name": "fact_member_change"
    }
}

# 报表类型名称映射（用于前端显示）
REPORT_TYPE_NAMES = {
    TableType.BOOKING: "预订汇总",
    TableType.ROOM: "包厢开台分析",
    TableType.SALES: "酒水销售分析",
    TableType.MEMBER_CHANGE: "连锁会员变动明细",
}


def _get_all_dates_in_range(start_date: date, end_date: date) -> Set[date]:
    """获取日期范围内的所有日期"""
    dates = set()
    current = start_date
    while current <= end_date:
        dates.add(current)
        current += timedelta(days=1)
    return dates


def _batch_get_coverage_data(
    db: Session,
    store_ids: List[int],
    table_type: str,
    start_date: date,
    end_date: date
) -> Dict[int, Dict[str, Any]]:
    """
    批量获取多个门店的数据覆盖情况（优化版本，减少数据库查询）
    
    Returns:
        Dict[store_id, coverage_info]
    """
    table_info = TABLE_TYPE_MAP.get(TableType(table_type))
    if not table_info:
        return {sid: {
            "status": "missing",
            "row_count": 0,
            "date_range": {"start": None, "end": None},
            "coverage_days": 0,
            "expected_days": 0,
            "latest_upload": None,
            "missing_dates": []
        } for sid in store_ids}
    
    model = table_info["model"]
    expected_days = (end_date - start_date).days + 1
    all_dates = _get_all_dates_in_range(start_date, end_date)
    
    # 批量查询：按门店分组获取统计数据
    stats_query = db.query(
        model.store_id,
        func.min(model.biz_date).label("min_date"),
        func.max(model.biz_date).label("max_date"),
        func.count(distinct(model.biz_date)).label("coverage_days"),
        func.count(model.id).label("row_count")
    ).filter(
        model.store_id.in_(store_ids),
        model.biz_date >= start_date,
        model.biz_date <= end_date
    ).group_by(model.store_id)
    
    stats_results = {r.store_id: r for r in stats_query.all()}
    
    # 批量查询：获取每个门店实际覆盖的日期列表
    covered_dates_query = db.query(
        model.store_id,
        model.biz_date
    ).filter(
        model.store_id.in_(store_ids),
        model.biz_date >= start_date,
        model.biz_date <= end_date
    ).distinct()
    
    # 按门店分组覆盖的日期
    covered_dates_map: Dict[int, Set[date]] = {sid: set() for sid in store_ids}
    for row in covered_dates_query.all():
        covered_dates_map[row.store_id].add(row.biz_date)
    
    # 批量查询：获取最新上传时间
    latest_batch_subquery = db.query(
        MetaFileBatch.store_id,
        func.max(MetaFileBatch.created_at).label("latest_upload")
    ).filter(
        MetaFileBatch.table_type == table_type,
        MetaFileBatch.status == "success",
        MetaFileBatch.store_id.in_(store_ids)
    ).group_by(MetaFileBatch.store_id).subquery()
    
    batch_results = {
        r.store_id: r.latest_upload 
        for r in db.query(latest_batch_subquery).all()
    }
    
    # 构建结果
    result = {}
    for store_id in store_ids:
        stats = stats_results.get(store_id)
        covered_dates = covered_dates_map.get(store_id, set())
        missing_dates = all_dates - covered_dates
        
        row_count = stats.row_count if stats else 0
        coverage_days = stats.coverage_days if stats else 0
        min_date = stats.min_date if stats else None
        max_date = stats.max_date if stats else None
        latest_upload = batch_results.get(store_id)
        
        # 判断状态
        if row_count == 0:
            status = "missing"
        elif coverage_days < expected_days:
            status = "partial"
        else:
            status = "complete"
        
        result[store_id] = {
            "status": status,
            "row_count": row_count,
            "date_range": {
                "start": min_date.isoformat() if min_date else None,
                "end": max_date.isoformat() if max_date else None
            },
            "coverage_days": coverage_days,
            "expected_days": expected_days,
            "latest_upload": latest_upload.isoformat() if latest_upload else None,
            "missing_dates": sorted([d.isoformat() for d in missing_dates])
        }
    
    return result


def _get_data_coverage(
    db: Session,
    store_id: Optional[int],
    table_type: str,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    获取指定门店、报表类型、日期范围的数据覆盖情况
    
    注意：建议使用 _batch_get_coverage_data 批量查询以提升性能
    """
    # 复用批量查询方法
    if store_id:
        result = _batch_get_coverage_data(db, [store_id], table_type, start_date, end_date)
        return result.get(store_id, {
            "status": "missing",
            "row_count": 0,
            "date_range": {"start": None, "end": None},
            "coverage_days": 0,
            "expected_days": 0,
            "latest_upload": None,
            "missing_dates": []
        })
    
    # 全部门店汇总查询
    table_info = TABLE_TYPE_MAP.get(TableType(table_type))
    if not table_info:
        return {
            "status": "missing",
            "row_count": 0,
            "date_range": {"start": None, "end": None},
            "coverage_days": 0,
            "expected_days": 0,
            "latest_upload": None,
            "missing_dates": []
        }
    
    model = table_info["model"]
    expected_days = (end_date - start_date).days + 1
    all_dates = _get_all_dates_in_range(start_date, end_date)
    
    # 构建查询
    query = db.query(
        func.min(model.biz_date).label("min_date"),
        func.max(model.biz_date).label("max_date"),
        func.count(distinct(model.biz_date)).label("coverage_days"),
        func.count(model.id).label("row_count")
    ).filter(
        model.biz_date >= start_date,
        model.biz_date <= end_date
    )
    
    result = query.first()
    
    # 获取覆盖的日期列表
    covered_dates_query = db.query(
        model.biz_date
    ).filter(
        model.biz_date >= start_date,
        model.biz_date <= end_date
    ).distinct()
    
    covered_dates = {row.biz_date for row in covered_dates_query.all()}
    missing_dates = all_dates - covered_dates
    
    # 获取最新上传时间
    batch_query = db.query(MetaFileBatch).filter(
        MetaFileBatch.table_type == table_type,
        MetaFileBatch.status == "success"
    )
    
    latest_batch = batch_query.order_by(MetaFileBatch.created_at.desc()).first()
    
    # 处理查询结果
    row_count = result.row_count or 0 if result else 0
    coverage_days = result.coverage_days or 0 if result else 0
    min_date = result.min_date if result else None
    max_date = result.max_date if result else None
    
    # 判断状态
    if row_count == 0:
        status = "missing"
    elif coverage_days < expected_days:
        status = "partial"
    else:
        status = "complete"
    
    return {
        "status": status,
        "row_count": row_count,
        "date_range": {
            "start": min_date.isoformat() if min_date else None,
            "end": max_date.isoformat() if max_date else None
        },
        "coverage_days": coverage_days,
        "expected_days": expected_days,
        "latest_upload": latest_batch.created_at.isoformat() if latest_batch else None,
        "missing_dates": sorted([d.isoformat() for d in missing_dates])
    }


@router.get("/coverage", summary="获取数据完整度")
async def get_data_coverage(
    store_id: Optional[int] = Query(None, description="门店ID（不传则查询所有门店）"),
    data_month: Optional[str] = Query(None, description="数据月份（YYYY-MM格式，不传则查询最新月份）"),
    report_types: Optional[str] = Query(None, description="报表类型（逗号分隔，如：booking,room,sales）"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_manager),
):
    """
    获取数据完整度视图
    
    返回各门店、各报表类型的数据覆盖情况
    """
    # 根据用户角色过滤store_id权限
    if current_user["role"] == "manager":
        if store_id is None:
            store_id = current_user["store_id"]
        elif store_id != current_user["store_id"]:
            raise HTTPException(status_code=403, detail="无权限访问其他门店数据")
    
    # 解析日期范围
    if data_month:
        try:
            year, month = map(int, data_month.split("-"))
            start_date = date(year, month, 1)
            # 计算该月最后一天
            if month == 12:
                end_date = date(year + 1, 1, 1) - date.resolution
            else:
                end_date = date(year, month + 1, 1) - date.resolution
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM")
    else:
        # 默认查询最新有数据的月份
        latest_date = db.query(func.max(FactBooking.biz_date)).scalar()
        if not latest_date:
            latest_date = date.today()
        
        start_date = latest_date.replace(day=1)
        if latest_date.month == 12:
            end_date = date(latest_date.year + 1, 1, 1) - date.resolution
        else:
            end_date = date(latest_date.year, latest_date.month + 1, 1) - date.resolution
    
    # 解析报表类型
    if report_types:
        requested_types = [t.strip() for t in report_types.split(",")]
        table_types = [t for t in TableType if t.value in requested_types]
    else:
        table_types = list(TableType)
    
    # 获取门店列表
    store_query = db.query(DimStore)
    if store_id:
        store_query = store_query.filter(DimStore.id == store_id)
    stores = store_query.filter(DimStore.is_active == True).all()
    store_ids = [s.id for s in stores]
    store_name_map = {s.id: s.store_name for s in stores}
    
    # 汇总统计
    total_stores = len(stores)
    total_report_types = len(table_types)
    complete_count = 0
    missing_count = 0
    partial_count = 0
    
    # 构建详情列表 - 使用批量查询优化性能
    details = []
    
    # 按报表类型批量查询（减少查询次数：从 N*M 次降为 M 次）
    for table_type in table_types:
        coverage_map = _batch_get_coverage_data(
            db=db,
            store_ids=store_ids,
            table_type=table_type.value,
            start_date=start_date,
            end_date=end_date
        )
        
        for store_id_item in store_ids:
            coverage = coverage_map.get(store_id_item, {})
            
            # 更新统计
            status = coverage.get("status", "missing")
            if status == "complete":
                complete_count += 1
            elif status == "missing":
                missing_count += 1
            elif status == "partial":
                partial_count += 1
            
            details.append({
                "store_id": store_id_item,
                "store_name": store_name_map.get(store_id_item, ""),
                "report_type": table_type.value,
                "report_type_name": REPORT_TYPE_NAMES.get(table_type, table_type.value),
                "status": status,
                "latest_upload": coverage.get("latest_upload"),
                "row_count": coverage.get("row_count", 0),
                "date_range": coverage.get("date_range", {"start": None, "end": None}),
                "coverage_days": coverage.get("coverage_days", 0),
                "expected_days": coverage.get("expected_days", 0),
                "missing_dates": coverage.get("missing_dates", [])
            })
    
    return {
        "success": True,
        "data": {
            "summary": {
                "total_stores": total_stores,
                "total_report_types": total_report_types,
                "complete_count": complete_count,
                "missing_count": missing_count,
                "partial_count": partial_count,
                "error_count": 0  # 暂时不支持错误统计
            },
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "details": details
        }
    }

