"""
ETL 流程联调脚本

功能：
串联 Parser -> Cleaner 完整链路，验证数据结构是否符合下游需求。
- 供 Dev A (数据库开发) 验证入库数据格式
- 供 Dev C (前端开发) 验证校验报告格式

用法：
    python main.py                                  # 处理默认测试文件
    python main.py <file1> <file2> ...              # 处理指定文件
    python main.py --stream <file.csv>              # 流式处理模式
    python main.py --stream --chunk-size 2000 <file.csv>  # 自定义 chunk 大小

Author: Dev B (Data Specialist)
Version: 2.0 - 支持流式处理
"""

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Tuple, Optional

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

# ============================================================================
# 路径设置：确保能正确导入 app 模块
# ============================================================================

# 获取 backend 目录的绝对路径
BACKEND_DIR = Path(__file__).resolve().parent
# 将 backend 目录添加到 Python 路径
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 导入 ETL 模块
from app.services import parser, cleaner
from app.services.cleaner import (
    ETLErrorType,
    CleanerService,
    ValidationResult,
    RowError,
)
from app.services.parser import ParserError, parse_csv_stream, parse_and_validate

# ============================================================================
# 常量配置
# ============================================================================

# 大文件阈值（超过此大小自动启用流式处理，单位：字节）
LARGE_FILE_THRESHOLD = 20 * 1024 * 1024  # 20MB

# 默认流式处理的 chunk 大小
DEFAULT_CHUNK_SIZE = 5000


# ============================================================================
# JSON 序列化辅助函数
# ============================================================================


