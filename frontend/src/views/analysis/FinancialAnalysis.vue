<template>
  <div class="financial-analysis">
    <el-card class="filter-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-row">
            <div class="title-text">
              <h2>💰 财务专项分析</h2>
              <p class="card-subtitle">聚焦“钱从哪里来、又流失到哪里”</p>
            </div>
            <el-tag type="warning" effect="light">数据源：Booking</el-tag>
          </div>
        </div>
      </template>

      <div class="filters">
        <div class="filter-item">
          <span class="filter-label">时间范围</span>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            unlink-panels
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :editable="false"
            @change="handleDateRangeChange"
          />
        </div>

        <div class="filter-item dimension-switch">
          <span class="filter-label">异常监控维度</span>
          <el-radio-group
            v-model="anomalyDimension"
            size="small"
          >
            <el-radio-button label="employee">员工</el-radio-button>
            <el-radio-button label="store">门店</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </el-card>

    <el-card class="summary-card" shadow="never" v-loading="loading">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="6" v-for="card in summaryCards" :key="card.title">
          <div class="summary-item">
            <p class="summary-title">{{ card.title }}</p>
            <p class="summary-value" :class="card.accent ? 'accent' : ''">
              <template v-if="card.type === 'currency'">
                ¥{{ formatCurrency(card.value) }}
              </template>
              <template v-else>
                {{ formatPercent(card.value) }}
              </template>
            </p>
            <p class="summary-desc">{{ card.desc }}</p>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="20" class="chart-row">
      <el-col :xs="24" :lg="12">
        <el-card class="chart-card payment-breakdown-card" shadow="never" v-loading="loading">
          <template #header>
            <div class="chart-header">
              <div>
                <h3>支付构成分析</h3>
                <p class="chart-subtitle">多渠道资金占比，区分现金流入与权益消耗</p>
              </div>
              <div class="payment-grand-total" v-if="hasPaymentData">
                <span class="total-label">支付总额</span>
                <span class="total-value">¥{{ formatCurrency(paymentBreakdown.grandTotal) }}</span>
              </div>
            </div>
          </template>

          <!-- 分组条形图展示 -->
          <div v-if="hasPaymentData" class="payment-breakdown">
            <div
              v-for="group in paymentBreakdown.groups"
              :key="group.groupId"
              class="payment-group"
            >
              <!-- 分组标题 -->
              <div class="group-header" :style="{ borderLeftColor: group.color }">
                <div class="group-info">
                  <span class="group-name">{{ group.groupName }}</span>
                  <span class="group-desc">{{ group.description }}</span>
                </div>
                <div class="group-stats">
                  <span class="group-total">¥{{ formatCurrency(group.total) }}</span>
                  <span class="group-ratio">{{ formatPercent(group.ratio) }}</span>
                </div>
              </div>

              <!-- 明细条形图 -->
              <div class="group-items">
                <div
                  v-for="item in group.items"
                  :key="item.code"
                  class="payment-item"
                >
                  <div class="item-label">
                    <span class="item-name">{{ item.name }}</span>
                  </div>
                  <div class="item-bar-wrapper">
                    <div class="item-bar-bg">
                      <div
                        class="item-bar"
                        :style="{
                          width: `${item.barWidth}%`,
                          backgroundColor: group.color
                        }"
                      ></div>
                    </div>
                  </div>
                  <div class="item-stats">
                    <span class="item-amount">¥{{ formatCurrency(item.amount) }}</span>
                    <span class="item-ratio">{{ formatPercent(item.ratio) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="chart-empty">
            {{ loading ? '数据加载中...' : '暂无支付数据，请调整筛选条件' }}
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="chart-card" shadow="never" v-loading="loading">
          <template #header>
            <div class="chart-header">
              <div>
                <h3>异常损耗监控</h3>
                <p class="chart-subtitle">对比不同{{ anomalyDimensionLabel }}的赠送 vs 免单</p>
              </div>
            </div>
          </template>
          <div class="chart-body">
            <div ref="anomalyChartRef" class="chart-container tall"></div>
            <div v-if="!hasAnomalyData" class="chart-empty">
              {{ loading ? '数据加载中...' : '暂无异常损耗数据' }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick, inject } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { queryStats, getDateRange } from '@/api/stats'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'

// 注入全局门店选择状态
const currentStore = inject('currentStore', ref('all'))

// 移动端检测
const isMobile = ref(false)
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

// 支付方式分组元数据
const PAYMENT_GROUP_META = {
  income: {
    label: '收入类',
    description: '现金流入',
    color: '#52c41a',
    order: 1
  },
  prepaid: {
    label: '预存消耗',
    description: '权益抵扣',
    color: '#1890ff',
    order: 2
  },
  loss: {
    label: '损耗类',
    description: '非收入抵扣',
    color: '#f5222d',
    order: 3
  }
}

// 支付方式配置（key -> 分类映射）
const PAYMENT_CATEGORY_CONFIG = [
  // 收入类：真正的现金流入
  { key: 'pay_wechat', label: '微信支付', group: 'income' },
  { key: 'pay_alipay', label: '支付宝', group: 'income' },
  { key: 'pay_scan', label: '扫码支付', group: 'income' },
  { key: 'pay_cash', label: '现金', group: 'income' },
  { key: 'pay_pos', label: 'POS机', group: 'income' },
  { key: 'pay_pos_card', label: 'POS银行卡', group: 'income' },
  { key: 'pay_douyin', label: '抖音核销', group: 'income' },
  { key: 'pay_meituan', label: '美团核销', group: 'income' },
  { key: 'pay_gaode', label: '高德核销', group: 'income' },
  { key: 'pay_fubei', label: '付呗支付', group: 'income' },
  { key: 'pay_waiter', label: '服务员收款', group: 'income' },
  { key: 'pay_groupon', label: '团购核销', group: 'income' },
  // 预存消耗类：之前已收到的钱
  { key: 'pay_member', label: '会员支付(合计)', group: 'prepaid', exclusive: true },
  { key: 'pay_member_principal', label: '会员本金', group: 'prepaid' },
  { key: 'pay_member_gift', label: '会员赠送', group: 'prepaid' },
  { key: 'pay_deposit', label: '定金抵扣', group: 'prepaid' },
  // 损耗类：非收入抵扣
  { key: 'pay_manager_sign', label: '店长签单', group: 'loss' },
  { key: 'pay_employee_credit', label: '员工扣款', group: 'loss' },
  { key: 'pay_entertainment', label: '招待抵扣', group: 'loss' },
  { key: 'pay_expired_wine', label: '过期取酒', group: 'loss' },
  { key: 'pay_performance_commission', label: '演绎提成', group: 'loss' },
  { key: 'pay_marketing_commission', label: '营销提成', group: 'loss' },
  { key: 'pay_member_disabled', label: '会员停用', group: 'loss' },
  { key: 'pay_staff_discount', label: '人员打折', group: 'loss' },
  { key: 'pay_triple_recharge', label: '三倍充值活动', group: 'loss' },
  { key: 'pay_inter_account', label: '往来款', group: 'loss' }
]

// 构建快速查找映射
const PAYMENT_KEY_TO_CONFIG = PAYMENT_CATEGORY_CONFIG.reduce((acc, cfg) => {
  acc[cfg.key] = cfg
  return acc
}, {})

// 动态支付方式的分类猜测（基于关键字）
const guessPaymentGroup = (key) => {
  const lowerKey = key.toLowerCase()
  // 收入类关键字
  if (['wechat', 'alipay', 'cash', 'pos', 'scan', 'douyin', 'meituan', 'gaode', 'fubei', 'waiter', 'groupon'].some(k => lowerKey.includes(k))) {
    return 'income'
  }
  // 预存类关键字
  if (['member', 'deposit', 'prepaid', 'balance'].some(k => lowerKey.includes(k))) {
    return 'prepaid'
  }
  // 默认归为损耗类
  return 'loss'
}

const createEmptyPaymentTotals = () =>
  PAYMENT_CATEGORY_CONFIG.reduce((acc, { key }) => {
    acc[key] = 0
    return acc
  }, {})

const dateRange = ref([])
const anomalyDimension = ref('employee')
const currentUser = ref(null)
const financialSeriesRows = ref([])
const summaryData = ref(null) // 新增：保存后端返回的全局汇总数据
const loading = ref(false)

const anomalyChartRef = ref(null)
const chartInstances = {
  anomaly: null
}

const dateRangeStorageKey = 'viewState:FinancialAnalysis:dateRange'
const DEFAULT_TOP_N = 20
let activeController = null
let latestRequestToken = 0

const isReadyToQuery = computed(() => isValidDateRange(dateRange.value))

const anomalyDimensionLabel = computed(() =>
  anomalyDimension.value === 'store' ? '门店' : '员工'
)

const toNumber = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const formatCurrency = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '--'
  }
  return numeric.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatPercent = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '--'
  }
  return `${(numeric * 100).toFixed(2)}%`
}

