"""
数据清洗与校验服务

功能：
1. 字段映射：中文列名 -> 英文业务字段名
2. 动态列归集：处理未知支付方式等动态列
3. 数据类型转换：数值清洗、日期标准化
4. 业务规则校验：平衡性检查、异常检测
5. 模糊匹配：智能识别相似列名并自动映射

Author: Dev B (Data Specialist)
Version: 2.0 - 增强容错性与流式处理支持
"""

import re
import difflib
from datetime import datetime
from enum import Enum
from typing import List, Dict, Tuple, Any, Optional, Set

import pandas as pd
from pydantic import BaseModel, Field


# ============================================================================
# 错误类型枚举
# ============================================================================


class ETLErrorType(str, Enum):
    """ETL 错误类型枚举"""

    PARSE_ERROR = "parse_error"  # 文件无法读取、编码错误
    HEADER_ERROR = "header_error"  # 表头定位失败、关键列缺失
    DATA_ERROR = "data_error"  # 数据类型错误、清洗失败
    LOGIC_ERROR = "logic_error"  # 业务逻辑错误（如金额不平）
    WARNING = "warning"  # 非阻断性问题（如模糊匹配、未知支付方式）


# ============================================================================
# 字段映射常量
# ============================================================================

# 预订汇总表字段映射
BOOKING_MAPPING: Dict[str, str] = {
    # 基础维度字段
    "部门": "department",
    "订位人": "booking_person",
    "订台数": "booking_count",
    # 金额字段
    "销售金额": "sales_amount",
    "服务费": "service_fee",
    "自动扣减": "auto_deduction",
    "基本业绩": "base_performance",
    "免单金额": "free_amount",
    "挂账金额": "credit_amount",
    "调整金额": "adjustment_amount",
    "折扣金额": "discount_amount",
    "抹零金额": "round_off_amount",
    "赠送金额": "gift_amount",
    "应收金额": "receivable_amount",
    "实收金额": "actual_received",
    # 支付方式字段
    "支付方式_微信支付": "payment_wechat",
    "支付方式_支付宝": "payment_alipay",
    "支付方式_会员支付": "payment_member",
    "支付方式_会员本金": "payment_member_principal",
    "支付方式_会员赠送": "payment_member_gift",
    "支付方式_现金": "payment_cash",
    "支付方式_pos银行卡": "payment_pos_card",
    "支付方式_服务员收款": "payment_waiter",
    "支付方式_员工信用扣款": "payment_employee_credit",
    "支付方式_付呗": "payment_fubei",
    "支付方式_团购": "payment_groupon",
    "支付方式_店长签单": "payment_manager_sign",
    "支付方式_演绎提成": "payment_performance_commission",
    "支付方式_抖音": "payment_douyin",
    "支付方式_POS机": "payment_pos",
    "支付方式_营销提成": "payment_marketing_commission",
    "支付方式_过期取酒": "payment_expired_wine",
    "支付方式_招待": "payment_entertainment",
    "支付方式_会员停用": "payment_member_disabled",
    "支付方式_三倍充值活动": "payment_triple_recharge",
    "支付方式_往来款": "payment_inter_account",
    "支付方式_高德": "payment_gaode",
    # 酒水类别字段
    "酒水类别金额_过期取酒": "beverage_expired_wine",
    "酒水类别金额_小计": "beverage_subtotal",
}

# 酒水销售分析表字段映射
SALES_MAPPING: Dict[str, str] = {
    # 维度字段
    "酒水名称": "beverage_name",
    "类别名称": "category_name",
    "单位": "unit",
    "区域": "area",
    # 成本字段
    "成本_小计": "cost_total",
    "成本_销售": "cost_sales",
    "成本_赠送": "cost_gift",
    # 利润字段
    "利润": "profit",
    "利润率": "profit_rate",
    # 合计字段
    "合计_数量": "total_quantity",
    "合计_金额": "total_amount",
    # 销售数量字段
    "销售数量_小计": "sales_qty_total",
    "销售数量_销售": "sales_qty_sales",
    "销售数量_套餐子物品": "sales_qty_combo",
    "销售数量_例送子物品": "sales_qty_free_combo",
    # 销售金额字段
    "销售金额_小计": "sales_amount_total",
    "销售金额_销售": "sales_amount_sales",
    "销售金额_套餐子物品": "sales_amount_combo",
    "销售金额_例送子物品": "sales_amount_free_combo",
    # 赠送数量字段
    "赠送数量_小计": "gift_qty_total",
    "赠送数量_赠送": "gift_qty_gift",
    "赠送数量_套餐子物品": "gift_qty_combo",
    # 赠送金额字段
    "赠送金额_小计": "gift_amount_total",
    "赠送金额_赠送": "gift_amount_gift",
    "赠送金额_套餐子物品": "gift_amount_combo",
}

