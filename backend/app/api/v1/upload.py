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
import hashlib
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime
from decimal import Decimal
import math

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
    Depends,
)
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import (
    TableType,
    BatchStatus,
    UploadResponse,
    ParseResult,
    ValidationResult,
    ImportResult,
    ImportSummary,
    RowError,
)
from app.core.database import get_db
<<<<<<< HEAD
from app.core.security import get_current_admin
=======
from app.models.meta import MetaFileBatch
>>>>>>> 74df8e1d05a8a41e361c03c6e8f9d57f1ca9c1dd
from app.services.cleaner import CleanerService
from app.services.parser import (
    read_excel_file,
    detect_report_type,
    ParserError,
)
from app.services.importer import ImporterService, DuplicateFileError, describe_duplicate_batch

router = APIRouter()
settings = get_settings()

# 临时存储解析结果 (生产环境应使用 Redis 或数据库)
_parse_cache: dict = {}


try:  # numpy/pandas 标量在 FastAPI/Pydantic 序列化时经常导致 500
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None


def _to_builtin(obj: Any) -> Any:
    """
    递归把 pandas/numpy 等类型转换为可 JSON 序列化的 Python 原生类型。

    典型场景：pandas 读出来的数值是 numpy.int64 / numpy.float64，
    Pydantic v2 默认无法序列化，会抛 PydanticSerializationError。
    """
    if obj is None:
        return None

    # numpy 标量 / 数组
    if np is not None:
        if isinstance(obj, np.generic):
            obj = obj.item()
        elif isinstance(obj, np.ndarray):
            obj = obj.tolist()

    # 规范化 JSON 不支持的浮点：NaN/Inf
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None

    # 常见可疑类型
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="ignore")

    # 容器递归处理
    if isinstance(obj, dict):
        # key 也强制转成 str，避免出现非字符串 key 影响 JSON
        return {str(k): _to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_builtin(x) for x in obj]

    return obj


def _calculate_file_hash(contents: bytes) -> str:
    """计算文件内容的 SHA256 哈希"""
    return hashlib.sha256(contents).hexdigest()


def _find_success_batch_by_hash(db: Session, file_hash: Optional[str]) -> Optional[MetaFileBatch]:
    if not file_hash:
        return None
    return (
        db.query(MetaFileBatch)
        .filter(
            MetaFileBatch.file_hash == file_hash,
            MetaFileBatch.status == BatchStatus.SUCCESS.value,
        )
        .order_by(MetaFileBatch.created_at.desc())
        .first()
    )


def _conflict_response(message: str) -> JSONResponse:
    payload = UploadResponse(success=False, message=message, data=None)
    # 注意：UploadResponse 内含 timestamp(datetime)，需用 jsonable_encoder 才能被 JSONResponse 正确序列化
    return JSONResponse(status_code=409, content=jsonable_encoder(payload))


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


def _convert_validation_result(
    cleaner_validation,
) -> Tuple[ValidationResult, Optional[str], Dict[str, Any]]:
    """
    将 Cleaner 的 ValidationResult 转为 API 层 Schema，并提取 meta 信息。
    """
    errors: List[RowError] = []
    warnings: List[str] = []
    error_rows = 0
    warning_rows = 0

    for err in cleaner_validation.errors:
        if getattr(err, "severity", "error") == "warning":
            warnings.append(err.message)
            warning_rows += 1
        else:
            errors.append(
                RowError(
                    row_index=int(err.row_index) if err.row_index is not None else -1,
                    column=str(err.column),
                    message=str(err.message),
                    raw_data=_to_builtin(err.raw_data or {}),
                )
            )
            error_rows += 1

    summary = {
        "total_rows": (
            int(cleaner_validation.total_rows)
            if cleaner_validation.total_rows is not None
            else 0
        ),
        "error_rows": error_rows,
        "warning_rows": warning_rows,
    }

    api_validation = ValidationResult(
        is_valid=cleaner_validation.is_valid,
        summary=summary,
        errors=errors,
        warnings=warnings,
    )

    meta = {}
    if isinstance(cleaner_validation.summary, dict):
        meta = cleaner_validation.summary.get("meta") or {}

    store_name = meta.get("store_name") if isinstance(meta, dict) else None

    return api_validation, store_name, meta


def _determine_table_type(filename: str, df) -> Tuple[TableType, str]:
    """
    结合文件内容和文件名，确定表类型。
    """
    detected = detect_report_type(df, filename)
    if detected in TableType._value2member_map_:
        table_type = TableType(detected)
        return table_type, TABLE_TYPE_NAMES[table_type]
    return detect_table_type(filename)