const aggregatedTotals = computed(() => {
  // 初始化基础累加器
  const acc = {
    bill_total: 0,
    sales_amount: 0,
    actual: 0,
    credit_amount: 0,
    discount_amount: 0,
    free_amount: 0,
    round_off_amount: 0,
    gift_amount: 0,
    free_series: 0,
    orders: 0,
    ...createEmptyPaymentTotals(),
    // 动态支付方式（从 extra_info / extra_payments 中收集）
    _dynamicPayments: {}
  }

  // 如果后端返回了全局汇总数据，优先使用全局数据
  if (summaryData.value) {
    const data = summaryData.value
    acc.bill_total = toNumber(data.bill_total ?? data.sales_amount)
    acc.sales_amount = toNumber(data.sales_amount)
    acc.actual = toNumber(data.actual)
    acc.credit_amount = toNumber(data.credit_amount)
    acc.discount_amount = toNumber(data.discount_amount)
    acc.free_amount = toNumber(data.free_amount)
    acc.round_off_amount = toNumber(data.round_off_amount)
    acc.gift_amount = toNumber(data.gift_amount)
    acc.free_series = toNumber(data.free_amount)
    acc.orders = toNumber(data.orders)

    // 核心支付方式字段
    PAYMENT_CATEGORY_CONFIG.forEach(({ key }) => {
      acc[key] = toNumber(data[key])
    })

    // 处理全局动态支付方式
    if (data.extra_payments && typeof data.extra_payments === 'object') {
      Object.entries(data.extra_payments).forEach(([key, value]) => {
        if (acc[key] !== undefined) {
          acc[key] += toNumber(value)
        } else {
          acc._dynamicPayments[key] = (acc._dynamicPayments[key] || 0) + toNumber(value)
        }
      })
    }
    return acc
  }

  // 兜底逻辑：如果后端没有返回全局汇总，则回退到对当前行（Top-N）进行累加
  financialSeriesRows.value.forEach((row) => {
    acc.bill_total += toNumber(row.bill_total ?? row.sales_amount)
    acc.sales_amount += toNumber(row.sales_amount)
    acc.actual += toNumber(row.actual)
    acc.credit_amount += toNumber(row.credit_amount)
    acc.discount_amount += toNumber(row.discount_amount)
    acc.free_amount += toNumber(row.free_amount)
    acc.round_off_amount += toNumber(row.round_off_amount)
    acc.gift_amount += toNumber(row.gift_amount)
    acc.free_series += toNumber(row.free_amount)
    acc.orders += toNumber(row.orders)

    // 核心支付方式字段
    PAYMENT_CATEGORY_CONFIG.forEach(({ key }) => {
      acc[key] += toNumber(row[key])
    })

    // 从 extra_payments JSON 读取（如果存在）
    if (row.extra_payments && typeof row.extra_payments === 'object') {
      Object.entries(row.extra_payments).forEach(([key, value]) => {
        const normalizedKey = key.startsWith('pay_') ? key : `pay_${key}`
        if (acc[normalizedKey] !== undefined) {
          acc[normalizedKey] += toNumber(value)
        } else {
          acc._dynamicPayments[normalizedKey] = (acc._dynamicPayments[normalizedKey] || 0) + toNumber(value)
        }
      })
    }

    // 从 extra_info JSON 读取支付方式（cleaner 打包的动态支付）
    if (row.extra_info && typeof row.extra_info === 'object') {
      Object.entries(row.extra_info).forEach(([key, value]) => {
        if (key.startsWith('pay_')) {
          if (acc[key] !== undefined) {
            acc[key] += toNumber(value)
          } else {
            acc._dynamicPayments[key] = (acc._dynamicPayments[key] || 0) + toNumber(value)
          }
        }
      })
    }
  })

  return acc
})

