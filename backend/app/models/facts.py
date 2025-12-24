"""
事实表模型

包含预订汇总、包厢开台、酒水销售等业务事实数据
"""
from sqlalchemy import Column, Integer, BigInteger, String, Date, DateTime, DECIMAL, JSON, Index
from sqlalchemy.sql import func

from app.core.database import Base


class FactBooking(Base):
    """
    预订汇总事实表
    
    记录员工预订业绩数据
    """
    __tablename__ = "fact_booking"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
    batch_id = Column(BigInteger, nullable=False, index=True, comment="关联批次")
    biz_date = Column(Date, nullable=False, comment="营业日期")
    store_id = Column(Integer, nullable=False, comment="关联门店")
    employee_id = Column(Integer, comment="关联员工(订位人)")
    department = Column(String(50), comment="部门(冗余)")
    customer_name = Column(String(50), comment="订位人/客户名")
    
    # ==================== 业务数据 ====================
    booking_qty = Column(Integer, default=0, comment="订台数")
    sales_amount = Column(DECIMAL(12, 2), default=0, comment="销售金额(应收)")
    actual_amount = Column(DECIMAL(12, 2), default=0, comment="实收金额")
    base_performance = Column(DECIMAL(12, 2), default=0, comment="基本业绩")
    service_fee = Column(DECIMAL(12, 2), default=0, comment="服务费")
    auto_deduction = Column(DECIMAL(12, 2), default=0, comment="自动扣减")
    
    # ==================== 扣减项 ====================
    gift_amount = Column(DECIMAL(12, 2), default=0, comment="赠送金额")
    discount_amount = Column(DECIMAL(12, 2), default=0, comment="折扣金额")
    free_amount = Column(DECIMAL(12, 2), default=0, comment="免单金额")
    credit_amount = Column(DECIMAL(12, 2), default=0, comment="挂账金额")
    round_off_amount = Column(DECIMAL(12, 2), default=0, comment="抹零金额")
    adjustment_amount = Column(DECIMAL(12, 2), default=0, comment="调整金额")
    
    # ==================== 核心支付方式 ====================
    pay_wechat = Column(DECIMAL(12, 2), default=0, comment="微信支付")
    pay_alipay = Column(DECIMAL(12, 2), default=0, comment="支付宝")
    pay_cash = Column(DECIMAL(12, 2), default=0, comment="现金")
    pay_pos = Column(DECIMAL(12, 2), default=0, comment="POS/银行卡")
    pay_member = Column(DECIMAL(12, 2), default=0, comment="会员支付")
    pay_douyin = Column(DECIMAL(12, 2), default=0, comment="抖音")
    pay_meituan = Column(DECIMAL(12, 2), default=0, comment="美团/团购")
    pay_scan = Column(DECIMAL(12, 2), default=0, comment="扫码支付")
    pay_deposit = Column(DECIMAL(12, 2), default=0, comment="定金消费")
    
    # ==================== 扩展字段 ====================
    extra_payments = Column(JSON, comment="其他支付方式(JSON)")
    extra_info = Column(JSON, comment="其他扩展信息(JSON)")
    
    created_at = Column(DateTime, server_default=func.now(), comment="入库时间")
    
    __table_args__ = (
        Index("idx_date_store", "biz_date", "store_id"),
        Index("idx_batch", "batch_id"),
        Index("idx_employee", "employee_id"),
        Index("idx_date_store_employee", "biz_date", "store_id", "employee_id"),
        {"comment": "预订汇总事实表"}
    )
    
    def __repr__(self):
        return f"<FactBooking(id={self.id}, date={self.biz_date}, employee_id={self.employee_id})>"