def json_encoder(obj: Any) -> Any:
    """
    自定义 JSON 序列化处理器

    处理以下类型：
    - Decimal -> float
    - datetime/date -> ISO 8601 字符串
    - bytes -> Base64 字符串（或忽略）
    - set -> list

    Args:
        obj: 需要序列化的对象

    Returns:
        Any: 可 JSON 序列化的值
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.decode("utf-8", errors="ignore")
    elif isinstance(obj, set):
        return list(obj)
    elif np is not None and isinstance(obj, np.generic):
        # 兼容 numpy.int64 / numpy.float64 等类型
        return obj.item()
    elif hasattr(obj, "dict"):
        # Pydantic 模型
        return obj.dict()
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        raise TypeError(f"无法序列化类型: {type(obj)}")


def to_json(obj: Any, indent: int = 2) -> str:
    """
    将对象转换为美化的 JSON 字符串

    Args:
        obj: 需要转换的对象
        indent: 缩进空格数

    Returns:
        str: JSON 字符串
    """
    return json.dumps(obj, default=json_encoder, ensure_ascii=False, indent=indent)


# ============================================================================
# 报表类型中文名称映射
# ============================================================================

REPORT_TYPE_NAMES = {
    "booking": "预订汇总表",
    "sales": "酒水销售分析表",
    "room": "包厢开台分析表",
    "unknown": "未知类型",
}


# ============================================================================
# 主流程函数
# ============================================================================


def process_file_full(file_path: str) -> bool:
    """
    全量处理单个文件的完整 ETL 流程

    流程：
    1. 读取文件内容
    2. 调用 Parser 解析文件
    3. 调用 Cleaner 清洗数据并校验
    4. 输出结果报告

    Args:
        file_path: 文件路径

    Returns:
        bool: 处理是否成功
    """
    print("\n" + "=" * 70)
    print(f"📂 处理文件: {file_path}")
    print("=" * 70)

    # 记录开始时间
    start_time = time.time()

    try:
        # ======== Step 0: 读取文件 ========
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            print(f"❌ 错误: 文件不存在 - {file_path}")
            return False

        filename = file_path_obj.name
        with open(file_path_obj, "rb") as f:
            file_content = f.read()

        print(f"✅ 文件读取成功，大小: {len(file_content):,} bytes")

        # ======== Step 1: Parse (解析) ========
        print("\n" + "-" * 40)
        print("【Step 1】解析文件 (Parser)")
        print("-" * 40)

        try:
            df, report_type, meta = parser.parse_and_validate(file_content, filename)
        except parser.ParserError as exc:
            print(f"❌ 解析失败: {exc}")
            return False

        print(f"✅ 解析完成")
        print(
            f"   - 报表类型: {report_type} ({REPORT_TYPE_NAMES.get(report_type, '未知')})"
        )
        print(f"   - 数据行数: {meta['row_count']}")
        print(f"   - 列数: {meta['column_count']}")
        print(f"   - 列名列表:")
        for i, col in enumerate(meta["columns"][:10], 1):
            print(f"       {i:2d}. {col}")
        if len(meta["columns"]) > 10:
            print(f"       ... 共 {len(meta['columns'])} 列 (仅显示前10列)")

        # ======== Step 2: Clean (清洗) ========
        print("\n" + "-" * 40)
        print("【Step 2】清洗数据 (Cleaner)")
        print("-" * 40)

        cleaned_data, validation_result = cleaner.clean_and_validate(
            df, report_type, filename=filename, detected_date=meta.get("detected_date")
        )

        # 计算耗时
        elapsed_time = time.time() - start_time

        print(f"✅ 清洗完成")
        print(f"   - 清洗后行数: {len(cleaned_data)}")
        print(f"   - 校验通过: {'是 ✅' if validation_result.is_valid else '否 ❌'}")
        print(f"   - 错误数量: {validation_result.error_count}")

        # ======== 输出结果 (JSON 格式) ========
        print("\n" + "-" * 40)
        print("【输出结果】JSON 格式报告")
        print("-" * 40)

        # 1. 基本信息
        basic_info = {
            "filename": filename,
            "report_type": report_type,
            "report_type_name": REPORT_TYPE_NAMES.get(report_type, "未知"),
            "elapsed_time_ms": round(elapsed_time * 1000, 2),
            "row_count": len(cleaned_data),
            "column_count": meta["column_count"],
        }

        print("\n📋 基本信息:")
        print(to_json(basic_info))

        # 2. 清洗数据抽样 (前2条)
        sample_data = cleaned_data[:2] if cleaned_data else []

        print("\n📋 清洗数据抽样 (前2条):")
        print(to_json(sample_data))

        # 3. 校验报告
        validation_report = {
            "is_valid": validation_result.is_valid,
            "summary": validation_result.summary,
            "errors_preview": [
                {
                    "row_index": err.row_index,
                    "column": err.column,
                    "message": err.message,
                    "raw_data": err.raw_data,
                }
                for err in validation_result.errors[:3]  # 前3个错误
            ],
            "total_error_count": validation_result.error_count,
        }

        print("\n📋 校验报告:")
        print(to_json(validation_report))

        # 4. 数据结构说明 (给下游开发者参考)
        if cleaned_data:
            first_record = cleaned_data[0]
            field_types = {}
            for key, value in first_record.items():
                if value is None:
                    field_types[key] = "null"
                elif isinstance(value, dict):
                    field_types[key] = "object (JSON)"
                elif isinstance(value, float):
                    field_types[key] = "number (float)"
                elif isinstance(value, int):
                    field_types[key] = "number (int)"
                elif isinstance(value, str):
                    field_types[key] = "string"
                else:
                    field_types[key] = type(value).__name__

            print("\n📋 字段类型说明 (供 Dev A 参考):")
            print(to_json(field_types))

        print("\n" + "-" * 40)
        print(f"⏱️ 处理耗时: {elapsed_time * 1000:.2f} ms")
        print("-" * 40)

        return True

    except Exception as e:
        # 异常处理：打印错误堆栈
        elapsed_time = time.time() - start_time
        print(f"\n❌ 处理失败: {e}")
        print("\n📋 错误堆栈:")
        traceback.print_exc()
        print(f"\n⏱️ 处理耗时 (失败): {elapsed_time * 1000:.2f} ms")

        return False


def process_file_stream(file_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> bool:
    """
    流式处理单个 CSV 文件的 ETL 流程

    适用于大文件（>50MB）的 CSV 处理，避免内存溢出。
    通过生成器分块读取和处理数据。

    流程：
    1. 读取文件内容
    2. 使用 parse_csv_stream 分块解析
    3. 对每个 chunk 调用 Cleaner 清洗
    4. 累加统计信息并输出报告

    Args:
        file_path: 文件路径
        chunk_size: 每个 chunk 的行数（默认 5000）

    Returns:
        bool: 处理是否成功
    """
    print("\n" + "=" * 70)
    print(f"📂 处理文件: {file_path}")
    print(f"🚀 模式: 流式处理 (Stream Mode)")
    print(f"📦 Chunk 大小: {chunk_size} 行")
    print("=" * 70)

    # 记录开始时间
    start_time = time.time()

    try:
        # ======== Step 0: 读取文件 ========
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            print(f"❌ 错误: 文件不存在 - {file_path}")
            return False

        # 验证文件类型
        filename = file_path_obj.name
        if not filename.lower().endswith(".csv"):
            print(f"❌ 错误: 流式处理仅支持 CSV 文件，当前文件: {filename}")
            print("   💡 提示: 请移除 --stream 参数使用全量处理模式")
            return False

        with open(file_path_obj, "rb") as f:
            file_content = f.read()

        file_size_mb = len(file_content) / (1024 * 1024)
        print(
            f"✅ 文件读取成功，大小: {len(file_content):,} bytes ({file_size_mb:.2f} MB)"
        )

        # ======== Step 1: 初始化服务 ========
        cleaner_service = CleanerService()

        # ======== Step 2: 获取流式生成器 ========
        print("\n" + "-" * 40)
        print("【开始流式处理】")
        print("-" * 40)

        try:
            stream = parse_csv_stream(file_content, filename, chunk_size=chunk_size)
        except ParserError as exc:
            print(f"❌ 解析失败: {exc}")
            return False

        # ======== Step 3: 循环处理每个 Chunk ========
        total_rows = 0
        total_cleaned_rows = 0
        all_errors: List[RowError] = []
        all_warnings: List[RowError] = []
        report_type: Optional[str] = None
        chunk_stats: List[dict] = []

        for chunk_idx, (df_chunk, meta) in enumerate(stream):
            chunk_start_time = time.time()

            # 获取报表类型（仅第一个 chunk）
            if report_type is None:
                report_type = meta["report_type"]
                print(
                    f"✅ 报表类型: {report_type} ({REPORT_TYPE_NAMES.get(report_type, '未知')})"
                )
                print()

            # 调用 Cleaner 清洗当前 Chunk
            cleaned_data, validation_result = cleaner_service.clean_data(
                df_chunk,
                meta["report_type"],
                filename=filename,
                detected_date=meta.get("detected_date"),
            )

            chunk_elapsed = time.time() - chunk_start_time

            # 累加统计信息
            chunk_rows = meta["chunk_rows"]
            total_rows += chunk_rows
            total_cleaned_rows += len(cleaned_data)

            # 收集错误和警告（修正行号为全局索引）
            chunk_error_count = 0
            chunk_warning_count = 0
            for error in validation_result.errors:
                # 修正行号：全局行号 = 当前块之前的行数 + 块内行号
                if error.row_index != -1:
                    error.row_index += chunk_idx * chunk_size

                # 分离错误和警告
                if error.severity == "warning":
                    all_warnings.append(error)
                    chunk_warning_count += 1
                else:
                    all_errors.append(error)
                    chunk_error_count += 1

            # 记录 chunk 统计
            chunk_stat = {
                "chunk_idx": chunk_idx + 1,
                "rows": chunk_rows,
                "cleaned_rows": len(cleaned_data),
                "errors": chunk_error_count,
                "warnings": chunk_warning_count,
                "elapsed_ms": round(chunk_elapsed * 1000, 2),
            }
            chunk_stats.append(chunk_stat)

            # 输出 chunk 进度
            status_icon = "✅" if chunk_error_count == 0 else "⚠️"
            print(
                f"  {status_icon} Chunk {chunk_idx + 1}: "
                f"处理 {chunk_rows} 行 -> {len(cleaned_data)} 行, "
                f"错误: {chunk_error_count}, 警告: {chunk_warning_count}, "
                f"耗时: {chunk_elapsed * 1000:.1f}ms"
            )

        # ======== Step 4: 输出最终汇总报告 ========
        elapsed_time = time.time() - start_time

        print("\n" + "-" * 40)
        print("【流式处理完成】汇总报告")
        print("-" * 40)

        # 基本信息
        summary_info = {
            "filename": filename,
            "mode": "stream",
            "report_type": report_type,
            "report_type_name": REPORT_TYPE_NAMES.get(report_type, "未知"),
            "chunk_size": chunk_size,
            "total_chunks": len(chunk_stats),
            "total_rows": total_rows,
            "total_cleaned_rows": total_cleaned_rows,
            "total_errors": len(all_errors),
            "total_warnings": len(all_warnings),
            "elapsed_time_ms": round(elapsed_time * 1000, 2),
            "throughput_rows_per_sec": (
                round(total_rows / elapsed_time, 2) if elapsed_time > 0 else 0
            ),
        }

        print("\n📋 处理汇总:")
        print(to_json(summary_info))

        # 错误预览（前 5 个）
        if all_errors:
            print("\n📋 错误预览 (前 5 个):")
            error_preview = [
                {
                    "row_index": err.row_index,
                    "column": err.column,
                    "error_type": (
                        err.error_type.value
                        if hasattr(err.error_type, "value")
                        else str(err.error_type)
                    ),
                    "message": err.message,
                }
                for err in all_errors[:5]
            ]
            print(to_json(error_preview))

            if len(all_errors) > 5:
                print(f"   ... 还有 {len(all_errors) - 5} 个错误未显示")

        # 警告预览（前 3 个）
        if all_warnings:
            print("\n📋 警告预览 (前 3 个):")
            warning_preview = [
                {
                    "row_index": err.row_index,
                    "column": err.column,
                    "message": err.message,
                }
                for err in all_warnings[:3]
            ]
            print(to_json(warning_preview))

            if len(all_warnings) > 3:
                print(f"   ... 还有 {len(all_warnings) - 3} 个警告未显示")

        # 最终状态
        print("\n" + "-" * 40)
        if len(all_errors) == 0:
            print(
                f"✅ 处理完成。总行数: {total_rows}, 清洗后: {total_cleaned_rows}, 无错误"
            )
        else:
            print(
                f"⚠️ 处理完成。总行数: {total_rows}, 清洗后: {total_cleaned_rows}, "
                f"错误: {len(all_errors)}, 警告: {len(all_warnings)}"
            )
        print(f"⏱️ 总耗时: {elapsed_time * 1000:.2f} ms")
        print("-" * 40)

        return True

    except Exception as e:
        # 异常处理：打印错误堆栈
        elapsed_time = time.time() - start_time
        print(f"\n❌ 流式处理失败: {e}")
        print("\n📋 错误堆栈:")
        traceback.print_exc()
        print(f"\n⏱️ 处理耗时 (失败): {elapsed_time * 1000:.2f} ms")

        return False


def process_file(
    file_path: str,
    stream_mode: bool = False,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    auto_stream_threshold: int = LARGE_FILE_THRESHOLD,
) -> bool:
    """
    处理单个文件（自动选择全量或流式模式）

    决策逻辑：
    1. 如果 stream_mode=True 且为 CSV 文件，使用流式处理
    2. 如果文件大小 > auto_stream_threshold 且为 CSV 文件，自动启用流式处理
    3. 否则使用全量处理

    Args:
        file_path: 文件路径
        stream_mode: 是否强制使用流式模式
        chunk_size: 流式处理的 chunk 大小
        auto_stream_threshold: 自动启用流式处理的文件大小阈值（字节）

    Returns:
        bool: 处理是否成功
    """
    file_path_obj = Path(file_path)
    is_csv = file_path_obj.suffix.lower() == ".csv"

    # 检查是否需要使用流式处理
    use_stream = False
    if stream_mode and is_csv:
        use_stream = True
    elif is_csv and file_path_obj.exists():
        file_size = file_path_obj.stat().st_size
        if file_size > auto_stream_threshold:
            use_stream = True
            print(
                f"💡 自动启用流式处理 (文件大小 {file_size / (1024*1024):.2f} MB > {auto_stream_threshold / (1024*1024):.0f} MB 阈值)"
            )

    if use_stream:
        return process_file_stream(file_path, chunk_size=chunk_size)
    else:
        return process_file_full(file_path)


def get_default_test_files() -> List[str]:
    """
    获取默认测试文件列表

    Returns:
        List[str]: 测试文件路径列表
    """
    # 项目根目录
    project_root = BACKEND_DIR.parent
    docs_dir = project_root / "docs"

    test_files = []

    # 优先使用官方样例 XLSX 文件
    xlsx_patterns = [
        "预订汇总*.xlsx",
        "酒水销售*.xlsx",
        "包厢开台*.xlsx",
    ]

    for pattern in xlsx_patterns:
        matched_files = sorted(docs_dir.glob(pattern))
        for file_path in matched_files:
            test_files.append(str(file_path))
            if len(test_files) >= 3:
                break
        if len(test_files) >= 3:
            break

    # 兜底：使用所有 XLSX 文件
    if not test_files:
        xlsx_files = sorted(docs_dir.glob("*.xlsx"))
        test_files = [str(f) for f in xlsx_files[:3]]

    # 最后兜底：使用 CSV 文件
    if not test_files:
        csv_patterns = [
            "副本预订汇总.csv",
            "副本酒水销售分析.csv",
            "副本包厢开台分析.csv",
        ]
        for pattern in csv_patterns:
            file_path = docs_dir / pattern
            if file_path.exists():
                test_files.append(str(file_path))

    return test_files


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数

    Returns:
        argparse.Namespace: 解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        description="KTV 报表系统 - ETL 联调脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                                  # 处理默认测试文件
  python main.py data1.xlsx data2.csv             # 处理指定文件
  python main.py --stream large_data.csv          # 强制流式处理
  python main.py --stream --chunk-size 2000 *.csv # 自定义 chunk 大小
  python main.py --auto-stream-threshold 10       # 设置自动流式阈值为 10MB

注意:
  - 流式处理模式 (--stream) 仅支持 CSV 文件
  - Excel 文件由于格式限制，始终使用全量处理模式
  - 当 CSV 文件大小超过阈值时，会自动启用流式处理
        """,
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="要处理的文件路径列表（不指定则使用默认测试文件）",
    )

    parser.add_argument(
        "--stream",
        action="store_true",
        help="强制启用流式处理模式（仅限 CSV 文件）",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        metavar="N",
        help=f"流式处理时每个 chunk 的行数（默认: {DEFAULT_CHUNK_SIZE}）",
    )

    parser.add_argument(
        "--auto-stream-threshold",
        type=float,
        default=LARGE_FILE_THRESHOLD / (1024 * 1024),
        metavar="MB",
        help=f"自动启用流式处理的文件大小阈值（MB，默认: {LARGE_FILE_THRESHOLD / (1024 * 1024):.0f}）",
    )

    parser.add_argument(
        "--no-auto-stream",
        action="store_true",
        help="禁用自动流式处理（即使大文件也使用全量模式）",
    )

    return parser.parse_args()


