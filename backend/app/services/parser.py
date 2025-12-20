"""
Excel/CSV 通用解析服务

功能：
1. 智能定位标题行（支持多行文件头，基于关键词密度评分）
2. 处理多级表头（合并单元格 Forward Fill + 扁平化）
3. 数据清理（去空行、过滤合计行）
4. 内存优化（类型降级、Category 转换）
5. 流式处理（大文件 CSV 分块读取）

Author: Dev B (Data Specialist)
"""

import io
import re
import numpy as np
from typing import Union, Optional, List, Tuple, Iterator
from zipfile import BadZipFile

import pandas as pd
from pandas.errors import EmptyDataError, ParserError as PandasParserError


# 用于识别表头的关键词列表
HEADER_KEYWORDS = [
    "实收金额",
    "开台单号",
    "酒水名称",
    "账单合计",
    "门店名称",
    "包厢名称",
    "订位人",
]


class ParserError(ValueError):
    """Parser 模块统一异常"""

    pass


def _normalize_text_for_match(text: str) -> str:
    """
    将文本标准化用于关键词匹配：
    - 转小写
    - 去除空白、标点和下划线
    """
    return re.sub(r"[\s\W_]+", "", str(text).lower())


def _extract_date_from_preview_df(preview_df: pd.DataFrame) -> Optional[str]:
    """
    从预览数据（前 N 行）中提取日期
    """
    # 匹配 2025-12-20, 2025.12.20, 2025/12/20 等
    # 以及 20251220
    patterns = [
        r"(20\d{2}[-./]\d{1,2}[-./]\d{1,2})",
        r"(20\d{2}年\d{1,2}月\d{1,2}日)",
    ]

    for row_idx in range(len(preview_df)):
        row_values = preview_df.iloc[row_idx].astype(str).tolist()
        row_text = " ".join(row_values)

        for pattern in patterns:
            match = re.search(pattern, row_text)
            if match:
                date_str = match.group(1)
                # 标准化处理
                date_str = (
                    date_str.replace("年", "-")
                    .replace("月", "-")
                    .replace("日", "")
                    .replace(".", "-")
                    .replace("/", "-")
                )
                try:
                    parts = date_str.split("-")
                    if len(parts) == 3:
                        return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                except:
                    continue
    return None


def find_header_row(file_content: bytes, filename: str, max_rows: int = 20) -> Tuple[int, Optional[str]]:
    """
    智能定位标题行索引（基于关键词密度评分机制）并提取潜在日期

    算法：
    1. 遍历前 N 行，对每一行计算包含 HEADER_KEYWORDS 的关键词数量（Match Count）
    2. 选择匹配关键词数量最多的行作为 Header Row
    3. 如果有多行得分相同且最高，选择行号最小的那个
    4. 在前 N 行中搜索日期信息
    5. 如果最高分为 0，抛出 ParserError

    Args:
        file_content: 文件二进制内容
        filename: 文件名（用于判断文件类型）
        max_rows: 搜索的最大行数（默认 20 行）

    Returns:
        Tuple[int, Optional[str]]: (标题行索引, 检测到的日期)

    Raises:
        ParserError: 无法识别表头
    """
    # 根据文件类型读取前 N 行
    file_stream = io.BytesIO(file_content)

    if filename.lower().endswith(".csv"):
        # CSV：直接按行解码，避免列数不一致导致的行被跳过
        try:
            encoding = _detect_csv_encoding(file_content)
        except ParserError:
            raise

        try:
            # 解码并保留空行，便于行号对应
            text = file_content.decode(encoding, errors="ignore")
        except UnicodeError as exc:
            raise ParserError("无法识别文件编码") from exc

        # 只取前 max_rows 行进行评分
        lines = text.splitlines()
        if len(lines) == 0:
            raise ParserError("空文件无法解析")

        preview_lines = lines[:max_rows]
        preview_df = pd.DataFrame(preview_lines)
    else:
        # Excel 文件
        try:
            file_stream.seek(0)
            preview_df = pd.read_excel(
                file_stream, nrows=max_rows, header=None, engine="openpyxl"
            )
        except (ValueError, BadZipFile, OSError) as exc:
            raise ParserError(f"无法读取 Excel 文件: {exc}") from exc

    # 提取日期
    detected_date = _extract_date_from_preview_df(preview_df)

    # 预先标准化关键词，避免重复处理
    normalized_keywords = [_normalize_text_for_match(k) for k in HEADER_KEYWORDS]

    # 基于关键词密度评分机制定位表头
    row_scores: List[Tuple[int, int]] = []  # (row_index, score)

    for row_idx in range(len(preview_df)):
        if filename.lower().endswith(".csv"):
            # DataFrame 每行只有一个单元格（原始行文本）
            row_raw = preview_df.iloc[row_idx, 0]
            row_text = _normalize_text_for_match(row_raw)
        else:
            row_values = preview_df.iloc[row_idx].tolist()
            # 标准化行文本，去除空白/标点/BOM 等干扰
            row_text = "".join(_normalize_text_for_match(val) for val in row_values)

        # 计算该行匹配的关键词数量
        match_count = 0
        for normalized_keyword in normalized_keywords:
            if normalized_keyword and normalized_keyword in row_text:
                match_count += 1

        row_scores.append((row_idx, match_count))

    # 找到最高分
    max_score = max(score for _, score in row_scores)

    # 如果最高分为 0，说明没有命中任何关键词
    if max_score == 0:
        raise ParserError(f"无法识别表头，未找到关键词: {HEADER_KEYWORDS}")

    # 选择得分最高的行（如果有多个同分，选行号最小的）
    for row_idx, score in row_scores:
        if score == max_score:
            return row_idx, detected_date

    # 理论上不会走到这里
    return 0, detected_date


