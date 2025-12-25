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

import os
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
    "订位人": "employee_name",
    "订台数": "booking_qty",
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
    "实收金额": "actual_amount",
    # 支付方式字段
    "支付方式_微信支付": "pay_wechat",
    "支付方式_支付宝": "pay_alipay",
    "支付方式_会员支付": "pay_member",
    "支付方式_会员本金": "pay_member_principal",
    "支付方式_会员赠送": "pay_member_gift",
    "支付方式_现金": "pay_cash",
    "支付方式_pos银行卡": "pay_pos_card",
    "支付方式_服务员收款": "pay_waiter",
    "支付方式_员工信用扣款": "pay_employee_credit",
    "支付方式_付呗": "pay_fubei",
    "支付方式_团购": "pay_groupon",
    "支付方式_店长签单": "pay_manager_sign",
    "支付方式_演绎提成": "pay_performance_commission",
    "支付方式_抖音": "pay_douyin",
    "支付方式_POS机": "pay_pos",
    "支付方式_营销提成": "pay_marketing_commission",
    "支付方式_过期取酒": "pay_expired_wine",
    "支付方式_招待": "pay_entertainment",
    "支付方式_会员停用": "pay_member_disabled",
    "支付方式_三倍充值活动": "pay_triple_recharge",
    "支付方式_往来款": "pay_inter_account",
    "支付方式_高德": "pay_gaode",
    "支付方式_人员打折": "pay_staff_discount",
    # 酒水类别字段
    "酒水类别金额_过期取酒": "beverage_expired_wine",
    "酒水类别金额_小计": "beverage_subtotal",
}

# 酒水销售分析表字段映射
SALES_MAPPING: Dict[str, str] = {
    # 维度字段
    "酒水名称": "product_name",
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
    "销售数量_小计": "sales_qty",
    "销售数量_销售": "sales_qty_sales",
    "销售数量_套餐子物品": "sales_qty_package",
    "销售数量_例送子物品": "sales_qty_example",
    # 销售金额字段
    "销售金额_小计": "sales_amount",
    "销售金额_销售": "sales_amount_sales",
    "销售金额_套餐子物品": "sales_amount_package",
    # 赠送数量字段
    "赠送数量_小计": "gift_qty",
    "赠送数量_赠送": "gift_qty_gift",
    "赠送数量_套餐子物品": "gift_qty_combo",
    # 赠送金额字段
    "赠送金额_小计": "gift_amount",
    "赠送金额_赠送": "gift_amount_gift",
    "赠送金额_套餐子物品": "gift_amount_combo",
}

# 包厢开台分析表字段映射
ROOM_MAPPING: Dict[str, str] = {
    # 基础信息字段
    "包厢名称": "room_no",
    "包厢类型": "room_type",
    "区域名称": "area_name",
    "开台单号": "order_no",
    "开房计费模式": "billing_mode",
    "开房时间": "open_time",
    "关房时间": "close_time",
    "清洁时间": "clean_time",
    "营业日": "biz_date",
    "消费时长": "duration_min",
    "时段": "time_slot",
    "账单备注": "bill_remark",
    # 金额字段
    "账单合计": "bill_total",
    "应收金额": "receivable_amount",
    "实收金额": "actual_amount",
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
    "支付方式_微信支付": "pay_wechat",
    "支付方式_支付宝": "pay_alipay",
    "支付方式_会员支付": "pay_member",
    "支付方式_会员本金": "pay_member_principal",
    "支付方式_会员赠送": "pay_member_gift",
    "支付方式_现金": "pay_cash",
    "支付方式_服务员收款": "pay_waiter",
    "支付方式_付呗": "pay_fubei",
    "支付方式_店长签单": "pay_manager_sign",
    "支付方式_美团": "pay_meituan",
    "支付方式_抖音": "pay_douyin",
    "支付方式_pos银行卡": "pay_pos_card",
    "支付方式_员工信用扣款": "pay_employee_credit",
    "支付方式_团购": "pay_groupon",
    "支付方式_演绎提成": "pay_performance_commission",
    "支付方式_POS机": "pay_pos",
    "支付方式_营销提成": "pay_marketing_commission",
    "支付方式_过期取酒": "pay_expired_wine",
    "支付方式_招待": "pay_entertainment",
    "支付方式_会员停用": "pay_member_disabled",
    "支付方式_三倍充值活动": "pay_triple_recharge",
    "支付方式_往来款": "pay_inter_account",
    "支付方式_高德": "pay_gaode",
    "支付方式_人员打折": "pay_staff_discount",
}