class FactRoom(Base):
    """
    包厢开台事实表
    
    记录每次开台的详细信息
    """
    __tablename__ = "fact_room"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
    batch_id = Column(BigInteger, nullable=False, index=True, comment="关联批次")
    biz_date = Column(Date, nullable=False, comment="营业日期")
    store_id = Column(Integer, nullable=False, comment="关联门店")
    room_id = Column(Integer, comment="关联包厢")
    
    # ==================== 订单信息 ====================
    order_no = Column(String(50), nullable=False, comment="开台单号(业务主键)")
    billing_mode = Column(String(100), comment="开房计费模式")
    open_time = Column(DateTime, comment="开房时间")
    close_time = Column(DateTime, comment="关房时间")
    clean_time = Column(DateTime, comment="清洁时间")
    duration_min = Column(Integer, default=0, comment="时长(分钟)")
    time_slot = Column(String(20), comment="时段")
    
    # ==================== 人员信息 ====================
    booker = Column(String(50), comment="订房人")
    booker_dept = Column(String(50), comment="订房人部门")
    sales_manager = Column(String(50), comment="销售经理")
    
    # ==================== 金额信息 ====================
    bill_total = Column(DECIMAL(12, 2), default=0, comment="账单合计")
    receivable_amount = Column(DECIMAL(12, 2), default=0, comment="应收金额")
    actual_amount = Column(DECIMAL(12, 2), default=0, comment="实收金额")
    base_performance = Column(DECIMAL(12, 2), default=0, comment="基本业绩")
    min_consumption = Column(DECIMAL(12, 2), default=0, comment="低消费")
    min_consumption_diff = Column(DECIMAL(12, 2), default=0, comment="低消差额")
    
    # ==================== 扣减项 ====================
    gift_amount = Column(DECIMAL(12, 2), default=0, comment="赠送金额")
    room_discount = Column(DECIMAL(12, 2), default=0, comment="房费折扣")
    beverage_discount = Column(DECIMAL(12, 2), default=0, comment="酒水折扣")
    free_amount = Column(DECIMAL(12, 2), default=0, comment="免单金额")
    credit_amount = Column(DECIMAL(12, 2), default=0, comment="挂账金额")
    round_off_amount = Column(DECIMAL(12, 2), default=0, comment="抹零金额")
    adjustment_amount = Column(DECIMAL(12, 2), default=0, comment="调整金额")
    
    # ==================== 核心支付方式 ====================
    pay_wechat = Column(DECIMAL(12, 2), default=0, comment="微信支付")
    pay_alipay = Column(DECIMAL(12, 2), default=0, comment="支付宝")
    pay_cash = Column(DECIMAL(12, 2), default=0, comment="现金")
    pay_pos = Column(DECIMAL(12, 2), default=0, comment="POS/银行卡")
    pay_member = Column(DECIMAL(12, 2), default=0, comment="会员支付")
    pay_douyin = Column(DECIMAL(12, 2), default=0, comment="抖音")
    pay_meituan = Column(DECIMAL(12, 2), default=0, comment="美团/团购")
    pay_scan = Column(DECIMAL(12, 2), default=0, comment="扫码支付")
    pay_deposit = Column(DECIMAL(12, 2), default=0, comment="定金消费")
    
    # ==================== 扩展字段 ====================
    extra_payments = Column(JSON, comment="其他支付方式(JSON)")
    extra_info = Column(JSON, comment="其他扩展信息(JSON)")
    
    created_at = Column(DateTime, server_default=func.now(), comment="入库时间")
    
    __table_args__ = (
        Index("idx_date_store", "biz_date", "store_id"),
        Index("idx_order_no", "store_id", "order_no", unique=True),
        Index("idx_batch", "batch_id"),
        Index("idx_room", "room_id"),
        Index("idx_date_store_room", "biz_date", "store_id", "room_id"),
        {"comment": "包厢开台事实表"}
    )
    
    def __repr__(self):
        return f"<FactRoom(id={self.id}, order_no={self.order_no})>"


class FactSales(Base):
    """
    酒水销售事实表
    
    记录商品销售汇总数据
    """
    __tablename__ = "fact_sales"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
    batch_id = Column(BigInteger, nullable=False, index=True, comment="关联批次")
    biz_date = Column(Date, nullable=False, comment="营业日期")
    store_id = Column(Integer, nullable=False, comment="关联门店")
    product_id = Column(Integer, comment="关联商品")
    
    # ==================== 商品信息(冗余) ====================
    product_name = Column(String(100), comment="商品名称")
    category_name = Column(String(50), comment="类别名称")
    unit = Column(String(20), comment="单位")
    area = Column(String(50), comment="区域")
    
    # ==================== 销售数据 ====================
    sales_qty = Column(Integer, default=0, comment="销售数量")
    sales_amount = Column(DECIMAL(12, 2), default=0, comment="销售金额")
    
    # 销售数量明细
    sales_qty_pure = Column(Integer, default=0, comment="纯销售数量")
    sales_qty_package = Column(Integer, default=0, comment="套餐子物品数量")
    sales_qty_example = Column(Integer, default=0, comment="例送子物品数量")
    
    # 销售金额明细
    sales_amount_pure = Column(DECIMAL(12, 2), default=0, comment="纯销售金额")
    sales_amount_package = Column(DECIMAL(12, 2), default=0, comment="套餐子物品金额")
    
    # ==================== 赠送数据 ====================
    gift_qty = Column(Integer, default=0, comment="赠送数量")
    gift_amount = Column(DECIMAL(12, 2), default=0, comment="赠送金额")
    
    # 赠送数量明细
    gift_qty_pure = Column(Integer, default=0, comment="纯赠送数量")
    gift_qty_package = Column(Integer, default=0, comment="套餐赠送数量")
    
    # ==================== 成本利润 ====================
    cost_total = Column(DECIMAL(12, 2), default=0, comment="成本小计")
    cost_sales = Column(DECIMAL(12, 2), default=0, comment="销售成本")
    cost_gift = Column(DECIMAL(12, 2), default=0, comment="赠送成本")
    profit = Column(DECIMAL(12, 2), default=0, comment="毛利")
    profit_rate = Column(DECIMAL(8, 2), default=0, comment="毛利率(%)")
    
    # ==================== 扩展字段 ====================
    extra_info = Column(JSON, comment="其他扩展信息(JSON)")
    
    created_at = Column(DateTime, server_default=func.now(), comment="入库时间")
    
    __table_args__ = (
        Index("idx_date_store", "biz_date", "store_id"),
        Index("idx_product", "product_id"),
        Index("idx_batch", "batch_id"),
        Index("idx_category", "category_name"),
        Index("idx_date_store_product", "biz_date", "store_id", "product_id"),
        {"comment": "酒水销售事实表"}
    )
    
    def __repr__(self):
        return f"<FactSales(id={self.id}, product={self.product_name})>"


# 导出所有事实表模型
__all__ = [
    "FactBooking",
    "FactRoom",
    "FactSales",
]