def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    优化 DataFrame 内存占用

    优化策略：
    1. Category 转换：对 object 类型列，如果 unique_count / total_count < 0.5，转换为 category
    2. 数值降级：int64 -> int32（如果范围允许），float64 -> float32

    Args:
        df: 输入 DataFrame

    Returns:
        pd.DataFrame: 内存优化后的 DataFrame
    """
    if len(df) == 0:
        return df

    # 创建副本避免修改原始数据
    df = df.copy()

    for col in df.columns:
        col_dtype = df[col].dtype

        # 1. 处理 object (字符串) 类型列 -> Category
        if col_dtype == "object":
            # 计算唯一值比例
            unique_count = df[col].nunique()
            total_count = len(df)

            # 重复率高于 50% 时转换为 category
            if total_count > 0 and unique_count / total_count <= 0.5:
                df[col] = df[col].astype("category")

        # 2. 处理 int64 类型列 -> int32
        elif col_dtype == np.int64:
            col_min = df[col].min()
            col_max = df[col].max()

            # int32 范围: -2147483648 到 2147483647
            if col_min >= np.iinfo(np.int32).min and col_max <= np.iinfo(np.int32).max:
                df[col] = df[col].astype(np.int32)

        # 3. 处理 float64 类型列 -> float32
        elif col_dtype == np.float64:
            # float32 精度对于金额计算通常足够（约7位有效数字）
            df[col] = df[col].astype(np.float32)

    return df


def _detect_multi_level_header(
    file_content: bytes, filename: str, header_row_index: int
) -> bool:
    """
    检测是否为多级表头

    Args:
        file_content: 文件二进制内容
        filename: 文件名
        header_row_index: 主表头行索引

    Returns:
        bool: 是否为多级表头
    """
    file_stream = io.BytesIO(file_content)

    if filename.lower().endswith(".csv"):
        for encoding in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
            try:
                file_stream.seek(0)
                # 读取主表头行和下一行
                preview_df = pd.read_csv(
                    file_stream,
                    skiprows=range(0, header_row_index),
                    nrows=2,
                    header=None,
                    encoding=encoding,
                    on_bad_lines="skip",
                )
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return False
    else:
        preview_df = pd.read_excel(
            file_stream,
            skiprows=range(0, header_row_index),
            nrows=2,
            header=None,
            engine="openpyxl",
        )

    if len(preview_df) < 2:
        return False

    # 获取第二行（潜在的子表头行）
    second_row = preview_df.iloc[1]

    # 检查第二行是否有非空值，且不是明显的数据行
    non_empty_count = second_row.notna().sum()
    if non_empty_count == 0:
        return False

    # 检查第二行的值是否像表头（非数字为主）
    text_values = 0
    numeric_values = 0
    for val in second_row.dropna():
        val_str = str(val).strip()
        if val_str:
            # 尝试判断是否为数字
            try:
                float(val_str.replace(",", "").replace("¥", ""))
                numeric_values += 1
            except ValueError:
                # 检查是否像表头关键词
                if re.match(r"^[a-zA-Z\u4e00-\u9fa5_\-\s]+$", val_str):
                    text_values += 1

    # 如果文本值占多数，认为是多级表头
    return text_values > numeric_values


def _flatten_multi_index_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    将 MultiIndex 列名扁平化

    规则：
    - (parent, child) -> "parent_child"
    - 如果 child 是 Unnamed 或空 -> "parent"
    - 对父级进行 Forward Fill 处理合并单元格

    Args:
        df: 带有 MultiIndex 列的 DataFrame

    Returns:
        pd.DataFrame: 扁平化列名后的 DataFrame
    """
    if not isinstance(df.columns, pd.MultiIndex):
        # 不是多级索引，直接清理列名
        df.columns = [str(col).strip() for col in df.columns]
        return df

    # 1. 提取所有层级
    n_levels = df.columns.nlevels
    levels = [df.columns.get_level_values(i).tolist() for i in range(n_levels)]

    # 2. 对第一层（父标题）进行 Forward Fill
    # 处理合并单元格读取为 NaN 的问题
    if n_levels > 1:
        filled_level_0 = []
        last_valid = None
        for val in levels[0]:
            if pd.isna(val) or str(val).strip() == "":
                filled_level_0.append(last_valid)
            else:
                val_str = str(val).strip()
                # 检查是否为 Unnamed 列
                if "Unnamed" in val_str:
                    filled_level_0.append(last_valid)
                else:
                    last_valid = val_str
                    filled_level_0.append(val_str)
        levels[0] = filled_level_0

    # 3. 扁平化列名
    new_columns = []
    for i in range(len(df.columns)):
        if n_levels == 1:
            new_columns.append(str(levels[0][i]).strip())
        else:
            parent = levels[0][i] if levels[0][i] is not None else ""
            child = levels[1][i] if len(levels) > 1 else ""

            # 转换为字符串并清理
            parent_str = str(parent).strip() if parent is not None else ""
            child_str = str(child).strip() if child is not None else ""

            # 判断是否需要合并
            child_is_empty = pd.isna(child) or child_str == "" or "Unnamed" in child_str

            if child_is_empty:
                new_columns.append(parent_str)
            else:
                # 合并父子标题
                new_columns.append(f"{parent_str}_{child_str}")

    df.columns = new_columns
    return df