const summaryCards = computed(() => {
  const totals = aggregatedTotals.value
  const receivable = totals.bill_total || totals.sales_amount
  const salesAmount = toNumber(totals.sales_amount)
  const actualRate = salesAmount ? toNumber(totals.actual) / salesAmount : 0
  return [
    {
      title: '实际总应收',
      value: receivable,
      desc: '账单合计金额 (GMV)',
      type: 'currency'
    },
    {
      title: '总实收',
      value: totals.actual,
      desc: '已到账金额',
      type: 'currency'
    },
    {
      title: '实收转化率',
      value: actualRate,
      desc: '实收 / 销售金额',
      type: 'percent',
      accent: true
    },
    {
      title: '总挂账',
      value: totals.credit_amount,
      desc: '待回款签单',
      type: 'currency'
    }
  ]
})

// 支付方式分组数据（用于分组条形图展示）
const paymentBreakdown = computed(() => {
  const totals = aggregatedTotals.value
  
  // 收集所有支付方式及其金额
  const paymentItems = []

  // 处理会员支付互斥：优先使用明细
  const memberPrincipal = toNumber(totals.pay_member_principal)
  const memberGift = toNumber(totals.pay_member_gift)
  const memberTotal = toNumber(totals.pay_member)
  const useMemberDetail = memberPrincipal > 0 || memberGift > 0

  // 1. 从配置中收集核心支付方式
  PAYMENT_CATEGORY_CONFIG.forEach(({ key, label, group, exclusive }) => {
    // 会员支付互斥处理
    if (key === 'pay_member' && useMemberDetail) return
    if ((key === 'pay_member_principal' || key === 'pay_member_gift') && !useMemberDetail && memberTotal > 0) {
      // 没有明细但有合计时，使用合计
      return
    }

    const amount = toNumber(totals[key])
    if (amount > 0) {
      paymentItems.push({
        code: key.replace('pay_', ''),
        key,
        name: label,
        amount,
        group
      })
    }
  })

  // 2. 收集动态支付方式（从 extra_info / extra_payments）
  const dynamicPayments = totals._dynamicPayments || {}
  Object.entries(dynamicPayments).forEach(([key, amount]) => {
    if (amount > 0) {
      const code = key.replace('pay_', '')
      // 尝试从配置中查找标签，否则使用 code
      const config = PAYMENT_KEY_TO_CONFIG[key]
      const group = config?.group || guessPaymentGroup(key)
      paymentItems.push({
        code,
        key,
        name: config?.label || code,
        amount,
        group,
        isDynamic: true
      })
    }
  })

  // 3. 计算总金额
  const grandTotal = paymentItems.reduce((sum, item) => sum + item.amount, 0)

  // 4. 按分组聚合
  const groupMap = {}
  Object.entries(PAYMENT_GROUP_META).forEach(([groupId, meta]) => {
    groupMap[groupId] = {
      groupId,
      groupName: meta.label,
      description: meta.description,
      color: meta.color,
      order: meta.order,
      total: 0,
      ratio: 0,
      items: []
    }
  })

  // 5. 将支付项分配到对应分组
  paymentItems.forEach((item) => {
    const group = groupMap[item.group]
    if (group) {
      group.items.push({
        ...item,
        ratio: grandTotal ? item.amount / grandTotal : 0
      })
      group.total += item.amount
    }
  })

  // 6. 计算分组占比，并对每个分组内的项目按金额降序排序
  const maxAmount = Math.max(...paymentItems.map(i => i.amount), 1)
  
  Object.values(groupMap).forEach((group) => {
    group.ratio = grandTotal ? group.total / grandTotal : 0
    // 按金额降序排序
    group.items.sort((a, b) => b.amount - a.amount)
    // 计算条形图宽度（相对于最大值）
    group.items.forEach((item) => {
      item.barWidth = maxAmount ? (item.amount / maxAmount) * 100 : 0
    })
  })

  // 7. 过滤空分组，按 order 排序
  const groups = Object.values(groupMap)
    .filter((g) => g.items.length > 0)
    .sort((a, b) => a.order - b.order)

  return {
    grandTotal,
    groups
  }
})