# 连锁会员变动明细 / 会员账户变动表字段映射
MEMBER_CHANGE_MAPPING: Dict[str, str] = {
    # 基本会员信息
    "会员名称": "member_name",
    "会员卡号": "card_no",
    "会员等级": "member_level",
    "联系电话": "phone",
    # 业务属性
    "变动类型": "change_type",
    "充值类型": "recharge_type",
    "建卡门店": "card_store_name",
    "商家门店": "biz_store_name",
    # 金额相关（多级表头扁平化后列名）
    "房费变动金额_本金": "room_amount_principal",
    "房费变动金额_赠送": "room_amount_gift",
    "酒水变动金额_本金": "drink_amount_principal",
    "酒水变动金额_赠送": "drink_amount_gift",
    # 成长值 / 积分 / 余额
    "成长值_变动": "growth_delta",
    "成长值_余额": "growth_balance",
    "变动积分": "points_delta",
    "积分余额": "points_balance",
    "余额_合计": "balance_total",
    "余额_本金": "balance_principal",
    "余额_赠送": "balance_gift",
    # 其他业务字段
    "支付信息": "pay_info",
    "充值销售人": "salesperson_recharge",
    "免单人": "free_by",
    "免单金额": "free_amount",
    "备注": "remark",
    "状态": "status",
    "变动时间": "change_time",
    "操作人": "operator",
}

# 关键数值字段（缺失时需自动补 0）
CORE_NUMERIC_FIELDS: Dict[str, Tuple[str, ...]] = {
    "booking": ("booking_qty",),
    "room": ("duration_min",),
    "sales": (),
    # 会员变动：至少确保这些金额字段存在并补 0，便于后续计算充值实收
    "member_change": (
        "room_amount_principal",
        "room_amount_gift",
        "drink_amount_principal",
        "drink_amount_gift",
        "balance_total",
        "balance_principal",
        "balance_gift",
        "growth_delta",
        "growth_balance",
        "points_delta",
        "points_balance",
        "free_amount",
    ),
}

# 收入类支付方式（计入实收）
INCOME_PAYMENT_FIELDS: Set[str] = {
    "pay_wechat",  # 微信支付
    "pay_alipay",  # 支付宝
    "pay_cash",  # 现金
    "pay_pos_card",  # POS银行卡
    "pay_waiter",  # 服务员收款
    "pay_fubei",  # 付呗
    "pay_groupon",  # 团购
    "pay_douyin",  # 抖音
    "pay_pos",  # POS机
    "pay_gaode",  # 高德
    "pay_meituan",  # 美团
}

# 成本/权益类支付方式（不计入实收）
COST_PAYMENT_FIELDS: Set[str] = {
    "pay_member",  # 会员支付
    "pay_member_principal",  # 会员本金
    "pay_member_gift",  # 会员赠送
    "pay_employee_credit",  # 员工信用扣款
    "pay_manager_sign",  # 店长签单
    "pay_performance_commission",  # 演绎提成
    "pay_marketing_commission",  # 营销提成
    "pay_expired_wine",  # 过期取酒
    "pay_entertainment",  # 招待
    "pay_member_disabled",  # 会员停用
    "pay_staff_discount",  # 人员打折
    "pay_triple_recharge",  # 三倍充值活动
}

# 会员相关支付方式（需与本金/赠送互斥计算）
MEMBER_PAYMENT_FIELDS: Set[str] = {
    "pay_member",
    "pay_member_principal",
    "pay_member_gift",
}