def _clean_dataframe(df: pd.DataFrame, filter_summary: bool = True) -> pd.DataFrame:
    """
    清理 DataFrame

    操作：
    1. 去除全为空的行
    2. 去除列名前后空格
    3. (可选) 过滤合计行

    Args:
        df: 输入 DataFrame
        filter_summary: 是否过滤合计行

    Returns:
        pd.DataFrame: 清理后的 DataFrame
    """
    # 1. 去除列名前后空格（处理可能的空白）
    df.columns = [str(col).strip() for col in df.columns]

    # 2. 去除全为空的行
    df = df.dropna(how="all")

    # 3. 过滤合计行
    if filter_summary and len(df) > 0:
        # 获取第一列名称
        first_col = df.columns[0]

        # 过滤掉第一列包含"合计"的行
        mask = df[first_col].astype(str).str.contains("合计", na=False)
        df = df[~mask]

    # 重置索引
    df = df.reset_index(drop=True)

    return df


def _remove_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    移除全为空的列和重复的空列名

    Args:
        df: 输入 DataFrame

    Returns:
        pd.DataFrame: 清理后的 DataFrame
    """
    # 移除全为空的列
    df = df.dropna(axis=1, how="all")

    # 处理可能的空列名或重复列名
    new_columns = []
    seen = {}
    for col in df.columns:
        col_str = str(col).strip()
        if col_str == "" or col_str == "nan":
            col_str = "unnamed_col"

        # 处理重复列名
        if col_str in seen:
            seen[col_str] += 1
            col_str = f"{col_str}_{seen[col_str]}"
        else:
            seen[col_str] = 0

        new_columns.append(col_str)

    df.columns = new_columns
    return df


def _detect_csv_encoding(file_content: bytes) -> str:
    """
    检测 CSV 文件编码

    Args:
        file_content: 文件二进制内容

    Returns:
        str: 检测到的编码名称

    Raises:
        ParserError: 无法识别编码
    """
    file_stream = io.BytesIO(file_content)

    for encoding in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
        try:
            file_stream.seek(0)
            pd.read_csv(
                file_stream,
                nrows=5,
                header=None,
                encoding=encoding,
                on_bad_lines="skip",
            )
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
        except EmptyDataError as exc:
            raise ParserError("空文件无法解析") from exc

    raise ParserError("无法识别 CSV 文件编码")


def read_excel_file(
    contents: bytes, filename: str, filter_summary: bool = True
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    读取 Excel 或 CSV 文件流，自动识别多级表头并扁平化

    Args:
        contents: 文件二进制内容
        filename: 文件名 (用于判断是 csv 还是 xlsx)
        filter_summary: 是否过滤合计行（默认 True）

    Returns:
        Tuple[pd.DataFrame, Optional[str]]: (清洗后的 DataFrame, 检测到的日期)

    Raises:
        ParserError: 无法识别表头或文件格式错误
    """
    try:
        # Step A: 智能定位标题行
        header_row_index, detected_date = find_header_row(contents, filename)

        # Step B: 检测是否为多级表头
        is_multi_level = _detect_multi_level_header(
            contents, filename, header_row_index
        )

        # 准备读取参数
        file_stream = io.BytesIO(contents)

        if is_multi_level:
            # 使用两行作为表头
            header_rows = [header_row_index, header_row_index + 1]
        else:
            # 单行表头
            header_rows = header_row_index

        # 读取文件
        if filename.lower().endswith(".csv"):
            # CSV 文件：尝试多种编码
            df = None
            for encoding in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
                try:
                    file_stream.seek(0)
                    df = pd.read_csv(
                        file_stream,
                        header=header_rows,
                        encoding=encoding,
                        on_bad_lines="skip",
                        low_memory=False,
                    )
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
                except (EmptyDataError, PandasParserError) as exc:
                    raise ParserError(f"解析 CSV 文件失败: {exc}") from exc

            if df is None:
                raise ParserError("无法识别 CSV 文件编码")
        else:
            # Excel 文件
            try:
                file_stream.seek(0)
                df = pd.read_excel(file_stream, header=header_rows, engine="openpyxl")
            except (ValueError, BadZipFile, OSError) as exc:
                raise ParserError(f"无法读取 Excel 文件: {exc}") from exc
    except ParserError:
        raise
    except (EmptyDataError, PandasParserError, ValueError, BadZipFile, OSError) as exc:
        raise ParserError(f"解析文件失败: {exc}") from exc

    # Step B2: 扁平化多级表头
    df = _flatten_multi_index_columns(df)

    # Step C: 数据清理
    df = _clean_dataframe(df, filter_summary=filter_summary)

    # 移除空列
    df = _remove_empty_columns(df)

    # Step D: 内存优化
    df = optimize_dataframe(df)

    return df, detected_date