const hasPaymentData = computed(() => paymentBreakdown.value.groups.length > 0)

const anomalyDataset = computed(() => {
  const rows = [...financialSeriesRows.value]
  const dataset = rows
    .map((row) => {
      let label = row.dimension_label || row.dimension_key || '未命名'
      // 当维度为员工且未选择特定门店时，在名字后面备注门店
      if (anomalyDimension.value === 'employee' && (!currentStore.value || currentStore.value === 'all')) {
        // 优先使用后端返回的 store_name 或通过 store_id 匹配到的名称
        const storeName = row.store_name || 
                        row.store_label || 
                        row.extra_info?.store_name
        
        if (storeName) {
          label += ` (${storeName})`
        }
      }
      return {
        label,
        gift: toNumber(row.gift_amount ?? row.gift),
        free: toNumber(row.free_amount ?? row.free_series)
      }
    })
    .sort((a, b) => b.gift + b.free - (a.gift + a.free))
  return dataset.slice(0, DEFAULT_TOP_N)
})

const hasAnomalyData = computed(() =>
  anomalyDataset.value.some((item) => item.gift > 0 || item.free > 0)
)

const ensureChartInstance = (key) => {
  const refMap = {
    anomaly: anomalyChartRef
  }
  if (chartInstances[key]) {
    return chartInstances[key]
  }
  const dom = refMap[key]?.value
  if (!dom) {
    return null
  }
  chartInstances[key] = echarts.init(dom)
  return chartInstances[key]
}

