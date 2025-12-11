"""
文件上传接口

Dev C 负责 API 路由层，串联 ETL 流水线:
Pipeline: Raw File -> Dev B (Parser) -> DataFrame -> Dev B (Cleaner) -> Cleaned Dicts -> Dev A (Importer) -> Database

参考文档:
- docs/web界面5.md (1.2 节)
- docs/任务分配.md (3.1 节 C2)
"""

import uuid
import os
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import (
    TableType,
    BatchStatus,
    UploadResponse,
    ParseResult,
    ValidationResult,
    ImportResult,
    ImportSummary,
)

router = APIRouter()
settings = get_settings()

# 临时存储解析结果 (生产环境应使用 Redis 或数据库)
_parse_cache: dict = {}


# ============================================================
# 表类型识别映射
# ============================================================

TABLE_TYPE_NAMES = {
    TableType.BOOKING: "预订汇总表",
    TableType.ROOM: "包厢开台分析表",
    TableType.SALES: "酒水销售分析表",
}


def detect_table_type(filename: str) -> tuple[TableType, str]:
    """
    根据文件名检测表类型
    
    TODO: 后续可改为基于文件内容识别
    """
    filename_lower = filename.lower()
    
    if "预订" in filename or "booking" in filename_lower:
        return TableType.BOOKING, TABLE_TYPE_NAMES[TableType.BOOKING]
    elif "包厢" in filename or "开台" in filename or "room" in filename_lower:
        return TableType.ROOM, TABLE_TYPE_NAMES[TableType.ROOM]
    elif "酒水" in filename or "销售" in filename or "sales" in filename_lower:
        return TableType.SALES, TABLE_TYPE_NAMES[TableType.SALES]
    else:
        # 默认作为预订表处理
        return TableType.BOOKING, TABLE_TYPE_NAMES[TableType.BOOKING]


def detect_store_name(filename: str) -> str:
    """
    从文件名提取门店名称
    
    TODO: 后续可改为基于文件内容识别
    """
    # 常见门店名称
    store_names = ["万象城店", "青年路店", "高新店", "曲江店"]
    
    for store in store_names:
        if store in filename:
            return store
    
    return "未知门店"


# ============================================================
# API 接口
# ============================================================

@router.post("/parse", response_model=UploadResponse, summary="解析上传文件")
async def parse_file(
    file: UploadFile = File(..., description="Excel/CSV 文件"),
    store_id: Optional[int] = Form(None, description="门店ID (可选)"),
):
    """
    步骤1: 解析上传的文件，返回预览数据供用户确认
    
    处理流程:
    1. 保存文件到临时目录
    2. 调用 ParserService 解析文件 (Dev B)
    3. 调用 CleanerService 清洗数据 (Dev B)
    4. 返回解析结果供前端预览
    """
    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    ext = file.filename.split(".")[-1].lower()
    if ext not in ["csv", "xls", "xlsx"]:
        raise HTTPException(status_code=400, detail="仅支持 .csv, .xls, .xlsx 格式")
    
    # 生成会话ID
    session_id = str(uuid.uuid4())
    
    # 保存文件
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{session_id}_{file.filename}")
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 识别表类型和门店
    table_type, table_type_name = detect_table_type(file.filename)
    store_name = detect_store_name(file.filename)
    
    # ============================================================
    # TODO: 调用 Dev B 的 Parser 和 Cleaner
    # from app.services.parser import ParserService
    # from app.services.cleaner import CleanerService
    # 
    # parser = ParserService()
    # df = parser.read_excel_file(file_path)
    # 
    # cleaner = CleanerService()
    # cleaned_data, validation = cleaner.clean_data(df, table_type)
    # ============================================================
    
    # Mock 数据 (等待 Dev B 实现后替换)
    preview_rows = []
    row_count = 0
    
    if table_type == TableType.ROOM:
        preview_rows = [
            {"包厢名称": "K07", "包厢类型": "电音中包", "开台单号": "Z-KT25120200041", "实收金额": 225},
            {"包厢名称": "K11", "包厢类型": "电音小包", "开台单号": "Z-KT25120200040", "实收金额": 193},
            {"包厢名称": "K18", "包厢类型": "电音小包", "开台单号": "Z-KT25120200039", "实收金额": 133},
        ]
        row_count = 78
    elif table_type == TableType.SALES:
        preview_rows = [
            {"酒水名称": "台湾香肠", "类别名称": "Fashion小吃", "销售数量": 12, "销售金额": 360},
            {"酒水名称": "精美美式薯条", "类别名称": "Fashion小吃", "销售数量": 8, "销售金额": 240},
            {"酒水名称": "百威啤酒", "类别名称": "啤酒", "销售数量": 45, "销售金额": 900},
        ]
        row_count = 34
    else:  # BOOKING
        preview_rows = [
            {"部门": "销售经理", "订位人": "张三", "订台数": 5, "销售金额": 12500, "实收金额": 11800},
            {"部门": "服务员", "订位人": "李四", "订台数": 3, "销售金额": 7800, "实收金额": 7500},
            {"部门": "销售经理", "订位人": "王五", "订台数": 4, "销售金额": 9600, "实收金额": 9200},
        ]
        row_count = 18
    
    validation = ValidationResult(
        is_valid=True,
        summary={"total_rows": row_count, "error_rows": 0, "warning_rows": 0},
        errors=[],
        warnings=[]
    )
    
    # 构建解析结果
    parse_result = ParseResult(
        file_type=table_type,
        file_type_name=table_type_name,
        store_id=store_id or 1,
        store_name=store_name,
        data_month=datetime.now().strftime("%Y-%m"),
        row_count=row_count,
        preview_rows=preview_rows,
        validation=validation,
        session_id=session_id,
    )
    
    # 缓存解析结果
    _parse_cache[session_id] = {
        "file_path": file_path,
        "parse_result": parse_result,
        "created_at": datetime.now(),
    }
    
    return UploadResponse(
        success=True,
        message="文件解析成功，请确认后入库",
        data=parse_result,
    )