def detect_report_type(df: pd.DataFrame, filename: str = "") -> str:
    """
    根据 DataFrame 列名或文件名检测报表类型

    Args:
        df: 解析后的 DataFrame
        filename: 文件名（可选）

    Returns:
        str: 报表类型 ('booking', 'room', 'sales', 'unknown')
    """
    columns_str = " ".join(str(col) for col in df.columns)
    filename_lower = filename.lower()

    # 预订汇总特征
    if "订位人" in columns_str or "订台数" in columns_str or "预订" in filename_lower:
        return "booking"

    # 包厢开台特征
    if (
        "开台单号" in columns_str
        or "包厢名称" in columns_str
        or "包厢" in filename_lower
    ):
        return "room"

    # 酒水销售特征
    if (
        "酒水名称" in columns_str
        or "类别名称" in columns_str
        or "酒水" in filename_lower
    ):
        return "sales"

    return "unknown"


def parse_csv_stream(
    contents: bytes, filename: str, chunk_size: int = 5000
) -> Iterator[Tuple[pd.DataFrame, dict]]:
    """
    CSV 流式解析生成器，用于处理大文件

    适用场景：大于 20MB 的 CSV 文件，避免一次性加载导致 OOM。

    Args:
        contents: 文件二进制内容
        filename: 文件名
        chunk_size: 每个 chunk 的行数（默认 5000 行）

    Yields:
        Tuple[pd.DataFrame, dict]:
            - DataFrame: 当前 chunk 的数据（已清洗、已优化）
            - dict: 元信息，包含 report_type, chunk_rows, chunk_index

    Raises:
        ParserError: 文件解析错误
    """
    # 验证文件类型
    if not filename.lower().endswith(".csv"):
        raise ParserError(
            "parse_csv_stream 仅支持 CSV 文件，Excel 文件请使用 read_excel_file"
        )

    # Step 1: 检测编码
    encoding = _detect_csv_encoding(contents)

    # Step 2: 定位表头位置
    header_row_index, detected_date = find_header_row(contents, filename)

    # Step 3: 检测是否为多级表头
    is_multi_level = _detect_multi_level_header(contents, filename, header_row_index)

    if is_multi_level:
        header_rows = [header_row_index, header_row_index + 1]
    else:
        header_rows = header_row_index

    # Step 4: 首次读取一小部分数据以检测报表类型
    file_stream = io.BytesIO(contents)
    preview_df = pd.read_csv(
        file_stream,
        header=header_rows,
        encoding=encoding,
        nrows=10,
        on_bad_lines="skip",
    )
    preview_df = _flatten_multi_index_columns(preview_df)
    report_type = detect_report_type(preview_df, filename)

    # Step 5: 使用 chunksize 分块读取
    file_stream = io.BytesIO(contents)
    chunk_reader = pd.read_csv(
        file_stream,
        header=header_rows,
        encoding=encoding,
        chunksize=chunk_size,
        on_bad_lines="skip",
        low_memory=False,
    )

    chunk_index = 0
    for df_chunk in chunk_reader:
        # 扁平化多级表头（保持逻辑一致）
        df_chunk = _flatten_multi_index_columns(df_chunk)

        # 数据清理
        df_chunk = _clean_dataframe(df_chunk, filter_summary=True)

        # 移除空列
        df_chunk = _remove_empty_columns(df_chunk)

        # 内存优化
        df_chunk = optimize_dataframe(df_chunk)

        # 生成元信息
        meta_info = {
            "report_type": report_type,
            "chunk_index": chunk_index,
            "chunk_rows": len(df_chunk),
            "columns": list(df_chunk.columns),
            "detected_date": detected_date,
        }

        yield df_chunk, meta_info
        chunk_index += 1


