<template>
  <div class="dashboard" v-loading="loading">
    <div class="dashboard-header">
      <div class="dashboard-title">经营数据看板</div>
      <el-date-picker
        v-model="selectedDate"
        type="date"
        placeholder="选择基准日期"
        format="YYYY-MM-DD"
        value-format="YYYY-MM-DD"
        clearable
        :disabled="loading"
      />
    </div>

    <!-- KPI 卡片 -->
    <section class="kpi-section">
      <div class="kpi-section-title">财务概览</div>
      <el-row :gutter="20" class="kpi-cards">
        <el-col :xs="24" :sm="12" :md="financialColSpan" :span="financialColSpan" v-for="kpi in financialKpis" :key="`fin-${kpi.title}`">
          <el-card class="kpi-card" :body-style="{ padding: '20px' }">
            <div class="kpi-icon" :style="{ background: kpi.color }">
              <el-icon size="24"><component :is="kpi.icon" /></el-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-title">{{ kpi.title }}</div>
              <div class="kpi-value" :style="{ color: kpi.valueColor || '#303133' }">{{ kpi.value }}</div>
              <div class="kpi-change" :class="kpi.trend">
                <el-icon v-if="kpi.trend === 'up'"><Top /></el-icon>
                <el-icon v-else><Bottom /></el-icon>
                {{ kpi.change }}
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </section>

    <section class="kpi-section">
      <div class="kpi-section-title">经营效能</div>
      <el-row :gutter="20" class="kpi-cards efficiency">
        <el-col :xs="24" :sm="12" :md="efficiencyColSpan" :span="efficiencyColSpan" v-for="kpi in efficiencyKpis" :key="`eff-${kpi.title}`">
          <el-card class="kpi-card" :body-style="{ padding: '20px' }">
            <div class="kpi-icon" :style="{ background: kpi.color }">
              <el-icon size="24"><component :is="kpi.icon" /></el-icon>
            </div>
            <div class="kpi-content">
              <div class="kpi-title">{{ kpi.title }}</div>
              <div class="kpi-value" :style="{ color: kpi.valueColor || '#303133' }">{{ kpi.value }}</div>
              <div class="kpi-change" :class="kpi.trend">
                <el-icon v-if="kpi.trend === 'up'"><Top /></el-icon>
                <el-icon v-else><Bottom /></el-icon>
                {{ kpi.change }}
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </section>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts">
      <el-col :xs="24" :sm="24" :md="16" :lg="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>📈 营收月度趋势（近12个月）</span>
              <div class="trend-toggle">
                <el-radio-group v-model="trendMetric" size="small">
                  <el-radio-button label="revenue">营收金额</el-radio-button>
                  <el-radio-button label="orders">开台单数</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div class="chart-container" ref="trendChartRef"></div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="24" :md="8" :lg="8">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>🏪 门店排行 TOP5</span>
            </div>
          </template>
          <div class="chart-container" ref="storeChartRef"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 排行榜 -->
    <el-row :gutter="20" class="rankings">
      <el-col :xs="24" :sm="24" :md="12" :lg="12">
        <el-card class="ranking-card">
          <template #header>
            <div class="card-header">
              <span>👑 员工业绩 TOP5</span>
            </div>
          </template>
          <div class="chart-container" ref="staffChartRef"></div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="24" :md="12" :lg="12">
        <el-card class="ranking-card">
          <template #header>
            <div class="card-header">
              <span>🍺 热销商品 TOP5</span>
            </div>
          </template>
          <div class="chart-container" ref="productChartRef"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, inject, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDashboardSummary } from '@/api/dashboard'
import { readSessionJSON, writeSessionJSON, isValidYmdDate } from '@/utils/viewState'

// 状态
const loading = ref(false)
const dashboardData = ref(null)
const selectedDate = ref('')
const selectedDateStorageKey = 'viewState:Dashboard:selectedDate'

const periodRangeLabel = computed(() => {
  const data = dashboardData.value
  if (!data) return '-'
  return formatPeriodRange(data.period_start, data.reference_date)
})