# ============================================================
# API 接口
# ============================================================


@router.post("/parse", response_model=UploadResponse, summary="解析上传文件")
async def parse_file(
    file: UploadFile = File(..., description="Excel/CSV 文件"),
    store_id: Optional[int] = Form(None, description="门店ID (可选)"),
    db: Session = Depends(get_db),
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

    file_hash: Optional[str] = None
    try:
        contents = await file.read()

        if not contents:
            raise HTTPException(status_code=400, detail="文件内容为空")

        file_hash = _calculate_file_hash(contents)
        duplicate_batch = _find_success_batch_by_hash(db, file_hash)
        if duplicate_batch:
            message = describe_duplicate_batch(duplicate_batch)
            return _conflict_response(message)

        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        df = read_excel_file(contents, file.filename)
    except ParserError as exc:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {exc}")

    table_type, table_type_name = _determine_table_type(file.filename, df)

    cleaner = CleanerService()
    try:
        cleaned_data, cleaner_validation = cleaner.clean_data(
            df, table_type.value, filename=file.filename
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"数据清洗失败: {exc}")

    validation, detected_store_name, meta = _convert_validation_result(
        cleaner_validation
    )
    resolved_store_name = detected_store_name or "未知门店"
    preview_rows = _to_builtin(cleaned_data[:5])
    row_count = (
        int(cleaner_validation.total_rows)
        if cleaner_validation.total_rows is not None
        else 0
    )

    # 构建解析结果
    parse_result = ParseResult(
        file_type=table_type,
        file_type_name=table_type_name,
        store_id=store_id,
        store_name=resolved_store_name,
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
        "cleaned_data": cleaned_data,
        "table_type": table_type.value,
        "store_name": resolved_store_name,
        "meta": meta,
        "created_at": datetime.now(),
        "file_hash": file_hash,
    }

    return UploadResponse(
        success=True,
        message="文件解析成功，请确认后入库",
        data=parse_result,
    )


@router.post("/confirm", response_model=UploadResponse, summary="确认入库")
async def confirm_import(
    session_id: str = Form(..., description="解析会话ID"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_admin),  # 上传需要管理员权限
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
    cleaned_data = cache.get("cleaned_data", [])
    cached_store_name = cache.get("store_name")
    table_type_value = cache.get("table_type") or (
        parse_result.file_type.value if parse_result.file_type else None
    )
    store_name = cached_store_name or parse_result.store_name
    file_hash = cache.get("file_hash")
    if not file_hash and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                file_hash = _calculate_file_hash(f.read())
                cache["file_hash"] = file_hash
        except Exception:
            file_hash = None

    if not table_type_value:
        raise HTTPException(status_code=400, detail="无法识别表类型，请重新上传文件")

    duplicate_batch = _find_success_batch_by_hash(db, file_hash)
    if duplicate_batch:
        message = describe_duplicate_batch(duplicate_batch)
        return _conflict_response(message)

    importer = ImporterService(db)
    meta = cache.get("meta") or {}

    try:
        service_result = importer.process_upload(
            file_name=os.path.basename(file_path),
            store_id=parse_result.store_id,
            table_type=table_type_value,
            cleaned_data=cleaned_data,
            biz_date=meta.get("biz_date"),
            store_name=store_name,
            payment_methods=meta.get("payment_methods"),
            file_hash=file_hash,
        )
    except DuplicateFileError as duplicate_error:
        return _conflict_response(str(duplicate_error))

    status_value = service_result.get("status", BatchStatus.FAILED.value)
    try:
        status_enum = BatchStatus(status_value)
    except ValueError:
        status_enum = BatchStatus.FAILED

    if status_enum != BatchStatus.SUCCESS:
        error_message = service_result.get("error") or "入库失败，请稍后重试"
        raise HTTPException(status_code=500, detail=error_message)

    summary = ImportSummary(
        row_count=service_result.get("row_count", 0),
        sales_total=service_result.get("sales_total"),
        actual_total=service_result.get("actual_total"),
        balance_diff_count=0,
    )

    import_result = ImportResult(
        batch_id=service_result.get("batch_id"),
        batch_no=service_result.get("batch_no") or "",
        status=status_enum,
        summary=summary,
        message=f"成功导入 {summary.row_count} 条数据",
    )

    # 清理缓存
    del _parse_cache[session_id]

    return UploadResponse(
        success=True,
        message=import_result.message,
        data=import_result,
    )


@router.delete("/cancel/{session_id}", summary="取消上传", response_model=None)
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