@router.post("/confirm", response_model=UploadResponse, summary="确认入库")
async def confirm_import(
    session_id: str = Form(..., description="解析会话ID"),
    background_tasks: BackgroundTasks = None,
):
    """
    步骤2: 确认入库
    
    处理流程:
    1. 从缓存获取解析结果
    2. 调用 ImporterService 入库 (Dev A)
    3. 返回入库结果
    """
    # 获取缓存的解析结果
    cache = _parse_cache.get(session_id)
    if not cache:
        raise HTTPException(status_code=404, detail="会话已过期，请重新上传文件")
    
    parse_result: ParseResult = cache["parse_result"]
    file_path = cache["file_path"]
    
    # ============================================================
    # TODO: 调用 Dev A 的 Importer
    # from app.services.importer import ImporterService
    # 
    # importer = ImporterService()
    # batch_id, batch_no = importer.save_batch(
    #     cleaned_data=cleaned_data,
    #     table_type=parse_result.file_type,
    #     store_id=parse_result.store_id,
    #     file_name=os.path.basename(file_path),
    # )
    # ============================================================
    
    # Mock 数据 (等待 Dev A 实现后替换)
    batch_id = 1
    batch_no = f"{datetime.now().strftime('%Y%m%d')}_{parse_result.store_name}_{parse_result.file_type}"
    
    # 构建入库结果
    import_result = ImportResult(
        batch_id=batch_id,
        batch_no=batch_no,
        status=BatchStatus.SUCCESS,
        summary=ImportSummary(
            row_count=parse_result.row_count,
            sales_total=50000.00,
            actual_total=48000.00,
            balance_diff_count=0,
        ),
        message=f"成功导入 {parse_result.row_count} 条数据",
    )
    
    # 清理缓存
    del _parse_cache[session_id]
    
    return UploadResponse(
        success=True,
        message=import_result.message,
        data=import_result,
    )


@router.delete("/cancel/{session_id}", summary="取消上传")
async def cancel_upload(session_id: str):
    """
    取消上传，清理临时文件
    """
    cache = _parse_cache.get(session_id)
    if cache:
        # 删除临时文件
        file_path = cache.get("file_path")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        del _parse_cache[session_id]
    
    return {"success": True, "message": "已取消上传"}