# 支付方式展示名称映射（code -> 中文名称）
PAYMENT_DISPLAY_NAME_MAP: Dict[str, str] = {
    "wechat": "微信支付",
    "alipay": "支付宝",
    "cash": "现金",
    "pos": "POS机",
    "pos_card": "POS银行卡",
    "douyin": "抖音",
    "meituan": "美团",
    "gaode": "高德",
    "member": "会员支付",
    "member_principal": "会员本金",
    "member_gift": "会员赠送",
    "member_disabled": "会员停用",
    "waiter": "服务员收款",
    "fubei": "付呗",
    "groupon": "团购/核销",
    "manager_sign": "店长签单",
    "employee_credit": "员工信用扣款",
    "performance_commission": "演绎提成",
    "marketing_commission": "营销提成",
    "expired_wine": "过期取酒",
    "entertainment": "招待",
    "triple_recharge": "三倍充值活动",
    "inter_account": "往来款",
    "staff_discount": "人员打折",
}

# 支付方式排序（code -> sort 值）
PAYMENT_SORT_ORDER_MAP: Dict[str, int] = {
    "wechat": 10,
    "alipay": 20,
    "cash": 30,
    "pos": 40,
    "pos_card": 50,
    "douyin": 60,
    "meituan": 70,
    "gaode": 80,
    "member": 100,
    "member_principal": 110,
    "member_gift": 120,
    "member_disabled": 130,
    "waiter": 140,
    "fubei": 150,
    "groupon": 160,
    "manager_sign": 170,
    "employee_credit": 180,
    "performance_commission": 190,
    "marketing_commission": 200,
    "expired_wine": 210,
    "entertainment": 220,
    "triple_recharge": 230,
    "inter_account": 240,
    "staff_discount": 250,
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
        str: snake_case 名称（如 "pay_xiaohongshu"）
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
            return f"pay_{en}"

    # 如果是纯英文，直接转换
    if re.match(r"^[a-zA-Z0-9_]+$", chinese_name):
        return f"pay_{chinese_name.lower()}"

    # 使用拼音首字母（简化处理）
    # 实际项目可以引入 pypinyin 库
    return f"pay_{chinese_name.replace(' ', '_')}"


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

    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名中提取第一个日期并标准化为 YYYY-MM-DD。

        Args:
            filename: 原始文件名

        Returns:
            Optional[str]: 标准化后的日期字符串，未匹配返回 None
        """
        if not filename:
            return None

        filename_str = str(filename)

        pattern_with_sep = r"(20\d{2}[-._]\d{1,2}[-._]\d{1,2})"
        match = re.search(pattern_with_sep, filename_str)
        if match:
            date_str = match.group(1).replace(".", "-").replace("_", "-")
            parts = date_str.split("-")
            if len(parts) == 3:
                year, month, day = parts
                return f"{year}-{int(month):02d}-{int(day):02d}"

        pattern_pure = r"(20\d{6})"
        match = re.search(pattern_pure, filename_str)
        if match:
            date_digits = match.group(1)
            return f"{date_digits[:4]}-{date_digits[4:6]}-{date_digits[6:]}"

        return None

    def _extract_store_from_filename(self, filename: str) -> Optional[str]:
        """
        从文件名中提取门店名称（如果存在）。

        匹配优先级：
        1. 括号内的“xx店/xxKTV”
        2. 直接以“店”或“KTV”结尾的中文短语
        3. 关键字兜底匹配（万象城/青年路等）

        Args:
            filename: 原始文件名

        Returns:
            Optional[str]: 解析出的门店名称，未匹配返回 None
        """
        if not filename:
            return None

        filename_str = os.path.splitext(os.path.basename(str(filename)))[0]
        if not filename_str:
            return None

        bracket_patterns = [
            r"（([^（）]{2,20}?(?:店|KTV))）",
            r"\(([^()]{2,20}?(?:店|KTV))\)",
        ]
        for pattern in bracket_patterns:
            match = re.search(pattern, filename_str)
            if match:
                candidate = match.group(1).strip()
                if candidate:
                    return candidate

        suffix_pattern = r"([\u4e00-\u9fa5·]{2,12}(?:店|KTV))"
        suffix_matches = re.findall(suffix_pattern, filename_str)
        if suffix_matches:
            return max(suffix_matches, key=len)

        fallback_keywords = {
            "万象城": "万象城店",
            "青年路": "青年路店",
            "高新": "高新店",
            "曲江": "曲江店",
        }
        for keyword, normalized in fallback_keywords.items():
            if keyword in filename_str:
                return normalized

        return None

    def _extract_stores_from_member_change(self, df_clean: pd.DataFrame) -> List[str]:
        """
        从连锁会员变动明细表中提取所有不同的门店名称
        
        从 biz_store_name 列中提取所有门店，并从括号中提取门店名称
        例如："空境·派对KTV（万象城店）" -> "万象城店"
        
        Args:
            df_clean: 清洗后的 DataFrame，应包含 biz_store_name 列
            
        Returns:
            List[str]: 去重后的门店名称列表
        """
        if "biz_store_name" not in df_clean.columns:
            return []
        
        store_names = set()
        for value in df_clean["biz_store_name"].dropna():
            if not isinstance(value, str) or not value.strip():
                continue
            
            # 从括号中提取门店名称
            extracted = self._extract_store_name_from_brackets(value.strip())
            if extracted:
                store_names.add(extracted)
        
        return sorted(list(store_names))
    
    @staticmethod
    def _extract_store_name_from_brackets(store_name: str) -> str:
        """
        从门店名称中提取括号内的内容
        
        例如：
        - "空境·派对KTV（万象城店）" -> "万象城店"
        - "空境·派对KTV(青年路店)" -> "青年路店"
        - "万象城店" -> "万象城店" (如果没有括号，返回原值)
        
        Args:
            store_name: 原始门店名称
            
        Returns:
            str: 提取后的门店名称
        """
        if not store_name or not isinstance(store_name, str):
            return store_name or ""
        
        store_name = store_name.strip()
        
        # 匹配中文括号或英文括号内的内容
        bracket_patterns = [
            r"（([^（）]+)）",  # 中文括号
            r"\(([^()]+)\)",   # 英文括号
        ]
        
        for pattern in bracket_patterns:
            match = re.search(pattern, store_name)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return extracted
        
        # 如果没有括号，返回原值
        return store_name

    @staticmethod
    def _normalize_payment_code(field_name: str) -> str:
        """
        将 pay_xxx 字段名转换为统一 code（去掉 pay_ 前缀，小写）。
        """
        if not isinstance(field_name, str):
            return ""
        normalized = field_name.strip()
        if normalized.lower().startswith("pay_"):
            normalized = normalized[4:]
        return normalized.lower()

    @staticmethod
    def _resolve_payment_display_name(field_name: str, code: str) -> str:
        """
        根据字段名/编码获取可读名称。
        """
        if code in PAYMENT_DISPLAY_NAME_MAP:
            return PAYMENT_DISPLAY_NAME_MAP[code]
        if field_name.lower().startswith("pay_"):
            return field_name[4:]
        return code or field_name

    @staticmethod
    def _classify_payment_category(field_name: str) -> str:
        """
        根据字段名判断支付方式分类。
        """
        if field_name in INCOME_PAYMENT_FIELDS:
            return "income"
        if field_name in COST_PAYMENT_FIELDS:
            return "equity"
        return "other"

    def _collect_payment_methods_meta(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        汇总当前批次涉及的支付方式元数据。
        """
        payment_meta: Dict[str, Dict[str, Any]] = {}

        def _build_meta(field_name: str, source: str) -> Optional[Dict[str, Any]]:
            if not isinstance(field_name, str) or not field_name.startswith("pay_"):
                return None
            code = self._normalize_payment_code(field_name)
            if not code:
                return None
            name = self._resolve_payment_display_name(field_name, code)
            category = self._classify_payment_category(field_name)
            sort_order = PAYMENT_SORT_ORDER_MAP.get(
                code, 500 if source == "fixed" else 900
            )
            meta = {
                "code": code,
                "name": name,
                "is_core": source == "fixed",
                "category": category,
                "source": source,
                "field_name": field_name,
                "sort_order": sort_order,
            }
            return meta

        # 固定列扫描
        for column in df.columns:
            if not isinstance(column, str) or not column.startswith("pay_"):
                continue
            meta = _build_meta(column, source="fixed")
            if meta:
                payment_meta[meta["code"]] = meta

        # 动态列来自 extra_info
        if "extra_info" in df.columns:
            dynamic_fields: Set[str] = set()
            for info in df["extra_info"]:
                if not isinstance(info, dict):
                    continue
                for key in info.keys():
                    if isinstance(key, str) and key.startswith("pay_"):
                        dynamic_fields.add(key)
            for field_name in dynamic_fields:
                code = self._normalize_payment_code(field_name)
                if code in payment_meta:
                    continue
                meta = _build_meta(field_name, source="dynamic")
                if meta:
                    payment_meta[meta["code"]] = meta

        # 按核心优先 & sort order 排序，保证输出稳定
        return sorted(
            payment_meta.values(),
            key=lambda item: (
                not item["is_core"],
                item.get("sort_order", 999),
                item["code"],
            ),
        )

    def clean_data(
        self,
        df: pd.DataFrame,
        report_type: str,
        filename: str = "",
        detected_date: Optional[str] = None,
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
            filename: 原始文件名，用于缺失时推断 biz_date
            detected_date: 从文件标题行检测到的日期（Parser 提供）

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
        df_clean = self._ensure_core_numeric_fields(df_clean, report_type)

        extracted_store_name = self._extract_store_from_filename(filename)

        # 4.1 营业日自动补全（字段映射后、类型转换前）
        if "biz_date" not in df_clean.columns:
            # 对于 member_change 类型，优先从 change_time 列提取日期
            if report_type == "member_change" and "change_time" in df_clean.columns:
                # 从 change_time 中提取日期部分
                def extract_date_from_change_time(value):
                    """从 change_time 值中提取日期部分"""
                    if pd.isna(value) or value is None:
                        return None
                    value_str = str(value).strip()
                    if value_str == "" or value_str.lower() == "nan":
                        return None
                    
                    # 尝试多种日期时间格式提取日期部分
                    # 匹配日期时间格式：2025-12-01 10:00:00, 2025/12/01 10:00:00 等
                    date_patterns = [
                        r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",  # 2025-12-01 或 2025/12/01
                        r"(\d{4}\.\d{1,2}\.\d{1,2})",      # 2025.12.01
                        r"(\d{4}年\d{1,2}月\d{1,2}日)",     # 2025年12月01日
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, value_str)
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
                    
                    # 尝试使用 pandas 解析
                    try:
                        dt = pd.to_datetime(value_str)
                        if pd.notna(dt):
                            return dt.strftime("%Y-%m-%d")
                    except:
                        pass
                    
                    return None
                
                # 从每行的 change_time 提取日期
                df_clean["biz_date"] = df_clean["change_time"].apply(extract_date_from_change_time)
                
                # 检查是否有有效的日期
                valid_dates = df_clean["biz_date"].notna()
                if valid_dates.any():
                    # 如果部分行有有效日期，对于无效的行使用文件名或标题行日期作为兜底
                    fallback_date = None
                    extracted_filename_date = self._extract_date_from_filename(filename)
                    if extracted_filename_date:
                        fallback_date = extracted_filename_date
                    elif detected_date:
                        fallback_date = detected_date
                    
                    if fallback_date:
                        df_clean.loc[~valid_dates, "biz_date"] = fallback_date
                        self._warnings.append(
                            RowError(
                                row_index=-1,
                                column="biz_date",
                                message=f"部分行的变动时间无效，使用兜底日期: {fallback_date}",
                                error_type=ETLErrorType.WARNING,
                                severity="warning",
                                raw_data={"fallback_date": fallback_date},
                            )
                        )
                    
                    # 检查是否仍有无效日期
                    if df_clean["biz_date"].isna().any():
                        self._errors.append(
                            RowError(
                                row_index=-1,
                                column="biz_date",
                                message=(
                                    "部分行无法从变动时间提取有效日期，"
                                    f"且文件名 '{filename}' 及标题行中均未发现有效日期"
                                ),
                                error_type=ETLErrorType.HEADER_ERROR,
                                severity="error",
                                raw_data={"filename": filename},
                            )
                        )
                else:
                    # 所有行的 change_time 都无效，回退到文件名或标题行
                    extracted_filename_date = self._extract_date_from_filename(filename)
                    if extracted_filename_date:
                        df_clean["biz_date"] = extracted_filename_date
                        self._warnings.append(
                            RowError(
                                row_index=-1,
                                column="biz_date",
                                message="变动时间列无效，使用文件名中的日期",
                                error_type=ETLErrorType.WARNING,
                                severity="warning",
                                raw_data={"extracted_date": extracted_filename_date},
                            )
                        )
                    elif detected_date:
                        df_clean["biz_date"] = detected_date
                        self._warnings.append(
                            RowError(
                                row_index=-1,
                                column="biz_date",
                                message=f"变动时间列无效，使用从标题行解析的日期: {detected_date}",
                                error_type=ETLErrorType.WARNING,
                                severity="warning",
                                raw_data={"detected_date": detected_date},
                            )
                        )
                    else:
                        self._errors.append(
                            RowError(
                                row_index=-1,
                                column="biz_date",
                                message=(
                                    "无法从变动时间提取日期，且文件内容缺少 'biz_date' 列，"
                                    f"文件名 '{filename}' 及标题行中均未发现有效日期"
                                ),
                                error_type=ETLErrorType.HEADER_ERROR,
                                severity="error",
                                raw_data={"filename": filename},
                            )
                        )
            else:
                # 其他报表类型：从文件名或标题行提取
                extracted_filename_date = self._extract_date_from_filename(filename)
                if extracted_filename_date:
                    df_clean["biz_date"] = extracted_filename_date
                elif detected_date:
                    # 使用 Parser 从标题行检测到的日期
                    df_clean["biz_date"] = detected_date
                    self._warnings.append(
                        RowError(
                            row_index=-1,
                            column="biz_date",
                            message=f"文件名无日期，使用从标题行解析的日期: {detected_date}",
                            error_type=ETLErrorType.WARNING,
                            severity="warning",
                            raw_data={"detected_date": detected_date},
                        )
                    )
                else:
                    self._errors.append(
                        RowError(
                            row_index=-1,
                            column="biz_date",
                            message=(
                                "无法获取营业日期：文件内容缺少 'biz_date' 列，"
                                f"且文件名 '{filename}' 及标题行中均未发现有效日期"
                            ),
                            error_type=ETLErrorType.HEADER_ERROR,
                            severity="error",
                            raw_data={"filename": filename},
                        )
                    )

        # 5. 数据类型转换
        df_clean = self._convert_types(df_clean, report_type)

        # 6. 添加 extra_info 列
        if extra_data_list:
            df_clean["extra_info"] = extra_data_list
        else:
            df_clean["extra_info"] = [{}] * len(df_clean)

        # 7. 业务规则校验
        validation_result = self._validate_business_rules(df_clean, report_type)

        # 7.1 合并文件级错误（例如营业日缺失）
        if self._errors:
            validation_result.errors.extend(self._errors)
            validation_result.error_count += len(self._errors)
            validation_result.is_valid = False

        # 8. 合并模糊匹配警告到校验结果
        if self._warnings:
            validation_result.errors.extend(self._warnings)
            # 警告不影响 is_valid 状态，但更新 summary
            validation_result.summary["fuzzy_match_warnings"] = len(self._warnings)

        # 8.1 写入文件级元数据（门店名称等）
        if validation_result.summary is None:
            validation_result.summary = {}
        meta_summary = dict(validation_result.summary.get("meta", {}))
        
        # 对于连锁会员变动明细表，统计所有不同的门店
        if report_type == "member_change" and "biz_store_name" in df_clean.columns:
            store_names = self._extract_stores_from_member_change(df_clean)
            if len(store_names) > 1:
                # 多个门店，显示"多门店"或门店列表
                meta_summary["store_name"] = f"多门店 ({len(store_names)}个)"
                meta_summary["store_names"] = sorted(store_names)  # 保存所有门店名称列表
            elif len(store_names) == 1:
                meta_summary["store_name"] = store_names[0]
            else:
                meta_summary["store_name"] = extracted_store_name
        else:
            meta_summary["store_name"] = extracted_store_name
        
        payment_methods_meta = self._collect_payment_methods_meta(df_clean)
        if payment_methods_meta:
            meta_summary["payment_methods"] = payment_methods_meta
        validation_result.summary["meta"] = meta_summary

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
            "member_change": MEMBER_CHANGE_MAPPING,
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

    def _ensure_core_numeric_fields(
        self, df: pd.DataFrame, report_type: str
    ) -> pd.DataFrame:
        """
        确保关键数值字段存在且缺失值补 0。
        """
        required_fields = CORE_NUMERIC_FIELDS.get(report_type.lower())
        if not required_fields:
            return df

        df_filled = df.copy()
        for field in required_fields:
            if field not in df_filled.columns:
                df_filled[field] = 0
            else:
                df_filled[field] = df_filled[field].fillna(0)
        return df_filled

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
        datetime_fields = {
            "open_time",
            "close_time",
            "clean_time",
            "biz_date",
            # 会员变动时间
            "change_time",
        }

        # 整数字段（数量类）
        integer_fields = {
            "booking_qty",
            "total_quantity",
            "duration_min",
            "sales_qty",
            "sales_qty_sales",
            "sales_qty_package",
            "sales_qty_free_combo",
            "gift_qty_total",
            "gift_qty_gift",
            "gift_qty_combo",
            # 会员成长值 / 积分
            "growth_delta",
            "growth_balance",
            "points_delta",
            "points_balance",
        }

        # 字符串字段（需要保持为字符串，避免被转换为数值）
        string_fields = {
            "card_no",  # 会员卡号可能是长数字，需要保持字符串格式
            "phone",    # 电话号码也需要保持字符串（可能有前导0）
            "member_name",
            "member_level",
            "card_store_name",
            "biz_store_name",
            "change_type",
            "recharge_type",
            "status",
            "operator",
            "salesperson_recharge",
            "free_by",
            "pay_info",
            "remark",
        }

        for col in df.columns:
            if col == "extra_info":
                continue

            if col in datetime_fields:
                # 日期时间转换
                df[col] = df[col].apply(_clean_datetime_value)
            elif col in string_fields:
                # 字符串字段：确保转换为字符串，避免科学计数法
                df[col] = df[col].astype(str).replace("nan", "").replace("None", "")
                # 对于 card_no，如果是科学计数法格式，尝试恢复原始值
                if col == "card_no":
                    def _fix_card_no(val):
                        if pd.isna(val) or val == "" or val == "nan":
                            return ""
                        val_str = str(val).strip()
                        # 如果是科学计数法格式（包含 'e' 或 'E'）
                        if "e" in val_str.lower() and "." in val_str:
                            try:
                                # 尝试转换为浮点数再转回整数，然后转字符串
                                num = float(val_str)
                                # 去掉小数点，恢复原始长数字
                                return str(int(num))
                            except (ValueError, OverflowError):
                                return val_str
                        return val_str
                    df[col] = df[col].apply(_fix_card_no)
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

        # 会员变动表专用派生字段：充值实收金额
        if report_type == "member_change":
            if "change_type" in df.columns:
                # 仅对充值类变动计算充值实收，其它类型默认为 0
                def _calc_recharge_income(row: pd.Series) -> float:
                    try:
                        change_type_str = str(row.get("change_type", "")).strip()
                        # 使用包含匹配，兼容 "充值"、"充值-首充"、"会员充值" 等变体
                        if "充值" not in change_type_str:
                            return 0.0
                    except Exception:
                        return 0.0

                    principal_room = _clean_numeric_value(
                        row.get("room_amount_principal", 0)
                    )
                    principal_drink = _clean_numeric_value(
                        row.get("drink_amount_principal", 0)
                    )
                    return principal_room + principal_drink

                df["recharge_real_income"] = df.apply(
                    _calc_recharge_income,
                    axis=1,
                )
            else:
                # 缺少 change_type 时，仍然补一个字段，全部为 0，避免下游 KeyError
                df["recharge_real_income"] = 0.0

            # 为了让 Importer 的 _calculate_totals 能直接汇总“会员充值实收”，
            # 这里复用 actual_amount 字段存放充值实收金额（仅用于统计，不入库存储）。
            df["actual_amount"] = df["recharge_real_income"]

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
            # 深度校验：账单构成校验（销售 - 优惠 = 实收） - 已按需取消
            # errors.extend(self._validate_booking_logic(df))
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

        if "actual_amount" not in df.columns:
            return errors

        for idx in range(len(df)):
            row = df.iloc[idx]
            actual_amount = _clean_numeric_value(row.get("actual_amount", 0))

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
            diff = abs(actual_amount - income_sum)
            if diff > self.tolerance:
                errors.append(
                    RowError(
                        row_index=idx,
                        column="actual_amount",
                        message=f"实收金额({actual_amount:.2f})与支付方式合计({income_sum:.2f})不平衡，差异: {diff:.2f}元",
                        error_type=ETLErrorType.LOGIC_ERROR,
                        severity="error",
                        raw_data={
                            "actual_amount": actual_amount,
                            "pay_sum": income_sum,
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
            if all(f in df.columns for f in ["profit", "sales_amount", "cost_total"]):
                profit = _clean_numeric_value(row.get("profit", 0))
                sales_amount = _clean_numeric_value(row.get("sales_amount", 0))
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
                                "sales_amount": sales_amount,
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

        # 必须存在 actual_amount 字段才能进行校验
        if "actual_amount" not in df.columns:
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
            actual_amount = _clean_numeric_value(row.get("actual_amount", 0))

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
            diff = abs(actual_amount - expected_actual)

            if diff > self.tolerance:
                errors.append(
                    RowError(
                        row_index=idx,
                        column="actual_amount",
                        message=(
                            f"账单构成校验失败: 实收金额({actual_amount:.2f}) != "
                            f"销售金额({sales_amount:.2f}) - 扣减合计({total_deduction:.2f}) = "
                            f"预期({expected_actual:.2f})，差异: {diff:.2f}元"
                        ),
                        error_type=ETLErrorType.LOGIC_ERROR,
                        severity="error",
                        raw_data={
                            "actual_amount": actual_amount,
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
        if "actual_amount" not in df.columns or "bill_total" not in df.columns:
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
            actual_amount = _clean_numeric_value(row.get("actual_amount", 0))
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
                _clean_numeric_value(row.get("pay_member", 0))
                if "pay_member" in df.columns
                else 0.0
            )
            member_detail_sum = 0.0
            member_detail_values: Dict[str, float] = {}
            member_detail_has_value = False
            for member_field in ("pay_member_principal", "pay_member_gift"):
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
                cost_payment_details["pay_member"] = member_total

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
                    # 调用统一分类方法，判断是否属于权益类 (equity)
                    if self._classify_payment_category(key) == "equity":
                        val = _clean_numeric_value(value)
                        if val != 0:
                            cost_payment_sum += val
                            cost_payment_details[key] = val

            # 计算预期实收金额
            expected_actual = bill_total - total_deduction - cost_payment_sum

            # 计算差异
            diff = abs(actual_amount - expected_actual)

            if diff > self.tolerance:
                errors.append(
                    RowError(
                        row_index=idx,
                        column="actual_amount",
                        message=(
                            f"包厢账单构成校验失败: 实收金额({actual_amount:.2f}) != "
                            f"账单合计({bill_total:.2f}) - 扣减({total_deduction:.2f}) - "
                            f"权益类支付({cost_payment_sum:.2f}) = 预期({expected_actual:.2f})，"
                            f"差异: {diff:.2f}元"
                        ),
                        error_type=ETLErrorType.LOGIC_ERROR,
                        severity="error",
                        raw_data={
                            "actual_amount": actual_amount,
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
    df: pd.DataFrame,
    report_type: str,
    tolerance: float = 1.0,
    filename: str = "",
    detected_date: Optional[str] = None,
) -> Tuple[List[Dict], ValidationResult]:
    """
    便捷函数：清洗数据并校验

    Args:
        df: 原始 DataFrame
        report_type: 报表类型 ('booking' | 'sales' | 'room')
        tolerance: 平衡性校验误差容忍度（元）
        filename: 原始文件名，用于缺失时推断 biz_date
        detected_date: 从文件标题行检测到的日期

    Returns:
        Tuple[List[Dict], ValidationResult]: (清洗后的数据, 校验结果)
    """
    service = CleanerService(tolerance=tolerance)
    return service.clean_data(
        df, report_type, filename=filename, detected_date=detected_date
    )


def _demo_payment_meta_extraction() -> None:
    """
    最小验证脚本：python backend/app/services/cleaner.py
    """
    sample = pd.DataFrame(
        [
            {
                "pay_wechat": 100,
                "pay_alipay": 50,
                "extra_info": {"pay_xiaohongshu": 30, "note": "demo"},
            }
        ]
    )
    service = CleanerService()
    meta = service._collect_payment_methods_meta(sample)
    print("payment_methods meta:", meta)


if __name__ == "__main__":
    _demo_payment_meta_extraction()