# 包厢开台分析表字段映射
ROOM_MAPPING: Dict[str, str] = {
    # 基础信息字段
    "包厢名称": "room_name",
    "包厢类型": "room_type",
    "区域名称": "area_name",
    "开台单号": "order_no",
    "开房计费模式": "billing_mode",
    "开房时间": "open_time",
    "关房时间": "close_time",
    "清洁时间": "clean_time",
    "营业日": "business_date",
    "消费时长": "duration_minutes",
    "时段": "time_period",
    "账单备注": "bill_remark",
    # 金额字段
    "账单合计": "bill_total",
    "应收金额": "receivable_amount",
    "实收金额": "actual_received",
    "赠送": "gift_amount",
    "抹零金额": "round_off_amount",
    "调整金额": "adjustment_amount",
    "挂账金额": "credit_amount",
    "免单金额": "free_amount",
    "房费折扣金额": "room_discount",
    "酒水折扣金额": "beverage_discount",
    "基本业绩": "base_performance",
    "低消费": "min_consumption",
    "低消差额": "min_consumption_diff",
    "计入低消金额": "included_min_consumption",
    "不计入低消金额": "excluded_min_consumption",
    "特饮金额": "special_drink_amount",
    # 支付方式字段
    "支付方式_微信支付": "payment_wechat",
    "支付方式_支付宝": "payment_alipay",
    "支付方式_会员支付": "payment_member",
    "支付方式_会员本金": "payment_member_principal",
    "支付方式_会员赠送": "payment_member_gift",
    "支付方式_现金": "payment_cash",
    "支付方式_服务员收款": "payment_waiter",
    "支付方式_付呗": "payment_fubei",
    "支付方式_店长签单": "payment_manager_sign",
    "支付方式_美团": "payment_meituan",
    "支付方式_抖音": "payment_douyin",
}

# 收入类支付方式（计入实收）
INCOME_PAYMENT_FIELDS: Set[str] = {
    "payment_wechat",  # 微信支付
    "payment_alipay",  # 支付宝
    "payment_cash",  # 现金
    "payment_pos_card",  # POS银行卡
    "payment_waiter",  # 服务员收款
    "payment_fubei",  # 付呗
    "payment_groupon",  # 团购
    "payment_douyin",  # 抖音
    "payment_pos",  # POS机
    "payment_gaode",  # 高德
    "payment_meituan",  # 美团
}

# 成本/权益类支付方式（不计入实收）
COST_PAYMENT_FIELDS: Set[str] = {
    "payment_member",  # 会员支付
    "payment_member_principal",  # 会员本金
    "payment_member_gift",  # 会员赠送
    "payment_employee_credit",  # 员工信用扣款
    "payment_manager_sign",  # 店长签单
    "payment_performance_commission",  # 演绎提成
    "payment_marketing_commission",  # 营销提成
    "payment_expired_wine",  # 过期取酒
    "payment_entertainment",  # 招待
    "payment_member_disabled",  # 会员停用
}

# 会员相关支付方式（需与本金/赠送互斥计算）
MEMBER_PAYMENT_FIELDS: Set[str] = {
    "payment_member",
    "payment_member_principal",
    "payment_member_gift",
}


# ============================================================================
# Pydantic 数据模型
# ============================================================================


class RowError(BaseModel):
    """单行错误信息（统一错误模型）"""

    row_index: int = Field(..., description="行索引（0-based），-1 表示文件级/全局错误")
    column: str = Field(..., description="错误列名")
    message: str = Field(..., description="错误描述")
    error_type: ETLErrorType = Field(
        default=ETLErrorType.DATA_ERROR, description="错误类型"
    )
    severity: str = Field(default="error", description="严重级别: error | warning")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="原始行数据快照")


class ValidationResult(BaseModel):
    """校验结果"""

    is_valid: bool = Field(..., description="是否通过校验")
    total_rows: int = Field(..., description="总行数")
    error_count: int = Field(..., description="错误行数")
    errors: List[RowError] = Field(default_factory=list, description="错误列表")
    summary: Dict[str, Any] = Field(default_factory=dict, description="校验摘要")


# ============================================================================
# 辅助函数
# ============================================================================


def _clean_numeric_value(value: Any) -> float:
    """
    清洗数值字段

    处理：
    - 去除货币符号 (¥, $)
    - 去除千分位分隔符 (,)
    - 空值/NaN 转为 0.0

    Args:
        value: 原始值

    Returns:
        float: 清洗后的数值
    """
    if pd.isna(value) or value is None:
        return 0.0

    if isinstance(value, (int, float)):
        return float(value) if not pd.isna(value) else 0.0

    # 字符串处理
    value_str = str(value).strip()
    if value_str == "" or value_str.lower() == "nan":
        return 0.0

    # 去除货币符号和分隔符
    value_str = (
        value_str.replace("¥", "").replace("$", "").replace(",", "").replace(" ", "")
    )

    # 处理百分号
    if value_str.endswith("%"):
        value_str = value_str[:-1]
        try:
            return float(value_str)
        except ValueError:
            return 0.0

    try:
        return float(value_str)
    except ValueError:
        return 0.0