def main():
    """
    主入口函数
    """
    # 解析命令行参数
    args = parse_arguments()

    print("\n" + "=" * 70)
    print("🚀 KTV 报表系统 - ETL 联调脚本")
    print("=" * 70)
    print("功能: 验证 Parser -> Cleaner 完整链路")
    print("输出: JSON 格式的清洗数据和校验报告")

    # 显示运行模式
    if args.stream:
        print(f"模式: 流式处理 (强制), Chunk 大小: {args.chunk_size} 行")
    elif args.no_auto_stream:
        print("模式: 全量处理 (禁用自动流式)")
    else:
        print(
            f"模式: 自动 (大于 {args.auto_stream_threshold:.0f}MB 的 CSV 文件启用流式处理)"
        )

    print("=" * 70)

    # 获取待处理的文件列表
    if args.files:
        files_to_process = args.files
        print(f"\n📁 待处理文件 (命令行指定): {len(files_to_process)} 个")
    else:
        # 使用默认测试文件
        files_to_process = get_default_test_files()
        if not files_to_process:
            print("\n⚠️ 未找到默认测试文件，请通过命令行参数指定文件:")
            print("   python main.py <file1> <file2> ...")
            print("   python main.py --help  # 查看帮助")
            return
        print(f"\n📁 待处理文件 (默认): {len(files_to_process)} 个")

    for file_path in files_to_process:
        print(f"   - {file_path}")

    # 计算自动流式处理阈值（转换为字节）
    auto_threshold = int(args.auto_stream_threshold * 1024 * 1024)
    if args.no_auto_stream:
        # 禁用自动流式处理：设置一个极大的阈值
        auto_threshold = float("inf")

    # 处理每个文件
    success_count = 0
    fail_count = 0

    for file_path in files_to_process:
        try:
            success = process_file(
                file_path,
                stream_mode=args.stream,
                chunk_size=args.chunk_size,
                auto_stream_threshold=auto_threshold,
            )
            if success:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"\n❌ 文件处理异常: {file_path}")
            traceback.print_exc()
            fail_count += 1

    # 输出汇总
    print("\n" + "=" * 70)
    print("📊 处理汇总")
    print("=" * 70)
    print(f"   总文件数: {len(files_to_process)}")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")
    print("=" * 70)
    print("\n✅ ETL 联调脚本执行完毕\n")


# ============================================================================
# 脚本入口
# ============================================================================

if __name__ == "__main__":
    main()