const disposeCharts = () => {
  Object.keys(chartInstances).forEach((key) => {
    if (chartInstances[key]) {
      chartInstances[key].dispose()
      chartInstances[key] = null
    }
  })
}

const buildAnomalyOption = () => {
  if (!hasAnomalyData.value) {
    return null
  }
  const categories = anomalyDataset.value.map((item) => item.label)
  const giftData = anomalyDataset.value.map((item) => Number(item.gift.toFixed(2)))
  const freeData = anomalyDataset.value.map((item) => Number(item.free.toFixed(2)))
  
  // 移动端配置调整
  const gridConfig = isMobile.value
    ? { left: 10, right: 15, bottom: 30, top: 40, containLabel: true }
    : { left: 20, right: 30, bottom: 20, top: 40, containLabel: true }

  const xAxisLabelConfig = isMobile.value
    ? {
        formatter: (value) => {
          // 移动端使用更简洁的格式
          if (value >= 10000) {
            return '¥' + (value / 10000).toFixed(1) + '万'
          } else if (value >= 1000) {
            return '¥' + (value / 1000).toFixed(0) + 'K'
          } else {
            return '¥' + value.toFixed(0)
          }
        },
        fontSize: 10,
        rotate: 0
      }
    : {
        formatter: (value) => `¥${formatCurrency(value)}`
      }

  const yAxisLabelConfig = isMobile.value
    ? {
        formatter: (value) => {
          // 移动端截断过长的名称（考虑到增加了门店名，放宽到12个字符）
          if (value && value.length > 12) {
            return value.slice(0, 11) + '...'
          }
          return value || '未命名'
        },
        fontSize: 11
      }
    : {
        formatter: (value) => value || '未命名'
      }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      valueFormatter: (value) => `¥${formatCurrency(value)}`
    },
    legend: {
      top: 0,
      textStyle: {
        fontSize: isMobile.value ? 11 : 12
      }
    },
    grid: gridConfig,
    xAxis: {
      type: 'value',
      axisLabel: xAxisLabelConfig
    },
    yAxis: {
      type: 'category',
      data: categories,
      axisLabel: yAxisLabelConfig
    },
    series: [
      {
        name: '赠送金额',
        type: 'bar',
        data: giftData,
        barMaxWidth: isMobile.value ? 20 : 32,
        barGap: '20%',
        barCategoryGap: '30%'
      },
      {
        name: '免单金额',
        type: 'bar',
        data: freeData,
        barMaxWidth: isMobile.value ? 20 : 32,
        barGap: '20%',
        barCategoryGap: '30%'
      }
    ]
  }
}

const updateAnomalyChart = () => {
  const chart = ensureChartInstance('anomaly')
  if (!chart) return
  const option = buildAnomalyOption()
  if (!option) {
    chart.clear()
    return
  }
  chart.setOption(option, true)
}

const handleResize = () => {
  checkMobile()
  Object.values(chartInstances).forEach((instance) => {
    instance?.resize()
  })
  // 移动端尺寸变化时重新更新图表配置
  nextTick(() => {
    updateAnomalyChart()
  })
}

const triggerAutoQuery = () => {
  if (isReadyToQuery.value) {
    fetchFinancialStats()
  }
}

const handleDateRangeChange = () => {
  if (!isReadyToQuery.value) {
    return
  }
  writeSessionJSON(dateRangeStorageKey, dateRange.value)
  triggerAutoQuery()
}