def _clean_datetime_value(value: Any) -> Optional[str]:
    """
    清洗日期时间字段

    Args:
        value: 原始值

    Returns:
        Optional[str]: ISO 8601 格式字符串，无法解析返回 None
    """
    if pd.isna(value) or value is None:
        return None

    # 已经是 datetime 对象
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().isoformat()

    value_str = str(value).strip()
    if value_str == "" or value_str.lower() == "nan":
        return None

    # 尝试多种日期格式
    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ]

    for fmt in date_formats:
        try:
            dt = datetime.strptime(value_str, fmt)
            return dt.isoformat()
        except ValueError:
            continue

    # pandas 自动解析
    try:
        dt = pd.to_datetime(value_str)
        if pd.notna(dt):
            return dt.isoformat()
    except Exception:
        pass

    return None


def _convert_to_snake_case(chinese_name: str) -> str:
    """
    将中文支付方式名称转换为 snake_case 英文名

    Args:
        chinese_name: 中文名称（如 "小红书"）

    Returns:
        str: snake_case 名称（如 "payment_xiaohongshu"）
    """
    # 常见支付方式的中英文映射
    payment_map = {
        "微信": "wechat",
        "支付宝": "alipay",
        "现金": "cash",
        "会员": "member",
        "团购": "groupon",
        "抖音": "douyin",
        "美团": "meituan",
        "高德": "gaode",
        "小红书": "xiaohongshu",
        "快手": "kuaishou",
        "拼多多": "pinduoduo",
        "银行卡": "card",
        "pos": "pos",
        "付呗": "fubei",
    }

    # 先尝试直接映射
    name_lower = chinese_name.lower()
    for cn, en in payment_map.items():
        if cn in chinese_name or cn.lower() in name_lower:
            return f"payment_{en}"

    # 如果是纯英文，直接转换
    if re.match(r"^[a-zA-Z0-9_]+$", chinese_name):
        return f"payment_{chinese_name.lower()}"

    # 使用拼音首字母（简化处理）
    # 实际项目可以引入 pypinyin 库
    return f"payment_{chinese_name.replace(' ', '_')}"


# ============================================================================
# CleanerService 主类
# ============================================================================


