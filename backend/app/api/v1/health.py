"""
数据健康度接口

提供数据完整度/健康度查询功能
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
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


def _get_data_coverage(
    db: Session,
    store_id: Optional[int],
    table_type: str,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    获取指定门店、报表类型、日期范围的数据覆盖情况
    """
    table_info = TABLE_TYPE_MAP.get(TableType(table_type))
    if not table_info:
        return {
            "status": "missing",
            "row_count": 0,
            "date_range": None,
            "coverage_days": 0,
            "expected_days": 0,
            "latest_upload": None
        }
    
    model = table_info["model"]
    
    # 构建查询
    query = db.query(
        func.min(model.biz_date).label("min_date"),
        func.max(model.biz_date).label("max_date"),
        func.count(distinct(model.biz_date)).label("coverage_days"),
        func.count(model.id).label("row_count")
    )
    
    if store_id:
        query = query.filter(model.store_id == store_id)
    
    query = query.filter(
        model.biz_date >= start_date,
        model.biz_date <= end_date
    )
    
    result = query.first()
    
    # 获取最新上传时间
    batch_query = db.query(MetaFileBatch).filter(
        MetaFileBatch.table_type == table_type,
        MetaFileBatch.status == "success"
    )
    if store_id:
        batch_query = batch_query.filter(MetaFileBatch.store_id == store_id)
    
    latest_batch = batch_query.order_by(MetaFileBatch.created_at.desc()).first()
    
    # 计算期望天数
    expected_days = (end_date - start_date).days + 1
    
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
        "latest_upload": latest_batch.created_at.isoformat() if latest_batch else None
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
    
    # 汇总统计
    total_stores = len(stores)
    total_report_types = len(table_types)
    complete_count = 0
    missing_count = 0
    partial_count = 0
    
    # 构建详情列表
    details = []
    
    for store in stores:
        for table_type in table_types:
            coverage = _get_data_coverage(
                db=db,
                store_id=store.id,
                table_type=table_type.value,
                start_date=start_date,
                end_date=end_date
            )
            
            # 更新统计
            if coverage["status"] == "complete":
                complete_count += 1
            elif coverage["status"] == "missing":
                missing_count += 1
            elif coverage["status"] == "partial":
                partial_count += 1
            
            details.append({
                "store_id": store.id,
                "store_name": store.store_name,
                "report_type": table_type.value,
                "report_type_name": REPORT_TYPE_NAMES.get(table_type, table_type.value),
                "status": coverage["status"],
                "latest_upload": coverage["latest_upload"],
                "row_count": coverage["row_count"],
                "date_range": coverage["date_range"],
                "coverage_days": coverage["coverage_days"],
                "expected_days": coverage["expected_days"]
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