def parse_and_validate(
    contents: bytes, filename: str
) -> Tuple[pd.DataFrame, str, dict]:
    """
    解析文件并返回基本验证信息

    便捷函数，整合解析和类型检测

    Args:
        contents: 文件二进制内容
        filename: 文件名

    Returns:
        Tuple[pd.DataFrame, str, dict]:
            - DataFrame: 解析后的数据
            - str: 报表类型
            - dict: 解析元信息
    """
    # 解析文件
    df, detected_date = read_excel_file(contents, filename)

    # 检测类型
    report_type = detect_report_type(df, filename)

    # 生成元信息
    meta = {
        "filename": filename,
        "report_type": report_type,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "detected_date": detected_date,
    }

    return df, report_type, meta


# ============== 测试入口 ==============
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python parser.py <文件路径> [--stream]")
        print("  --stream: 使用流式处理模式（仅限 CSV）")
        sys.exit(1)

    file_path = sys.argv[1]
    use_stream = "--stream" in sys.argv

    with open(file_path, "rb") as f:
        content = f.read()

    filename = file_path.split("/")[-1].split("\\")[-1]

    try:
        if use_stream and filename.lower().endswith(".csv"):
            # 流式处理模式
            print(f"\n{'='*60}")
            print(f"文件: {filename}")
            print(f"模式: 流式处理 (Stream Mode)")
            print(f"{'='*60}")

            total_rows = 0
            for df_chunk, meta in parse_csv_stream(content, filename, chunk_size=2000):
                total_rows += meta["chunk_rows"]
                print(f"\nChunk {meta['chunk_index']}: {meta['chunk_rows']} 行")
                print(f"  报表类型: {meta['report_type']}")
                print(
                    f"  内存占用: {df_chunk.memory_usage(deep=True).sum() / 1024:.2f} KB"
                )

            print(f"\n总计处理: {total_rows} 行")
            print(f"{'='*60}\n")
        else:
            # 全量处理模式
            df, report_type, meta = parse_and_validate(content, filename)

            print(f"\n{'='*60}")
            print(f"文件: {filename}")
            print(f"模式: 全量处理")
            print(f"报表类型: {report_type}")
            print(f"检测到日期: {meta.get('detected_date', '未找到')}")
            print(f"行数: {meta['row_count']}")
            print(f"列数: {meta['column_count']}")
            print(f"内存占用: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")
            print(f"\n列名列表:")
            for i, col in enumerate(meta["columns"], 1):
                print(f"  {i:2d}. {col}")

            print(f"\n前 3 行数据预览:")
            print(df.head(3).to_string())
            print(f"{'='*60}\n")

    except Exception as e:
        print(f"解析失败: {e}")
        sys.exit(1)