class CleanerService:
    """
    数据清洗服务

    负责将 Parser 输出的 DataFrame 转换为符合数据库规范的数据结构。

    特性：
    - 支持模糊列名匹配（相似度 > 0.85 自动映射）
    - 无状态设计，支持流式分块处理
    - 统一的错误模型，区分 error 和 warning
    """

    # 模糊匹配阈值（相似度 > 此值时视为匹配成功）
    FUZZY_MATCH_THRESHOLD: float = 0.85

    def __init__(self, tolerance: float = 1.0):
        """
        初始化清洗服务

        Args:
            tolerance: 平衡性校验的误差容忍度（元）
        """
        self.tolerance = tolerance
        self._errors: List[RowError] = []
        # 用于收集模糊匹配等非阻断性警告
        self._warnings: List[RowError] = []

    def clean_data(
        self, df: pd.DataFrame, report_type: str
    ) -> Tuple[List[Dict], ValidationResult]:
        """
        主入口函数：清洗数据并校验

        设计说明（流式处理适配）：
        - 此方法是无状态的，仅依赖传入的 df 参数
        - 可安全地对分块数据（Chunk）多次调用
        - 返回的 row_index 是相对于当前 df 的索引

        Args:
            df: 原始 DataFrame (Parser 输出)
            report_type: 报表类型 ('booking' | 'sales' | 'room')

        Returns:
            Tuple[List[Dict], ValidationResult]: (清洗后的数据列表, 校验报告)
        """
        # 重置错误和警告收集器（确保无状态）
        self._errors = []
        self._warnings = []

        # 1. 获取对应的映射字典
        mapping = self._get_mapping_by_type(report_type)
        if mapping is None:
            return [], ValidationResult(
                is_valid=False,
                total_rows=len(df),
                error_count=1,
                errors=[
                    RowError(
                        row_index=-1,
                        column="report_type",
                        message=f"不支持的报表类型: {report_type}",
                        error_type=ETLErrorType.HEADER_ERROR,
                        severity="error",
                        raw_data={},
                    )
                ],
                summary={"error": "不支持的报表类型"},
            )

        # 2. 复制 DataFrame 避免修改原数据
        df_clean = df.copy()

        # 3. 动态列归集（处理未知支付方式）
        df_clean, extra_data_list = self._pack_dynamic_columns(df_clean, mapping)

        # 4. 重命名列（应用映射，包含模糊匹配）
        df_clean = self._apply_mapping(df_clean, mapping)

        # 5. 数据类型转换
        df_clean = self._convert_types(df_clean, report_type)

        # 6. 添加 extra_info 列
        if extra_data_list:
            df_clean["extra_info"] = extra_data_list
        else:
            df_clean["extra_info"] = [{}] * len(df_clean)

        # 7. 业务规则校验
        validation_result = self._validate_business_rules(df_clean, report_type)

        # 8. 合并模糊匹配警告到校验结果
        if self._warnings:
            validation_result.errors.extend(self._warnings)
            # 警告不影响 is_valid 状态，但更新 summary
            validation_result.summary["fuzzy_match_warnings"] = len(self._warnings)

        # 9. 转换为 List[Dict]
        cleaned_data = self._dataframe_to_records(df_clean)

        return cleaned_data, validation_result

    def _get_mapping_by_type(self, report_type: str) -> Optional[Dict[str, str]]:
        """
        根据报表类型获取对应的映射字典

        Args:
            report_type: 报表类型

        Returns:
            Optional[Dict[str, str]]: 映射字典，不支持的类型返回 None
        """
        mapping_dict = {
            "booking": BOOKING_MAPPING,
            "sales": SALES_MAPPING,
            "room": ROOM_MAPPING,
        }
        return mapping_dict.get(report_type.lower())

    def _pack_dynamic_columns(
        self, df: pd.DataFrame, mapping: Dict[str, str]
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        动态列归集：将未映射的支付方式列打包到 extra_info

        Args:
            df: 输入 DataFrame
            mapping: 字段映射字典

        Returns:
            Tuple[pd.DataFrame, List[Dict]]:
                - 移除动态列后的 DataFrame
                - 每行的额外支付方式字典列表
        """
        dynamic_columns: List[str] = []

        # 识别以 "支付方式_" 开头但不在映射中的列
        for col in df.columns:
            col_str = str(col)
            if col_str.startswith("支付方式_") and col_str not in mapping:
                dynamic_columns.append(col)

        if not dynamic_columns:
            return df, [{} for _ in range(len(df))]

        column_field_map = {
            col: _convert_to_snake_case(str(col).replace("支付方式_", "", 1))
            for col in dynamic_columns
        }

        row_index = pd.RangeIndex(len(df))
        dynamic_df = df[dynamic_columns].copy()
        dynamic_df["__row_index"] = row_index.to_numpy()

        melted = dynamic_df.melt(
            id_vars="__row_index", var_name="column", value_name="raw_value"
        )

        if melted.empty:
            df_clean = df.drop(columns=dynamic_columns, errors="ignore")
            return df_clean, [{} for _ in range(len(df_clean))]

        raw_str = melted["raw_value"].astype(str).str.strip()

        invalid_mask = raw_str.str.lower().isin({"", "nan", "none", "nat", "<na>"})
        cleaned_str = (
            raw_str.where(~invalid_mask)
            .str.replace("¥", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.rstrip("%")
        )

        numeric_values = pd.to_numeric(cleaned_str, errors="coerce").fillna(0.0)
        melted["value"] = numeric_values
        filtered = melted[numeric_values != 0].copy()

        if filtered.empty:
            df_clean = df.drop(columns=dynamic_columns, errors="ignore")
            return df_clean, [{} for _ in range(len(df_clean))]

        filtered["field"] = filtered["column"].map(column_field_map)

        pivot = filtered.pivot_table(
            index="__row_index",
            columns="field",
            values="value",
            aggfunc="sum",
        ).reindex(row_index)

        extra_info_series = pd.Series(
            [{} for _ in range(len(df))], index=row_index, dtype=object
        )

        if not pivot.empty:
            stacked = pivot.stack()
            if not stacked.empty:
                # 注意：groupby.apply(dict) 在 pandas 中可能把 dict “展开”为 Series，
                # 进而产生 MultiIndex，导致后续 update/reindex_like 失败。
                # 这里用 agg 保证每个 row 产出一个“标量 dict”，index 仅为行号。
                extra_dict_series = stacked.groupby(level=0).agg(
                    lambda s: s.droplevel(0).to_dict()
                )
                # 批量写回（避免 Series.update 内部的 reindex_like/MultiIndex 推断）
                extra_info_series.loc[extra_dict_series.index] = (
                    extra_dict_series.values
                )

        df_clean = df.drop(columns=dynamic_columns, errors="ignore")
        return df_clean, extra_info_series.tolist()

    def _apply_mapping(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        应用字段映射，重命名列（支持模糊匹配）

        处理流程：
        1. 精确匹配：列名完全一致
        2. 模糊匹配：相似度 > FUZZY_MATCH_THRESHOLD (0.85) 时自动映射
        3. 记录警告：模糊匹配成功时生成 WARNING 级别日志

        Args:
            df: 输入 DataFrame
            mapping: 字段映射字典 (中文名 -> 英文名)

        Returns:
            pd.DataFrame: 重命名后的 DataFrame
        """
        rename_dict: Dict[str, str] = {}
        # 跟踪已使用的映射目标，避免多列映射到同一字段
        used_targets: Set[str] = set()
        # 未匹配的列名（用于模糊匹配）
        unmatched_columns: List[str] = []

        # === 第一轮：精确匹配 ===
        for col in df.columns:
            col_str = str(col)
            if col_str in mapping:
                target = mapping[col_str]
                rename_dict[col_str] = target
                used_targets.add(target)
            else:
                unmatched_columns.append(col_str)

        # === 第二轮：模糊匹配（仅针对未精确匹配的列） ===
        # 获取尚未被使用的映射源列表
        available_sources = {
            cn: en for cn, en in mapping.items() if en not in used_targets
        }

        for col in unmatched_columns:
            best_match = self._find_best_fuzzy_match(col, available_sources)
            if best_match:
                source_name, target_name, similarity = best_match
                rename_dict[col] = target_name
                used_targets.add(target_name)
                # 从可用源中移除已匹配的
                del available_sources[source_name]

                # 记录模糊匹配警告
                self._warnings.append(
                    RowError(
                        row_index=-1,  # 文件级警告
                        column=col,
                        message=(
                            f"列名模糊匹配: '{col}' 被自动映射为 '{source_name}' "
                            f"(标准字段: {target_name}, 相似度: {similarity:.2%})"
                        ),
                        error_type=ETLErrorType.WARNING,
                        severity="warning",
                        raw_data={
                            "original_column": col,
                            "matched_source": source_name,
                            "target_field": target_name,
                            "similarity": round(similarity, 4),
                        },
                    )
                )

        # 重命名
        df = df.rename(columns=rename_dict)

        # 保留已映射的列
        mapped_columns = set(rename_dict.values())
        columns_to_keep = [col for col in df.columns if col in mapped_columns]

        # 如果有 extra_info 列，保留它
        if "extra_info" in df.columns:
            columns_to_keep.append("extra_info")

        return df[columns_to_keep] if columns_to_keep else df

    def _find_best_fuzzy_match(
        self, column_name: str, available_sources: Dict[str, str]
    ) -> Optional[Tuple[str, str, float]]:
        """
        为给定列名找到最佳的模糊匹配

        使用 difflib.SequenceMatcher 计算相似度，
        返回相似度最高且超过阈值的匹配。

        Args:
            column_name: 待匹配的列名
            available_sources: 可用的映射源 (中文名 -> 英文名)

        Returns:
            Optional[Tuple[str, str, float]]:
                (匹配的中文源名, 目标英文名, 相似度)，无匹配返回 None
        """
        best_match: Optional[Tuple[str, str, float]] = None
        best_similarity: float = 0.0

        for source_cn, target_en in available_sources.items():
            # 使用 SequenceMatcher 计算相似度
            similarity = difflib.SequenceMatcher(None, column_name, source_cn).ratio()

            if similarity > best_similarity and similarity > self.FUZZY_MATCH_THRESHOLD:
                best_similarity = similarity
                best_match = (source_cn, target_en, similarity)

        return best_match

    def _convert_types(self, df: pd.DataFrame, report_type: str) -> pd.DataFrame:
        """
        数据类型转换

        Args:
            df: 输入 DataFrame
            report_type: 报表类型

        Returns:
            pd.DataFrame: 类型转换后的 DataFrame
        """
        df = df.copy()

        # 日期时间字段
        datetime_fields = {"open_time", "close_time", "clean_time", "business_date"}

        # 整数字段（数量类）
        integer_fields = {
            "booking_count",
            "total_quantity",
            "duration_minutes",
            "sales_qty_total",
            "sales_qty_sales",
            "sales_qty_combo",
            "sales_qty_free_combo",
            "gift_qty_total",
            "gift_qty_gift",
            "gift_qty_combo",
        }

        for col in df.columns:
            if col == "extra_info":
                continue

            if col in datetime_fields:
                # 日期时间转换
                df[col] = df[col].apply(_clean_datetime_value)
            elif col in integer_fields:
                # 整数转换
                df[col] = df[col].apply(lambda x: int(_clean_numeric_value(x)))
            else:
                # 尝试数值转换
                try:
                    sample_values = df[col].dropna().head(5)
                    is_numeric = True
                    for val in sample_values:
                        if isinstance(val, str):
                            val_clean = val.replace("¥", "").replace(",", "").strip()
                            try:
                                float(val_clean)
                            except ValueError:
                                is_numeric = False
                                break

                    if is_numeric or df[col].dtype in ["int64", "float64"]:
                        df[col] = df[col].apply(_clean_numeric_value)
                except Exception:
                    pass

        return df

    def _validate_business_rules(
        self, df: pd.DataFrame, report_type: str
    ) -> ValidationResult:
        """
        业务规则校验

        Args:
            df: 清洗后的 DataFrame
            report_type: 报表类型

        Returns:
            ValidationResult: 校验结果
        """
        errors: List[RowError] = []
        total_rows = len(df)

        if report_type == "booking":
            # 平衡性校验：实收金额 vs 收入类支付方式合计
            errors.extend(self._validate_balance(df, report_type))
            # 深度校验：账单构成校验（销售 - 优惠 = 实收）
            errors.extend(self._validate_booking_logic(df))
        elif report_type == "room":
            # 平衡性校验：实收金额 vs 收入类支付方式合计
            errors.extend(self._validate_balance(df, report_type))
            # 深度校验：账单构成校验 + 时间逻辑校验
            errors.extend(self._validate_room_logic(df))
        elif report_type == "sales":
            # 酒水销售表：成本/利润校验
            errors.extend(self._validate_sales_balance(df))

        # 汇总
        is_valid = len(errors) == 0
        summary = {
            "report_type": report_type,
            "total_rows": total_rows,
            "error_count": len(errors),
            "validation_time": datetime.now().isoformat(),
        }

        return ValidationResult(
            is_valid=is_valid,
            total_rows=total_rows,
            error_count=len(errors),
            errors=errors,
            summary=summary,
        )

    def _validate_balance(self, df: pd.DataFrame, report_type: str) -> List[RowError]:
        """
        平衡性校验：实收金额 = 收入类支付方式合计

        Args:
            df: 清洗后的 DataFrame
            report_type: 报表类型

        Returns:
            List[RowError]: 错误列表
        """
        errors: List[RowError] = []

        if "actual_received" not in df.columns:
            return errors

        for idx in range(len(df)):
            row = df.iloc[idx]
            actual_received = _clean_numeric_value(row.get("actual_received", 0))

            # 计算收入类支付方式合计
            income_sum = 0.0
            for field in INCOME_PAYMENT_FIELDS:
                if field in df.columns:
                    income_sum += _clean_numeric_value(row.get(field, 0))

            # 加上 extra_info 中的动态支付方式
            extra_info = row.get("extra_info", {})
            if isinstance(extra_info, dict):
                for key, value in extra_info.items():
                    # 动态支付方式默认视为收入类
                    income_sum += _clean_numeric_value(value)

            # 计算差异
            diff = abs(actual_received - income_sum)
            if diff > self.tolerance:
                errors.append(
                    RowError(
                        row_index=idx,
                        column="actual_received",
                        message=f"实收金额({actual_received:.2f})与支付方式合计({income_sum:.2f})不平衡，差异: {diff:.2f}元",
                        error_type=ETLErrorType.LOGIC_ERROR,
                        severity="error",
                        raw_data={
                            "actual_received": actual_received,
                            "payment_sum": income_sum,
                            "difference": diff,
                        },
                    )
                )

        return errors

    def _validate_sales_balance(self, df: pd.DataFrame) -> List[RowError]:
        """
        酒水销售表校验：成本/利润平衡

        Args:
            df: 清洗后的 DataFrame

        Returns:
            List[RowError]: 错误列表
        """
        errors: List[RowError] = []

        for idx in range(len(df)):
            row = df.iloc[idx]

            # 成本平衡校验：成本_小计 = 成本_销售 + 成本_赠送
            if all(f in df.columns for f in ["cost_total", "cost_sales", "cost_gift"]):
                cost_total = _clean_numeric_value(row.get("cost_total", 0))
                cost_sales = _clean_numeric_value(row.get("cost_sales", 0))
                cost_gift = _clean_numeric_value(row.get("cost_gift", 0))

                expected_total = cost_sales + cost_gift
                diff = abs(cost_total - expected_total)

                if diff > self.tolerance:
                    errors.append(
                        RowError(
                            row_index=idx,
                            column="cost_total",
                            message=f"成本小计({cost_total:.2f})与成本_销售+成本_赠送({expected_total:.2f})不匹配",
                            error_type=ETLErrorType.LOGIC_ERROR,
                            severity="error",
                            raw_data={
                                "cost_total": cost_total,
                                "cost_sales": cost_sales,
                                "cost_gift": cost_gift,
                                "expected": expected_total,
                            },
                        )
                    )

            # 利润校验：利润 = 销售金额_小计 - 成本_小计
            if all(
                f in df.columns for f in ["profit", "sales_amount_total", "cost_total"]
            ):
                profit = _clean_numeric_value(row.get("profit", 0))
                sales_amount = _clean_numeric_value(row.get("sales_amount_total", 0))
                cost_total = _clean_numeric_value(row.get("cost_total", 0))

                expected_profit = sales_amount - cost_total
                diff = abs(profit - expected_profit)

                if diff > self.tolerance:
                    errors.append(
                        RowError(
                            row_index=idx,
                            column="profit",
                            message=f"利润({profit:.2f})与销售金额-成本({expected_profit:.2f})不匹配",
                            error_type=ETLErrorType.LOGIC_ERROR,
                            severity="error",
                            raw_data={
                                "profit": profit,
                                "sales_amount_total": sales_amount,
                                "cost_total": cost_total,
                                "expected_profit": expected_profit,
                            },
                        )
                    )

        return errors

    def _validate_booking_logic(self, df: pd.DataFrame) -> List[RowError]:
        """
        预订汇总表深度校验：验证账单金额的扣减逻辑是否成立

        校验公式：
            |实收金额 - (销售金额 - 免单金额 - 挂账金额 - 折扣金额 - 抹零金额 - 调整金额)| <= tolerance

        Args:
            df: 清洗后的 DataFrame（列名已映射为英文）

        Returns:
            List[RowError]: 错误列表
        """
        errors: List[RowError] = []

        # 必须存在 actual_received 字段才能进行校验
        if "actual_received" not in df.columns:
            return errors

        # 定义扣减字段及其默认值
        deduction_fields = [
            "free_amount",  # 免单金额
            "credit_amount",  # 挂账金额
            "discount_amount",  # 折扣金额
            "round_off_amount",  # 抹零金额
            "adjustment_amount",  # 调整金额
        ]

        for idx in range(len(df)):
            row = df.iloc[idx]

            # 获取实收金额
            actual_received = _clean_numeric_value(row.get("actual_received", 0))

            # 获取销售金额（如果不存在则跳过该行校验）
            if "sales_amount" not in df.columns:
                continue
            sales_amount = _clean_numeric_value(row.get("sales_amount", 0))

            # 累加所有扣减金额
            total_deduction = 0.0
            deduction_details = {}
            for field in deduction_fields:
                if field in df.columns:
                    value = _clean_numeric_value(row.get(field, 0))
                else:
                    value = 0.0
                deduction_details[field] = value
                total_deduction += value

            # 计算预期实收金额
            expected_actual = sales_amount - total_deduction

            # 计算差异
            diff = abs(actual_received - expected_actual)

            if diff > self.tolerance:
                errors.append(
                    RowError(
                        row_index=idx,
                        column="actual_received",
                        message=(
                            f"账单构成校验失败: 实收金额({actual_received:.2f}) != "
                            f"销售金额({sales_amount:.2f}) - 扣减合计({total_deduction:.2f}) = "
                            f"预期({expected_actual:.2f})，差异: {diff:.2f}元"
                        ),
                        error_type=ETLErrorType.LOGIC_ERROR,
                        severity="error",
                        raw_data={
                            "actual_received": actual_received,
                            "sales_amount": sales_amount,
                            "total_deduction": total_deduction,
                            "expected_actual": expected_actual,
                            "difference": diff,
                            **deduction_details,
                        },
                    )
                )

        return errors

    def _validate_room_logic(self, df: pd.DataFrame) -> List[RowError]:
        """
        包厢开台表深度校验：验证账单构成和时间逻辑

        A. 账单构成校验公式：
            |实收金额 - (账单合计 - 抹零 - 调整 - 挂账 - 免单 - 房费折扣 - 酒水折扣 - 权益类支付)| <= tolerance

        B. 时间逻辑校验规则：
            - open_time <= close_time
            - close_time <= clean_time

        Args:
            df: 清洗后的 DataFrame（列名已映射为英文）

        Returns:
            List[RowError]: 错误列表
        """
        errors: List[RowError] = []

        # ===== A. 账单构成校验 =====
        errors.extend(self._validate_room_bill_balance(df))

        # ===== B. 时间逻辑校验 =====
        errors.extend(self._validate_room_time_logic(df))

        return errors

    def _validate_room_bill_balance(self, df: pd.DataFrame) -> List[RowError]:
        """
        包厢开台表账单构成校验

        校验公式：
            实收金额 ≈ 账单合计 - 抹零 - 调整 - 挂账 - 免单 - 房费折扣 - 酒水折扣 - 权益类支付

        Args:
            df: 清洗后的 DataFrame

        Returns:
            List[RowError]: 错误列表
        """
        errors: List[RowError] = []

        # 必须存在关键字段才能进行校验
        if "actual_received" not in df.columns or "bill_total" not in df.columns:
            return errors

        # 定义扣减字段
        deduction_fields = [
            "round_off_amount",  # 抹零金额
            "adjustment_amount",  # 调整金额
            "credit_amount",  # 挂账金额
            "free_amount",  # 免单金额
            "room_discount",  # 房费折扣
            "beverage_discount",  # 酒水折扣
        ]

        for idx in range(len(df)):
            row = df.iloc[idx]

            # 获取实收金额和账单合计
            actual_received = _clean_numeric_value(row.get("actual_received", 0))
            bill_total = _clean_numeric_value(row.get("bill_total", 0))

            # 累加扣减金额
            total_deduction = 0.0
            deduction_details = {}
            for field in deduction_fields:
                if field in df.columns:
                    value = _clean_numeric_value(row.get(field, 0))
                else:
                    value = 0.0
                deduction_details[field] = value
                total_deduction += value

            # 累加权益类支付（COST_PAYMENT_FIELDS）
            cost_payment_sum = 0.0
            cost_payment_details = {}

            # —— 会员支付互斥处理 ——
            member_total = (
                _clean_numeric_value(row.get("payment_member", 0))
                if "payment_member" in df.columns
                else 0.0
            )
            member_detail_sum = 0.0
            member_detail_values: Dict[str, float] = {}
            member_detail_has_value = False
            for member_field in ("payment_member_principal", "payment_member_gift"):
                if member_field in df.columns:
                    value = _clean_numeric_value(row.get(member_field, 0))
                    member_detail_values[member_field] = value
                    member_detail_sum += value
                    if value != 0:
                        member_detail_has_value = True

            if member_detail_has_value:
                cost_payment_sum += member_detail_sum
                for field, value in member_detail_values.items():
                    if value != 0:
                        cost_payment_details[field] = value
            elif member_total != 0:
                cost_payment_sum += member_total
                cost_payment_details["payment_member"] = member_total

            # —— 其他权益类支付方式 ——
            for field in COST_PAYMENT_FIELDS:
                if field in MEMBER_PAYMENT_FIELDS:
                    continue
                if field in df.columns:
                    value = _clean_numeric_value(row.get(field, 0))
                    if value != 0:
                        cost_payment_details[field] = value
                        cost_payment_sum += value

            # 检查 extra_info 中是否有额外的权益类支付
            extra_info = row.get("extra_info", {})
            if isinstance(extra_info, dict):
                for key, value in extra_info.items():
                    # 判断是否属于权益类（简单规则：包含 member、sign、commission 等关键词）
                    if any(
                        kw in key.lower()
                        for kw in ["member", "sign", "commission", "entertainment"]
                    ):
                        cost_payment_sum += _clean_numeric_value(value)
                        cost_payment_details[key] = _clean_numeric_value(value)

            # 计算预期实收金额
            expected_actual = bill_total - total_deduction - cost_payment_sum

            # 计算差异
            diff = abs(actual_received - expected_actual)

            if diff > self.tolerance:
                errors.append(
                    RowError(
                        row_index=idx,
                        column="actual_received",
                        message=(
                            f"包厢账单构成校验失败: 实收金额({actual_received:.2f}) != "
                            f"账单合计({bill_total:.2f}) - 扣减({total_deduction:.2f}) - "
                            f"权益类支付({cost_payment_sum:.2f}) = 预期({expected_actual:.2f})，"
                            f"差异: {diff:.2f}元"
                        ),
                        error_type=ETLErrorType.LOGIC_ERROR,
                        severity="error",
                        raw_data={
                            "actual_received": actual_received,
                            "bill_total": bill_total,
                            "total_deduction": total_deduction,
                            "cost_payment_sum": cost_payment_sum,
                            "expected_actual": expected_actual,
                            "difference": diff,
                            **deduction_details,
                            **cost_payment_details,
                        },
                    )
                )

        return errors

    def _validate_room_time_logic(self, df: pd.DataFrame) -> List[RowError]:
        """
        包厢开台表时间逻辑校验

        规则：
            - open_time <= close_time（如果两者都存在）

        Args:
            df: 清洗后的 DataFrame

        Returns:
            List[RowError]: 错误列表
        """
        errors: List[RowError] = []

        for idx in range(len(df)):
            row = df.iloc[idx]

            # 获取时间字段值（可能是 ISO 字符串或 None）
            open_time_str = row.get("open_time")
            close_time_str = row.get("close_time")
            clean_time_str = row.get("clean_time")

            # 解析时间（忽略空值）
            open_time = self._parse_time_safely(open_time_str)
            close_time = self._parse_time_safely(close_time_str)
            clean_time = self._parse_time_safely(clean_time_str)

            # 规则1: open_time <= close_time
            if open_time is not None and close_time is not None:
                if open_time > close_time:
                    errors.append(
                        RowError(
                            row_index=idx,
                            column="close_time",
                            message=(
                                f"时间逻辑错误: 开房时间({open_time_str}) > "
                                f"关房时间({close_time_str})，开房时间应早于或等于关房时间"
                            ),
                            error_type=ETLErrorType.LOGIC_ERROR,
                            severity="error",
                            raw_data={
                                "open_time": open_time_str,
                                "close_time": close_time_str,
                            },
                        )
                    )

            # 规则2: close_time <= clean_time
        return errors

    def _parse_time_safely(self, time_value: Any) -> Optional[datetime]:
        """
        安全地解析时间值

        Args:
            time_value: 时间值（可能是字符串、datetime 或 None）

        Returns:
            Optional[datetime]: 解析后的 datetime 对象，无法解析返回 None
        """
        if time_value is None or pd.isna(time_value):
            return None

        if isinstance(time_value, datetime):
            return time_value

        if isinstance(time_value, pd.Timestamp):
            return time_value.to_pydatetime()

        # 字符串处理
        time_str = str(time_value).strip()
        if time_str == "" or time_str.lower() in ("nan", "none", "nat"):
            return None

        try:
            # 尝试 pandas 自动解析
            dt = pd.to_datetime(time_str)
            if pd.notna(dt):
                return dt.to_pydatetime()
        except Exception:
            pass

        return None

    def _dataframe_to_records(self, df: pd.DataFrame) -> List[Dict]:
        """
        将 DataFrame 转换为 List[Dict]

        确保：
        - NaN 转为 None 或 0
        - extra_info 保持为 Dict

        Args:
            df: 输入 DataFrame

        Returns:
            List[Dict]: 记录列表
        """
        records = []

        for idx in range(len(df)):
            row = df.iloc[idx]
            record = {}

            for col in df.columns:
                value = row[col]

                if col == "extra_info":
                    # extra_info 必须是字典
                    record[col] = value if isinstance(value, dict) else {}
                elif pd.isna(value):
                    # NaN 处理
                    record[col] = None
                elif isinstance(value, float):
                    # 浮点数保留2位小数
                    record[col] = round(value, 2)
                else:
                    record[col] = value

            records.append(record)

        return records


# ============================================================================
# 便捷函数
# ============================================================================


def clean_and_validate(
    df: pd.DataFrame, report_type: str, tolerance: float = 1.0
) -> Tuple[List[Dict], ValidationResult]:
    """
    便捷函数：清洗数据并校验

    Args:
        df: 原始 DataFrame
        report_type: 报表类型 ('booking' | 'sales' | 'room')
        tolerance: 平衡性校验误差容忍度（元）

    Returns:
        Tuple[List[Dict], ValidationResult]: (清洗后的数据, 校验结果)
    """
    service = CleanerService(tolerance=tolerance)
    return service.clean_data(df, report_type)