const fetchFinancialStats = async () => {
  if (!isReadyToQuery.value) {
    ElMessage.warning('请选择完整的时间范围后再查询')
    return
  }

  const [startDate, endDate] = dateRange.value
  const params = {
    table: 'booking',
    start_date: startDate,
    end_date: endDate,
    dimension: anomalyDimension.value,
    granularity: 'day',
    top_n: DEFAULT_TOP_N
  }
  // 使用全局门店选择
  if (currentStore.value && currentStore.value !== 'all') {
    const parsedStoreId = parseInt(currentStore.value, 10)
    if (Number.isFinite(parsedStoreId)) {
      params.store_id = parsedStoreId
    }
  }

  if (activeController) {
    activeController.abort()
    activeController = null
  }

  const controller = new AbortController()
  activeController = controller
  const requestId = ++latestRequestToken
  loading.value = true

  try {
    const response = await queryStats(params, { signal: controller.signal })
    if (requestId !== latestRequestToken) {
      return
    }
    const payload = response?.data || {}
    if (response?.success) {
      const seriesRows = Array.isArray(payload.series_rows) ? payload.series_rows : []
      financialSeriesRows.value = seriesRows.map((row) => ({
        ...row,
        dimension_label: row.dimension_label || row.dimension_key || '--'
      }))
      summaryData.value = payload.summary || null // 保存全局汇总
    } else {
      financialSeriesRows.value = []
      summaryData.value = null
    }
  } catch (error) {
    if (error?.name === 'AbortError' || error?.message === 'canceled') {
      return
    }
    if (requestId !== latestRequestToken) {
      return
    }
    console.error('[FinancialAnalysis] 查询失败:', error)
    ElMessage.error('财务专项数据查询失败，请稍后重试')
    financialSeriesRows.value = []
  } finally {
    if (requestId === latestRequestToken) {
      loading.value = false
    }
    if (activeController === controller) {
      activeController = null
    }
  }
}

const loadCurrentUser = () => {
  try {
    const raw = localStorage.getItem('user')
    if (raw) {
      currentUser.value = JSON.parse(raw)
    }
  } catch (error) {
    console.error('[FinancialAnalysis] 读取用户信息失败', error)
  }
}

const buildFallbackRange = () => {
  const today = new Date()
  const end = today.toISOString().split('T')[0]
  const startDate = new Date(today)
  startDate.setDate(today.getDate() - 6)
  const start = startDate.toISOString().split('T')[0]
  return [start, end]
}

const restoreDateRange = async () => {
  const saved = readSessionJSON(dateRangeStorageKey, null)
  if (isValidDateRange(saved)) {
    dateRange.value = saved
    return
  }
  try {
    const rangeRes = await getDateRange('booking')
    if (rangeRes?.success && rangeRes.suggested_start && rangeRes.suggested_end) {
      dateRange.value = [rangeRes.suggested_start, rangeRes.suggested_end]
      writeSessionJSON(dateRangeStorageKey, dateRange.value)
      return
    }
  } catch (error) {
    console.error('[FinancialAnalysis] 获取日期范围失败:', error)
  }
  dateRange.value = buildFallbackRange()
  writeSessionJSON(dateRangeStorageKey, dateRange.value)
}

watch(
  () => anomalyDataset.value,
  () => {
    nextTick(updateAnomalyChart)
  },
  { deep: true }
)

watch(
  () => currentStore.value,
  () => {
    triggerAutoQuery()
    nextTick(() => handleResize())
  }
)

watch(
  () => anomalyDimension.value,
  () => {
    triggerAutoQuery()
    nextTick(() => handleResize())
  }
)

watch(
  () => paymentBreakdown.value,
  () => {
    nextTick(() => handleResize())
  },
  { deep: true }
)

onMounted(async () => {
  checkMobile()
  loadCurrentUser()
  await restoreDateRange()
  await nextTick()
  nextTick(() => {
    ensureChartInstance('anomaly')
    handleResize()
  })
  if (isReadyToQuery.value) {
    fetchFinancialStats()
  }
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  disposeCharts()
  if (activeController) {
    activeController.abort()
  }
})
</script>