// 注入门店选择状态
const currentStore = inject('currentStore', ref(''))

// KPI 数据 (从 API 响应计算)
const financialKpis = computed(() => {
  const data = dashboardData.value
  if (!data) {
    return [
      { title: '当日实收', value: '-', change: '-', trend: 'up', icon: 'Money', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', valueColor: '#303133' },
      { title: '本月实收', value: '-', change: '-', trend: 'up', icon: 'TrendCharts', color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', valueColor: '#303133' },
      { title: '本月成本', value: '-', change: '-', trend: 'down', icon: 'WalletFilled', color: 'linear-gradient(135deg, #ffd86f 0%, #fc6262 100%)', valueColor: '#303133' },
      { title: '毛利率', value: '-', change: '-', trend: 'up', icon: 'PieChart', color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', valueColor: '#303133' },
    ]
  }

  return [
    { 
      title: '当日实收', 
      value: formatCurrency(data.yesterday_actual), 
      change: formatPercent(data.yesterday_change), 
      trend: data.yesterday_change >= 0 ? 'up' : 'down',
      icon: 'Money', 
      color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      valueColor: '#303133'
    },
    { 
      title: '本月实收', 
      value: formatCurrency(data.month_actual), 
      change: buildRangeWrappedText(`同比 ${formatPercent(data.month_change)}`), 
      trend: data.month_change >= 0 ? 'up' : 'down',
      icon: 'TrendCharts', 
      color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      valueColor: '#303133'
    },
    { 
      title: '本月成本',
      value: formatCurrency(data.month_cost),
      change: buildRangeWrappedText('累计成本'),
      trend: 'down',
      icon: 'WalletFilled',
      color: 'linear-gradient(135deg, #ffd86f 0%, #fc6262 100%)',
      valueColor: '#303133'
    },
    { 
      title: '毛利率', 
      value: formatPercent(data.profit_rate), 
      change: buildRangeWrappedText(`毛利 ${formatCurrency(data.month_profit)}`), 
      trend: 'up',
      icon: 'PieChart', 
      color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      valueColor: data.profit_rate < 0.35 ? '#f56c6c' : '#303133'
    },
  ]
})

const efficiencyKpis = computed(() => {
  const data = dashboardData.value
  if (!data) {
    return [
      { title: '包厢周转率', value: '-', change: '-', trend: 'up', icon: 'Histogram', color: 'linear-gradient(135deg, #7f7fd5 0%, #86a8e7 50%, #91eae4 100%)', valueColor: '#303133' },
      { title: '平均消费时长', value: '-', change: '-', trend: 'up', icon: 'Timer', color: 'linear-gradient(135deg, #43cea2 0%, #185a9d 100%)', valueColor: '#303133' },
      { title: '赠送率', value: '-', change: '-', trend: 'down', icon: 'Present', color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', valueColor: '#303133' },
    ]
  }

  return [
    { 
      title: '包厢周转率',
      value: formatTurnoverPercent(data.turnover_rate),
      change: buildRangeWrappedText(`开台 ${Number(data.total_orders || 0).toLocaleString('zh-CN')} 单`),
      trend: data.turnover_rate >= 1 ? 'up' : 'down',
      icon: 'Histogram',
      color: 'linear-gradient(135deg, #7f7fd5 0%, #86a8e7 50%, #91eae4 100%)',
      valueColor: '#303133'
    },
    { 
      title: '平均消费时长',
      value: formatDuration(data.avg_duration),
      change: buildRangeWrappedText('按月累计'),
      trend: 'up',
      icon: 'Timer',
      color: 'linear-gradient(135deg, #43cea2 0%, #185a9d 100%)',
      valueColor: '#303133'
    },
    { 
      title: '赠送率', 
      value: formatPercent(data.gift_rate), 
      change: buildRangeWrappedText('本月赠送'), 
      trend: 'down',
      icon: 'Present', 
      color: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
      valueColor: '#303133'
    },
  ]
})

const calcColSpan = (count) => {
  if (!count) return 6
  const span = Math.floor(24 / count)
  return span > 0 ? span : 6
}

const financialColSpan = computed(() => calcColSpan(financialKpis.value.length))
const efficiencyColSpan = computed(() => calcColSpan(efficiencyKpis.value.length))

// 格式化函数
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '-'
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

const formatPercent = (value) => {
  if (value === null || value === undefined) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(1)}%`
}

const extractDateParts = (value) => {
  if (!value) return null
  const normalized = String(value).slice(0, 10)
  const [year, month, day] = normalized.split('-')
  if (!year || !month || !day) return null
  return {
    month: month.padStart(2, '0'),
    day: day.padStart(2, '0')
  }
}

const formatPeriodRange = (start, end) => {
  const startParts = extractDateParts(start)
  const endParts = extractDateParts(end)
  if (!startParts || !endParts) return '-'
  return `${startParts.month}.${startParts.day} ~ ${endParts.month}.${endParts.day}`
}

const getPeriodRangePrefix = () => {
  const range = periodRangeLabel.value
  return range && range !== '-' ? `${range} ` : ''
}

const buildRangeWrappedText = (text) => {
  const prefix = getPeriodRangePrefix()
  if (!text) return prefix.trim() || '-'
  return prefix ? `${prefix}${text}` : text
}

const formatDuration = (value) => {
  if (value === null || value === undefined) return '-'
  const minutes = Number(value)
  if (Number.isNaN(minutes)) return '-'
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const mins = Math.round(minutes % 60)
    if (mins === 0) {
      return `${hours}小时`
    }
    return `${hours}小时${mins}分`
  }
  return `${minutes.toFixed(0)}分钟`
}

const formatTurnoverPercent = (value) => {
  if (value === null || value === undefined) return '-'
  return `${(Number(value) * 100).toFixed(0)}%`
}

// 图表 ref
const trendMetric = ref('revenue')
const trendSource = ref([])
const trendChartRef = ref(null)
const storeChartRef = ref(null)
const staffChartRef = ref(null)
const productChartRef = ref(null)

let charts = []
let trendChartInstance = null
const TREND_MONTH_WINDOW = 12

const getTrendReferenceDate = () => {
  if (dashboardData.value?.reference_date) {
    const parsed = new Date(dashboardData.value.reference_date)
    if (!Number.isNaN(parsed.getTime())) {
      return parsed
    }
  }
  if (selectedDate.value) {
    const parsed = new Date(selectedDate.value)
    if (!Number.isNaN(parsed.getTime())) {
      return parsed
    }
  }
  return null
}

const buildRecentMonths = (count = TREND_MONTH_WINDOW) => {
  const referenceDate = getTrendReferenceDate()
  if (!referenceDate) return []

  const months = []
  for (let i = count - 1; i >= 0; i -= 1) {
    const date = new Date(referenceDate.getFullYear(), referenceDate.getMonth() - i, 1)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    months.push(`${year}-${month}`)
  }
  return months
}

const monthKeyOf = (dateStr) => {
  if (!dateStr) return ''
  const s = String(dateStr)
  if (/^\d{4}-\d{2}/.test(s)) return s.slice(0, 7)
  return s
}

const buildTrendSeries = (metric) => {
  const months = buildRecentMonths()
  const isRevenue = metric === 'revenue'

  if (!months.length) {
    return { months: [], seriesData: [], hasData: false }
  }

  const monthMap = new Map()

  for (const item of trendSource.value || []) {
    const key = monthKeyOf(item.date)
    if (!key) continue

    const revenueValue = Number(item.revenue ?? item.value ?? 0)
    const ordersValue = Number(item.orders ?? 0)

    if (!Number.isFinite(revenueValue) && !Number.isFinite(ordersValue)) continue

    monthMap.set(key, {
      revenue: Number.isFinite(revenueValue) ? revenueValue : 0,
      orders: Number.isFinite(ordersValue) ? ordersValue : 0
    })
  }

  const seriesData = months.map((monthKey) => {
    const entry = monthMap.get(monthKey)
    const raw = entry ? (isRevenue ? entry.revenue : entry.orders) : 0
    const value = isRevenue ? Number((raw / 10000).toFixed(2)) : raw
    return { value, raw }
  })

  const hasData = seriesData.some(item => Number(item.raw) > 0)

  return { months, seriesData, hasData }
}

const setTrendEmptyState = () => {
  if (!trendChartInstance) return
  trendChartInstance.clear()
  trendChartInstance.setOption({
    title: {
      text: '暂无趋势数据',
      left: 'center',
      top: 'center',
      textStyle: {
        color: '#999',
        fontSize: 14
      }
    },
    xAxis: { show: false },
    yAxis: { show: false },
    series: []
  }, true)
}

const updateTrendChart = () => {
  if (!trendChartInstance) return
  const metric = trendMetric.value
  const isRevenue = metric === 'revenue'
  const { months, seriesData, hasData } = buildTrendSeries(metric)

  if (!months.length || !hasData) {
    setTrendEmptyState()
    return
  }

  const gradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: isRevenue ? 'rgba(102, 126, 234, 0.5)' : 'rgba(67, 206, 162, 0.35)' },
    { offset: 1, color: isRevenue ? 'rgba(102, 126, 234, 0.05)' : 'rgba(24, 90, 157, 0.05)' }
  ])

  trendChartInstance.setOption({
    title: { show: false },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const data = params[0]
        const raw = data?.data?.raw ?? data?.value ?? 0
        const label = data?.name || ''
        const numericRaw = Number(raw)
        const rawNumber = Number.isFinite(numericRaw) ? numericRaw : 0
        if (isRevenue) {
          return `${label}<br/>当月营收: ¥${rawNumber.toLocaleString()}`
        }
        return `${label}<br/>当月开台: ${rawNumber.toLocaleString()} 单`
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: months,
      axisLabel: {
        interval: 0,
        rotate: months.length > 8 ? 30 : 0,
        formatter: (value) => value
      }
    },
    yAxis: {
      type: 'value',
      name: isRevenue ? '金额（万元）' : '开台数（单）'
    },
    series: [{
      name: isRevenue ? '营收' : '开台数',
      type: 'line',
      smooth: true,
      data: seriesData,
      areaStyle: isRevenue ? { color: gradient } : undefined,
      lineStyle: { color: isRevenue ? '#667eea' : '#43cea2', width: 3 }
    }]
  }, true)
}

const initTrendChart = () => {
  if (!trendChartRef.value) return

  if (!trendChartInstance) {
    trendChartInstance = echarts.init(trendChartRef.value)
    charts.push(trendChartInstance)
  }

  updateTrendChart()
}

// 初始化门店排行
const initStoreChart = (topStores) => {
  if (!storeChartRef.value) return

  // 清理之前的图表实例
  const existingChart = echarts.getInstanceByDom(storeChartRef.value)
  if (existingChart) {
    existingChart.dispose()
    const index = charts.indexOf(existingChart)
    if (index > -1) {
      charts.splice(index, 1)
    }
  }

  const chart = echarts.init(storeChartRef.value)
  charts.push(chart)

  if (!topStores || topStores.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    })
    return
  }

  const names = topStores.map(item => item.name).reverse()
  const values = topStores.map(item => item.value).reverse()

  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: names
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#f093fb' },
          { offset: 1, color: '#f5576c' }
        ])
      },
      label: {
        show: true,
        position: 'right',
        formatter: (params) => `¥${(params.value / 10000).toFixed(1)}万`
      }
    }]
  })
}

// 初始化员工排行
const initStaffChart = (topEmployees) => {
  if (!staffChartRef.value) return

  // 清理之前的图表实例
  const existingChart = echarts.getInstanceByDom(staffChartRef.value)
  if (existingChart) {
    existingChart.dispose()
    const index = charts.indexOf(existingChart)
    if (index > -1) {
      charts.splice(index, 1)
    }
  }

  const chart = echarts.init(staffChartRef.value)
  charts.push(chart)

  if (!topEmployees || topEmployees.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    })
    return
  }

  const names = topEmployees.map(item => item.name).reverse()
  const values = topEmployees.map(item => item.value).reverse()

  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: names
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#667eea' },
          { offset: 1, color: '#764ba2' }
        ])
      },
      label: {
        show: true,
        position: 'right',
        formatter: (params) => `¥${params.value.toLocaleString()}`
      }
    }]
  })
}

// 初始化商品排行
const initProductChart = (topProducts) => {
  if (!productChartRef.value) return

  // 清理之前的图表实例
  const existingChart = echarts.getInstanceByDom(productChartRef.value)
  if (existingChart) {
    existingChart.dispose()
    const index = charts.indexOf(existingChart)
    if (index > -1) {
      charts.splice(index, 1)
    }
  }

  const chart = echarts.init(productChartRef.value)
  charts.push(chart)

  if (!topProducts || topProducts.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    })
    return
  }

  const names = topProducts.map(item => item.name).reverse()
  const values = topProducts.map(item => item.value).reverse()

  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: names
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#43e97b' },
          { offset: 1, color: '#38f9d7' }
        ])
      },
      label: {
        show: true,
        position: 'right',
        formatter: (params) => `¥${params.value.toLocaleString()}`
      }
    }]
  })
}

// 加载数据
let suppressSelectedDateWatch = false

const loadDashboardData = async (storeId = null, options = {}) => {
  loading.value = true

  try {
    // 转换门店ID：'all'表示全部门店，'1'表示万象城店，'2'表示青年路店
    const storeIdParam = storeId === 'all' ? null : (storeId ? parseInt(storeId, 10) : null)
    const hasTargetOverride = Object.prototype.hasOwnProperty.call(options, 'targetDate')
    const targetDateParam = hasTargetOverride ? options.targetDate : selectedDate.value
    const normalizedTargetDate = targetDateParam || null

    const data = await getDashboardSummary(storeIdParam, normalizedTargetDate)
    dashboardData.value = data
    trendSource.value = data.revenue_trend || []

    if ((!selectedDate.value || selectedDate.value === '') && data.reference_date) {
      suppressSelectedDateWatch = true
      selectedDate.value = data.reference_date
      if (isValidYmdDate(selectedDate.value)) {
        writeSessionJSON(selectedDateStorageKey, selectedDate.value)
      }
    }
    
    // 初始化图表 (无论是否有数据都要初始化，确保清空之前的图表)
    await nextTick()
    initTrendChart()
    initStoreChart(data.top_stores || [])
    initStaffChart(data.top_employees || [])
    initProductChart(data.top_products || [])
  } catch (error) {
    console.error('加载看板数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 窗口大小变化时重新调整图表
const handleResize = () => {
  charts.forEach(chart => chart.resize())
}

watch(trendMetric, () => {
  updateTrendChart()
})

watch(trendSource, () => {
  updateTrendChart()
})

watch(selectedDate, (newDate, oldDate) => {
  if (newDate === oldDate) return
  if (suppressSelectedDateWatch) {
    suppressSelectedDateWatch = false
    return
  }
  if (isValidYmdDate(newDate)) {
    writeSessionJSON(selectedDateStorageKey, newDate)
  } else if (!newDate) {
    writeSessionJSON(selectedDateStorageKey, '')
  }
  loadDashboardData(currentStore.value, { targetDate: newDate || null })
})

// 监听门店选择变化
watch(currentStore, (newStoreId) => {
  console.log('Dashboard检测到门店变化:', newStoreId)
  loadDashboardData(newStoreId)
})

onMounted(() => {
  const saved = readSessionJSON(selectedDateStorageKey, '')
  if (isValidYmdDate(saved)) {
    selectedDate.value = saved
  }
  loadDashboardData(currentStore.value)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach(chart => chart.dispose())
})
</script>

<style lang="scss" scoped>
.dashboard {
  .dashboard-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 20px;

    .dashboard-title {
      font-size: 20px;
      font-weight: 600;
      color: #303133;
    }

    :deep(.el-date-editor) {
      flex: 1 0 200px;
      min-width: 200px;
      max-width: 320px;
    }
  }


  .kpi-section {
    margin-bottom: 20px;

    .kpi-section-title {
      font-size: 16px;
      font-weight: 600;
      color: #606266;
      margin-bottom: 12px;
    }
  }

  .kpi-cards {
    margin-bottom: 10px;
  }
  
  .kpi-card {
    display: flex;
    align-items: center;
    
    :deep(.el-card__body) {
      display: flex;
      align-items: center;
      width: 100%;
    }
    
    .kpi-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      margin-right: 15px;
      flex-shrink: 0;
    }
    
    .kpi-content {
      flex: 1;
      
      .kpi-title {
        font-size: 14px;
        color: #909399;
        margin-bottom: 8px;
      }
      
      .kpi-value {
        font-size: 24px;
        font-weight: bold;
        color: #303133;
        margin-bottom: 5px;
      }
      
      .kpi-change {
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 3px;
        
        &.up { color: #67c23a; }
        &.down { color: #f56c6c; }
      }
    }
  }

  .kpi-cards.efficiency {
    .kpi-card .kpi-title {
      color: #606edc;
    }
  }
  
  .charts, .rankings {
    margin-bottom: 20px;
  }
  
  .chart-card, .ranking-card {
    .card-header {
      font-weight: bold;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;

      .trend-toggle {
        display: flex;
        align-items: center;
      }
    }
    
    .chart-container {
      height: 300px;
    }
  }

  // 移动端优化
  @media (max-width: 768px) {
    .dashboard-header {
      .dashboard-title {
        font-size: 18px;
        margin-right: 12px;
      }
      
      // 调整移动端日期选择器样式，避免独占一行
      :deep(.el-date-editor) {
        flex: 1;
        width: auto;
        min-width: 150px;
        max-width: none;
      }
    }

    .kpi-section {
      .kpi-section-title {
        font-size: 15px;
        margin-bottom: 10px;
      }
      
      // 移动端下 KPI 卡片单列显示，增加底部间距
      :deep(.el-col) {
        margin-bottom: 15px;
      }
    }

    .kpi-card {
      :deep(.el-card__body) {
        padding: 15px !important;
      }

      .kpi-icon {
        width: 50px;
        height: 50px;
        margin-right: 12px;

        .el-icon {
          font-size: 20px !important;
        }
      }

      .kpi-content {
        .kpi-title {
          font-size: 13px;
          margin-bottom: 6px;
        }

        .kpi-value {
          font-size: 20px;
          margin-bottom: 4px;
        }

        .kpi-change {
          font-size: 12px;
        }
      }
    }

    // 图表区域移动端单列显示
    .charts, .rankings {
      :deep(.el-col) {
        width: 100%;
        max-width: 100%;
        margin-bottom: 15px;
      }
    }

    .chart-card, .ranking-card {
      .card-header {
        font-size: 14px;

        .trend-toggle {
          width: 100%;

          :deep(.el-radio-group) {
            width: 100%;
            display: flex;

            .el-radio-button {
              flex: 1;

              :deep(.el-radio-button__inner) {
                width: 100%;
                padding: 8px 10px;
                font-size: 12px;
              }
            }
          }
        }
      }

      .chart-container {
        height: 250px;
      }
    }
  }

  @media (max-width: 480px) {
    .dashboard-header {
      .dashboard-title {
        font-size: 16px;
      }
    }

    .kpi-section {
      margin-bottom: 15px;

      .kpi-section-title {
        font-size: 14px;
      }
    }

    .kpi-card {
      :deep(.el-card__body) {
        padding: 12px !important;
      }

      .kpi-icon {
        width: 45px;
        height: 45px;
        margin-right: 10px;
        border-radius: 10px;

        .el-icon {
          font-size: 18px !important;
        }
      }

      .kpi-content {
        .kpi-title {
          font-size: 12px;
        }

        .kpi-value {
          font-size: 18px;
        }

        .kpi-change {
          font-size: 11px;
        }
      }
    }

    .chart-card, .ranking-card {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 15px;
      }

      .card-header {
        font-size: 13px;
      }

      .chart-container {
        height: 220px;
      }
    }
  }
}
</style>