<style lang="scss" scoped>
.financial-analysis {
  display: flex;
  flex-direction: column;
  gap: 20px;

  .card-header {
    .title-row {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      flex-wrap: wrap;

      .title-text {
        h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .card-subtitle {
          margin: 4px 0 0;
          color: #909399;
          font-size: 13px;
        }
      }

      .el-tag {
        flex-shrink: 0;
        margin-top: 2px;
      }
    }
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    align-items: center;

    .filter-item {
      display: flex;
      align-items: center;
      gap: 12px;

      :deep(.el-date-editor--daterange) {
        width: 360px;
      }

      :deep(.el-select) {
        width: 180px;
      }

      :deep(.el-input) {
        width: 180px;
      }
    }

    .dimension-switch {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .filter-label {
      font-size: 13px;
      color: #606266;
      white-space: nowrap;
    }
  }

  .summary-card {
    .summary-item {
      border-radius: 12px;
      padding: 18px;
      background: #f5f7fa;

      .summary-title {
        margin: 0;
        color: #909399;
        font-size: 13px;
      }

      .summary-value {
        margin: 6px 0;
        font-size: 24px;
        font-weight: 600;
        color: #303133;

        &.accent {
          color: #409eff;
        }
      }

      .summary-desc {
        margin: 0;
        color: #a0a3aa;
        font-size: 12px;
      }
    }
  }

  .chart-row {
    align-items: stretch;

    .el-col {
      display: flex;
    }

    .chart-card {
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 100%;

      :deep(.el-card__body) {
        flex: 1;
        display: flex;
        flex-direction: column;
      }
    }

    .chart-body {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
  }

  .chart-card {
    .chart-header {
      display: flex;
      align-items: center;
      justify-content: space-between;

      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }

      .chart-subtitle {
        margin: 4px 0 0;
        color: #909399;
        font-size: 13px;
      }
    }

    .chart-body {
      min-height: 320px;
      display: flex;
      align-items: stretch;
      justify-content: center;
      position: relative;
      flex: 1;
    }

    .chart-container {
      width: 100%;
      min-height: 320px;
      height: 100%;

      &.tall {
        min-height: 560px;
      }
    }

    .chart-empty {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: rgba(255, 255, 255, 0.9);
      z-index: 10;
      color: #909399;
      font-size: 14px;
    }
  }

  // 支付构成卡片特殊样式
  .payment-breakdown-card {
    .chart-header {
      .payment-grand-total {
        text-align: right;

        .total-label {
          display: block;
          font-size: 12px;
          color: #909399;
        }

        .total-value {
          font-size: 20px;
          font-weight: 600;
          color: #303133;
        }
      }
    }

    // 分组条形图容器
    .payment-breakdown {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    // 每个分组
    .payment-group {
      .group-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: #f5f7fa;
        border-radius: 8px;
        border-left: 4px solid;
        margin-bottom: 12px;

        .group-info {
          .group-name {
            font-size: 15px;
            font-weight: 600;
            color: #303133;
          }

          .group-desc {
            margin-left: 8px;
            font-size: 12px;
            color: #909399;
          }
        }

        .group-stats {
          text-align: right;

          .group-total {
            font-size: 16px;
            font-weight: 600;
            color: #303133;
          }

          .group-ratio {
            margin-left: 8px;
            font-size: 13px;
            color: #606266;
          }
        }
      }

      // 分组内的明细项
      .group-items {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding-left: 20px;
      }

      .payment-item {
        display: grid;
        grid-template-columns: 100px 1fr 140px;
        align-items: center;
        gap: 12px;
        padding: 6px 0;

        .item-label {
          .item-name {
            font-size: 13px;
            color: #606266;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
        }

        .item-bar-wrapper {
          .item-bar-bg {
            width: 100%;
            height: 20px;
            background: #f0f2f5;
            border-radius: 4px;
            overflow: hidden;

            .item-bar {
              height: 100%;
              border-radius: 4px;
              transition: width 0.3s ease;
              min-width: 4px;
            }
          }
        }

        .item-stats {
          display: flex;
          justify-content: flex-end;
          gap: 8px;

          .item-amount {
            font-size: 13px;
            font-weight: 500;
            color: #303133;
            min-width: 80px;
            text-align: right;
          }

          .item-ratio {
            font-size: 12px;
            color: #909399;
            min-width: 50px;
            text-align: right;
          }
        }
      }
    }
  }

  @media (max-width: 768px) {
    gap: 15px;

    .filter-card {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 12px;
      }

      .card-header {
        .title-row {
          flex-direction: column;
          align-items: flex-start;
          gap: 6px;

          .title-text {
            h2 {
              font-size: 16px;
            }

            .card-subtitle {
              font-size: 12px;
            }
          }
        }
      }
    }

    .filters {
      flex-direction: row;
      flex-wrap: wrap;
      gap: 12px;
      align-items: stretch;

      .filter-item {
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;

        .filter-label {
          font-size: 12px;
        }

        :deep(.el-select),
        :deep(.el-input) {
          width: 100% !important;
        }

        // 时间范围选择器独占一行
        &:first-child {
          width: 100%;
        }

        // 门店选择器和异常监控维度在同一行
        &:nth-child(2) {
          width: calc(50% - 6px);
        }

        // 时间范围选择器移动端优化
        :deep(.el-date-editor--daterange) {
          width: 100% !important;
          padding: 3px 5px;
          
          .el-range-separator {
            padding: 0 4px;
            font-size: 12px;
            width: auto;
          }
          
          .el-range-input {
            font-size: 12px;
            width: 42%;
          }

          .el-range__icon,
          .el-range__close-icon {
            font-size: 12px;
            width: 18px;
          }
        }
      }

      .dimension-switch {
        width: calc(50% - 6px);
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;

        :deep(.el-radio-group) {
          width: 100%;
          display: flex;

          .el-radio-button {
            flex: 1;

            .el-radio-button__inner {
              width: 100%;
              height: 32px;
              line-height: 30px;
              padding: 0 12px;
            }
          }
        }
      }
    }

    .summary-card {
      :deep(.el-card__body) {
        padding: 12px;
      }

      :deep(.el-row) {
        .el-col {
          margin-bottom: 12px;

          &:last-child {
            margin-bottom: 0;
          }
        }
      }

      .summary-item {
        padding: 14px;

        .summary-title {
          font-size: 12px;
        }

        .summary-value {
          font-size: 20px;
        }

        .summary-desc {
          font-size: 11px;
        }
      }
    }

    .chart-row {
      .el-col {
        margin-bottom: 15px;

        &:last-child {
          margin-bottom: 0;
        }
      }
    }

    .chart-card {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 12px;
      }

      .chart-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;

        h3 {
          font-size: 14px;
        }

        .chart-subtitle {
          font-size: 12px;
        }
      }

      .chart-body {
        min-height: 280px;
      }

      .chart-container {
        min-height: 280px;

        &.tall {
          min-height: 480px;
        }
      }
    }

    // 支付构成卡片移动端优化
    .payment-breakdown-card {
      .chart-header {
        .payment-grand-total {
          margin-top: 8px;
          text-align: left;

          .total-label {
            display: inline;
            margin-right: 8px;
          }

          .total-value {
            font-size: 18px;
          }
        }
      }

      .payment-breakdown {
        gap: 16px;
      }

      .payment-group {
        .group-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
          padding: 10px 12px;

          .group-info {
            .group-name {
              font-size: 14px;
            }

            .group-desc {
              font-size: 11px;
            }
          }

          .group-stats {
            width: 100%;
            display: flex;
            justify-content: space-between;
            text-align: left;

            .group-total {
              font-size: 15px;
            }

            .group-ratio {
              font-size: 12px;
            }
          }
        }

        .group-items {
          padding-left: 12px;
          gap: 6px;
        }

        .payment-item {
          grid-template-columns: 80px 1fr 100px;
          gap: 8px;
          padding: 4px 0;

          .item-label {
            .item-name {
              font-size: 12px;
            }
          }

          .item-bar-wrapper {
            .item-bar-bg {
              height: 16px;
            }
          }

          .item-stats {
            gap: 4px;

            .item-amount {
              font-size: 12px;
              min-width: 60px;
            }

            .item-ratio {
              font-size: 11px;
              min-width: 40px;
            }
          }
        }
      }
    }
  }

  @media (max-width: 480px) {
    gap: 12px;

    .filter-card {
      .card-header {
        h2 {
          font-size: 15px;
        }
      }
    }

    .summary-card {
      .summary-item {
        padding: 12px;

        .summary-title {
          font-size: 11px;
        }

        .summary-value {
          font-size: 18px;
        }

        .summary-desc {
          font-size: 10px;
        }
      }
    }

    .chart-card {
      .chart-header {
        h3 {
          font-size: 13px;
        }

        .chart-subtitle {
          font-size: 11px;
        }
      }

      .chart-body {
        min-height: 250px;
      }

      .chart-container {
        min-height: 250px;

        &.tall {
          min-height: 400px;
        }
      }
    }

    .payment-breakdown-card {
      .payment-group {
        .group-header {
          padding: 8px 10px;

          .group-info {
            .group-name {
              font-size: 13px;
            }

            .group-desc {
              font-size: 10px;
            }
          }

          .group-stats {
            .group-total {
              font-size: 14px;
            }

            .group-ratio {
              font-size: 11px;
            }
          }
        }

        .group-items {
          padding-left: 8px;
        }

        .payment-item {
          grid-template-columns: 70px 1fr 85px;
          gap: 6px;

          .item-label {
            .item-name {
              font-size: 11px;
            }
          }

          .item-bar-wrapper {
            .item-bar-bg {
              height: 14px;
            }
          }

          .item-stats {
            .item-amount {
              font-size: 11px;
              min-width: 50px;
            }

            .item-ratio {
              font-size: 10px;
              min-width: 35px;
            }
          }
        }
      }
    }
  }
}
</style>

