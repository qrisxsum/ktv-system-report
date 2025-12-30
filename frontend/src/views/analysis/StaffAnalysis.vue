<template>
  <div class="staff-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="header-title">👑 人员风云榜</span>
          <div class="header-right">
            <span class="filter-label">时间范围</span>
            <el-date-picker
              class="date-range"
              v-model="dateRange"
              type="daterange"
              unlink-panels
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              :editable="false"
              @change="handleDateChange"
            />
          </div>
        </div>
      </template>

      <!-- TOP 3 荣誉领奖台 -->
      <div class="top-three-podium" v-if="topThree.length > 0 && !loading">
        <div class="podium-item second" v-if="topThree[1]">
          <div class="rank-badge silver">🥈</div>
          <div class="avatar">{{ topThree[1].name.slice(0, 1) }}</div>
          <div class="name">
            {{ topThree[1].name }}
            <div v-if="currentStore === 'all' && topThree[1].store_name" class="podium-store">{{ topThree[1].store_name }}</div>
          </div>
          <div class="metric-label">{{ rankMetricLabel }}</div>
          <div class="amount">{{ formatMetricValue(topThree[1]) }}</div>
          <div class="sub-info">
            <span>订台 {{ topThree[1].booking_count }} 单</span>
            <span>客单价 ¥{{ topThree[1].avgPerOrder.toFixed(0) }}</span>
          </div>
        </div>
        <div class="podium-item first" v-if="topThree[0]">
          <div class="crown">👑</div>
          <div class="rank-badge gold">🥇</div>
          <div class="avatar champion">{{ topThree[0].name.slice(0, 1) }}</div>
          <div class="name">
            {{ topThree[0].name }}
            <div v-if="currentStore === 'all' && topThree[0].store_name" class="podium-store">{{ topThree[0].store_name }}</div>
          </div>
          <div class="metric-label">{{ rankMetricLabel }}</div>
          <div class="amount">{{ formatMetricValue(topThree[0]) }}</div>
          <div class="sub-info">
            <span>订台 {{ topThree[0].booking_count }} 单</span>
            <span>客单价 ¥{{ topThree[0].avgPerOrder.toFixed(0) }}</span>
          </div>
        </div>
        <div class="podium-item third" v-if="topThree[2]">
          <div class="rank-badge bronze">🥉</div>
          <div class="avatar">{{ topThree[2].name.slice(0, 1) }}</div>
          <div class="name">
            {{ topThree[2].name }}
            <div v-if="currentStore === 'all' && topThree[2].store_name" class="podium-store">{{ topThree[2].store_name }}</div>
          </div>
          <div class="metric-label">{{ rankMetricLabel }}</div>
          <div class="amount">{{ formatMetricValue(topThree[2]) }}</div>
          <div class="sub-info">
            <span>订台 {{ topThree[2].booking_count }} 单</span>
            <span>客单价 ¥{{ topThree[2].avgPerOrder.toFixed(0) }}</span>
          </div>
        </div>
      </div>

      <!-- 排名维度切换 -->
      <div class="rank-toggle-section">
        <span class="toggle-label">排名依据：</span>
        <el-radio-group v-model="rankMetric" size="small" @change="handleRankMetricChange">
          <el-radio-button value="actual_amount">实收金额</el-radio-button>
          <el-radio-button value="booking_count">订台数</el-radio-button>
          <el-radio-button value="sales_amount">销售金额</el-radio-button>
          <el-radio-button value="base_performance">基本业绩</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 汇总统计卡片 -->
      <el-row :gutter="16" class="summary-cards">
        <el-col :xs="12" :sm="6">
          <div class="summary-item primary">
            <div class="label">总员工数</div>
            <div class="value">{{ total }} 人</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-item success">
            <div class="label">总实收金额</div>
            <div class="value">¥{{ summaryStats.totalActual.toLocaleString() }}</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-item info">
            <div class="label">总订台数</div>
            <div class="value">{{ summaryStats.totalOrders }} 单</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-item warning">
            <div class="label">平均客单价</div>
            <div class="value">¥{{ summaryStats.avgPerOrder.toFixed(0) }}</div>
          </div>
        </el-col>
      </el-row>
      
      <div class="chart-wrapper" ref="chartWrapperRef">
      <div class="chart-container" ref="chartRef" v-loading="loading"></div>
      </div>
      
      <el-table
        ref="tableRef"
        :data="staffData"
        stripe
        border
        style="margin-top: 20px"
        v-loading="loading"
        @sort-change="handleSortChange"
      >
        <el-table-column label="排名" width="70" align="center" :fixed="isMobile ? 'left' : false">
          <template #default="{ $index }">
            <span v-if="$index === 0" class="rank-icon gold">🥇</span>
            <span v-else-if="$index === 1" class="rank-icon silver">🥈</span>
            <span v-else-if="$index === 2" class="rank-icon bronze">🥉</span>
            <span v-else class="rank-number">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="姓名" min-width="100" :fixed="isMobile ? 'left' : false">
          <template #default="{ row, $index }">
            <div class="name-cell">
              <span class="staff-name">{{ row.name }}</span>
              <el-tag v-if="$index === 0" size="small" type="warning" effect="dark" class="top-tag">TOP</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-if="currentStore === 'all'" prop="store_name" label="所属门店" width="120" />
        <el-table-column prop="booking_count" label="订台数" width="90" align="right" sortable />
        <el-table-column prop="sales_amount" label="销售金额" width="120" align="right" sortable>
          <template #default="{ row }">
            ¥{{ (row.sales_amount || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="actual_amount" label="实收金额" width="120" align="right" sortable="custom">
          <template #default="{ row }">
            <span class="highlight-value">¥{{ (row.actual_amount || 0).toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="avgPerOrder" label="客单价" width="90" align="right" sortable="custom">
          <template #default="{ row }">
            ¥{{ row.avgPerOrder.toFixed(0) }}
          </template>
        </el-table-column>
        <el-table-column prop="conversionRate" label="转化率" width="80" align="center" sortable="custom">
          <template #default="{ row }">
            <span :class="getConversionClass(row.conversionRate)">
              {{ row.conversionRate.toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="contributionPct" label="贡献占比" min-width="130">
          <template #default="{ row }">
            <div class="contribution-cell">
              <el-progress 
                :percentage="row.contributionPct" 
                :stroke-width="10"
                :color="getProgressColor(row.contributionPct)"
                :show-text="false"
              />
              <span class="pct-text">{{ row.contributionPct.toFixed(1) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="gift_amount" label="赠送金额" width="100" align="right" sortable="custom">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.gift_amount > 500 }">
              ¥{{ (row.gift_amount || 0).toFixed(0) }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          background
          :layout="paginationLayout"
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="pageSizeOptions"
          :total="total"
          :disabled="loading"
          :pager-count="pagerCount"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
      
      <div v-if="!staffData.length && !loading" class="empty-hint">
        暂无数据，请先上传订台数据
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, inject, reactive, nextTick } from 'vue'
import * as echarts from 'echarts'
import { queryStats, getDateRange } from '@/api/stats'
import { ElMessage } from 'element-plus'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'
import { usePagination } from '@/composables/usePagination'

const loading = ref(false)
const dateRange = ref([])
const chartRef = ref(null)
const chartWrapperRef = ref(null)
const tableRef = ref(null)
let chart = null
const dateRangeStorageKey = 'viewState:StaffAnalysis:dateRange'

// 排名维度
const rankMetric = ref('actual_amount')
const rankMetricLabel = computed(() => {
  const labels = {
    actual_amount: '实收金额',
    booking_count: '订台数',
    sales_amount: '销售金额',
    base_performance: '基本业绩'
  }
  return labels[rankMetric.value] || '实收金额'
})

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const tableRows = ref([])
const chartRows = ref([])
const total = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20
})

const sortState = reactive({
  prop: null,
  order: null
})

// 前端字段名到后端字段名的映射
const SORT_FIELD_MAP = {
  booking_count: 'orders',
  actual_amount: 'actual',
  base_performance: 'performance',
  avgPerOrder: 'avg_order_amount',
  conversionRate: 'actual_rate'
}

// 使用分页优化 Composable
const { isMobile, pageSizeOptions, paginationLayout, pagerCount, checkDevice } = usePagination({
  desktopPageSizes: [20, 50, 100],
  mobilePageSizes: [20, 50]
})

const normalizeStaffRow = (item = {}) => ({
  name: item.dimension_label || item.dimension_key || '未知员工',
  store_name: item.store_name || item.store_label || item.extra_info?.store_name || '',
  booking_count: item.orders || 0,
  sales_amount: item.sales_amount || 0,
  actual_amount: item.actual || 0,
  base_performance: item.performance || 0,
  gift_amount: item.gift_amount || 0
})

// 汇总统计
const summaryStats = computed(() => {
  const source = chartRows.value.map(normalizeStaffRow)
  const totalActual = source.reduce((sum, i) => sum + i.actual_amount, 0)
  const totalOrders = source.reduce((sum, i) => sum + i.booking_count, 0)
  return {
    totalActual,
    totalOrders,
    avgPerOrder: totalOrders > 0 ? totalActual / totalOrders : 0
  }
})

// 增强员工数据（添加客单价、转化率、贡献占比）
// 优先使用后端返回的字段，如果没有则前端计算（兼容旧数据）
const enhanceStaffData = (data) => {
  const totalActual = data.reduce((sum, i) => sum + i.actual_amount, 0)
  return data.map(item => ({
    ...item,
    avgPerOrder: item.avg_order_amount !== undefined ? item.avg_order_amount : (item.booking_count > 0 ? item.actual_amount / item.booking_count : 0),
    conversionRate: item.actual_rate !== undefined ? item.actual_rate * 100 : (item.sales_amount > 0 ? (item.actual_amount / item.sales_amount) * 100 : 0),
    contributionPct: item.contribution_pct !== undefined ? item.contribution_pct : (totalActual > 0 ? (item.actual_amount / totalActual) * 100 : 0)
  }))
}

// 排序函数
const sortByMetric = (data, metric) => {
  return [...data].sort((a, b) => {
    if (metric === 'booking_count') {
      return b.booking_count - a.booking_count
    } else if (metric === 'sales_amount') {
      return b.sales_amount - a.sales_amount
    } else if (metric === 'base_performance') {
      return b.base_performance - a.base_performance
    }
    return b.actual_amount - a.actual_amount
  })
}

// 处理后的员工数据
// 统一使用后端排序，直接使用后端返回的顺序（后端已排好序）
const staffData = computed(() => {
  const data = tableRows.value.map(normalizeStaffRow)
  const enhanced = enhanceStaffData(data)
  // 后端已按排序字段排好序，直接返回
  return enhanced
})

// 图表所用数据（不受分页影响）
// 注意：图表数据使用 series_rows，后端已按排序字段排好序
const chartStaffData = computed(() => {
  const data = chartRows.value.map(normalizeStaffRow)
  const enhanced = enhanceStaffData(data)
  // 后端已按排序字段排好序，直接返回
  return enhanced
})

// TOP 3 数据
const topThree = computed(() => {
  return chartStaffData.value.slice(0, 3)
})

// 格式化指标值
const formatMetricValue = (item) => {
  if (rankMetric.value === 'booking_count') {
    return `${item.booking_count} 单`
  }
  const value = item[rankMetric.value] || 0
  return `¥${value.toLocaleString()}`
}

// 转化率样式
const getConversionClass = (rate) => {
  if (rate >= 90) return 'conversion-high'
  if (rate >= 70) return 'conversion-medium'
  return 'conversion-low'
}

// 进度条颜色
const getProgressColor = (pct) => {
  if (pct >= 20) return '#667eea'
  if (pct >= 10) return '#43e97b'
  return '#909399'
}

// 排名维度切换
const handleRankMetricChange = async () => {
  // 切换排名依据时，需要重新获取数据以使用新的排序字段
  // 清除表头排序状态，使用 rankMetric 作为排序依据
  sortState.prop = null
  sortState.order = null
  pagination.page = 1
  await fetchData()
}

// 初始化日期范围（使用数据库中的最新日期）
const initDateRange = async () => {
  try {
    const rangeRes = await getDateRange('booking')
    if (rangeRes.success && rangeRes.suggested_start && rangeRes.suggested_end) {
      dateRange.value = [rangeRes.suggested_start, rangeRes.suggested_end]
    } else {
      // 如果没有数据，使用当前月份
      const today = new Date()
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
      dateRange.value = [
        firstDay.toISOString().split('T')[0],
        today.toISOString().split('T')[0]
      ]
    }
  } catch (error) {
    console.error('获取日期范围失败:', error)
    const today = new Date()
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
    dateRange.value = [
      firstDay.toISOString().split('T')[0],
      today.toISOString().split('T')[0]
    ]
  }
}

// 获取数据
const fetchData = async () => {
  if (!dateRange.value || dateRange.value.length !== 2) {
    return
  }
  
  loading.value = true
  
  try {
    const [startDate, endDate] = dateRange.value

    // 将前端字段名映射到后端字段名
    // 如果有表头排序，使用表头排序字段；否则使用排名依据（rankMetric）对应的后端字段
    let backendSortField = undefined
    let sortOrder = undefined
    
    if (sortState.prop) {
      // 表头排序
      backendSortField = SORT_FIELD_MAP[sortState.prop] || sortState.prop
      sortOrder = sortState.order === 'ascending' ? 'asc' : sortState.order === 'descending' ? 'desc' : undefined
    } else {
      // 无表头排序时，使用排名依据（rankMetric）进行后端排序
      backendSortField = SORT_FIELD_MAP[rankMetric.value] || rankMetric.value
      sortOrder = 'desc' // 默认降序
    }
    
    const params = {
      table: 'booking',
      start_date: startDate,
      end_date: endDate,
      dimension: 'employee',
      granularity: 'day',
      page: pagination.page,
      page_size: pagination.pageSize,
      sort_by: backendSortField,
      sort_order: sortOrder
    }

    // 根据当前门店选择设置store_id参数
    if (currentStore.value && currentStore.value !== 'all') {
      const parsedStoreId = parseInt(currentStore.value, 10)
      if (Number.isFinite(parsedStoreId)) {
        params.store_id = parsedStoreId
      }
    }

    // 过滤掉 undefined 值
    const filteredParams = Object.fromEntries(
      Object.entries(params).filter(([, value]) => value !== undefined)
    )

    const response = await queryStats(filteredParams)

    if (response.success && response.data) {
      const rows = Array.isArray(response.data.rows) ? response.data.rows : []
      const seriesRows = Array.isArray(response.data.series_rows) ? response.data.series_rows : []
      tableRows.value = rows
      chartRows.value = seriesRows
      const parsedTotal = Number(response.data.total)
      total.value = Number.isFinite(parsedTotal) ? parsedTotal : rows.length
    } else {
      tableRows.value = []
      chartRows.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('获取员工分析数据失败:', error)
    ElMessage.error('获取员工分析数据失败')
    tableRows.value = []
    chartRows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const initChart = () => {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
    // 移动端：初始化时设置图表容器最小宽度
    if (isMobile.value) {
      const container = chartRef.value
      const minWidth = Math.max(600, window.innerWidth)
      container.style.minWidth = `${minWidth}px`
    }
    updateChart()
  }
}

const updateChart = () => {
  if (!chart) return
  
  // 移动端：确保图表容器有足够宽度以显示完整标签
  if (isMobile.value && chartRef.value) {
    const container = chartRef.value
    // 计算所需的最小宽度：根据标签长度动态调整
    // 如果显示全部门店，标签会更长，需要更多空间
    const hasStoreNames = currentStore.value === 'all' && chartStaffData.value.some(item => item.store_name)
    const minWidth = hasStoreNames ? Math.max(700, window.innerWidth) : Math.max(600, window.innerWidth)
    container.style.minWidth = `${minWidth}px`
  }
  
  // 取前10名员工数据（不受分页影响）
  const isCountMetric = rankMetric.value === 'booking_count'
  const metricKey = rankMetric.value
  
  const data = chartStaffData.value
    .slice(0, 10)
    .map(item => ({ 
      name: (currentStore.value === 'all' && item.store_name) ? `${item.name}(${item.store_name})` : item.name, 
      value: item[metricKey] || 0,
      actualAmount: item.actual_amount,
      bookingCount: item.booking_count
    }))
    .reverse() // 图表从下到上排列
  
  // 根据设备类型调整配置
  // 移动端：增加左侧边距以容纳完整的员工名+门店名标签，并设置最小宽度支持横向滚动
  const gridConfig = isMobile.value 
    ? { left: '35%', right: '5%', top: '5%', bottom: '10%' }
    : { left: '15%', right: '15%', top: '5%', bottom: '5%' }
  
  const xAxisLabelConfig = isMobile.value
    ? {
        formatter: (value) => {
          if (isCountMetric) {
            return value + '单'
          }
          if (value >= 10000) {
            return '¥' + (value / 10000).toFixed(1) + '万'
          } else if (value >= 1000) {
            return '¥' + (value / 1000).toFixed(0) + 'K'
          } else {
            return '¥' + value.toFixed(0)
          }
        },
        fontSize: 10,
        margin: 8
      }
    : {
        formatter: (value) => {
          if (isCountMetric) {
            return value + '单'
          }
          return '¥' + (value / 1000).toFixed(0) + 'K'
        }
      }
  
  // 根据排名维度选择不同渐变色
  const gradientColors = {
    actual_amount: [{ offset: 0, color: '#667eea' }, { offset: 1, color: '#764ba2' }],
    booking_count: [{ offset: 0, color: '#43e97b' }, { offset: 1, color: '#38f9d7' }],
    sales_amount: [{ offset: 0, color: '#f093fb' }, { offset: 1, color: '#f5576c' }],
    base_performance: [{ offset: 0, color: '#4facfe' }, { offset: 1, color: '#00f2fe' }]
  }
  
  chart.setOption({
    tooltip: { 
      trigger: 'axis', 
      formatter: (params) => {
        const d = params[0]
        const dataItem = data[d.dataIndex]
        if (isCountMetric) {
          return `${d.name}<br/>订台数: ${d.value} 单<br/>实收: ¥${dataItem.actualAmount.toLocaleString()}`
        }
        return `${d.name}<br/>${rankMetricLabel.value}: ¥${d.value.toLocaleString()}<br/>订台: ${dataItem.bookingCount} 单`
      },
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: gridConfig,
    xAxis: { 
      type: 'value',
      axisLabel: xAxisLabelConfig
    },
    yAxis: {
      type: 'category',
      data: data.map(d => d.name),
      axisLabel: {
        interval: 0,
        fontSize: isMobile.value ? 11 : undefined,
        // 移动端：允许标签完整显示，不截断
        width: isMobile.value ? 120 : undefined,
        overflow: isMobile.value ? 'none' : undefined,
        ellipsis: isMobile.value ? '' : undefined
      }
    },
    series: [{
      type: 'bar',
      data: data.map(d => d.value),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, gradientColors[metricKey] || gradientColors.actual_amount)
      },
      label: {
        show: true,
        position: 'right',
        formatter: (params) => {
          if (isCountMetric) {
            return params.value + '单'
          }
          return '¥' + params.value.toLocaleString()
        },
        fontSize: isMobile.value ? 10 : undefined
      }
    }]
  })
  
  // 移动端：图表更新后，将滚动位置设置为中间
  scrollChartToCenter()
}

// 将图表滚动到中间位置
const scrollChartToCenter = () => {
  if (isMobile.value && chartWrapperRef.value) {
    nextTick(() => {
      const wrapper = chartWrapperRef.value
      if (wrapper && wrapper.scrollWidth > wrapper.clientWidth) {
        const scrollLeft = (wrapper.scrollWidth - wrapper.clientWidth) / 2
        wrapper.scrollLeft = scrollLeft
      }
    })
  }
}

// 监听门店变化，重新获取数据
watch(currentStore, () => {
  pagination.page = 1
  fetchData()
})

// 监听图表数据变化，更新图表
watch(chartStaffData, () => {
  updateChart()
})

const scrollTableToTop = () => {
  nextTick(() => {
    if (tableRef.value?.setScrollTop) {
      tableRef.value.setScrollTop(0)
    }
  })
}

const handlePageChange = async (page) => {
  pagination.page = page
  await fetchData()
  scrollTableToTop()
}

const handlePageSizeChange = async (size) => {
  pagination.pageSize = size
  pagination.page = 1
  await fetchData()
  scrollTableToTop()
}

const handleSortChange = async ({ prop, order }) => {
  // 更新排序状态
  sortState.prop = prop || null
  sortState.order = order || null
  // 排序变化时重置到第一页
  pagination.page = 1
  await fetchData()
  // 注意：排序时不需要滚动表格，保持用户当前查看位置
}

const handleDateChange = () => {
  pagination.page = 1
  if (isValidDateRange(dateRange.value)) {
    writeSessionJSON(dateRangeStorageKey, dateRange.value)
  }
  fetchData()
}

const handleResize = () => {
  checkDevice()
  // 移动端：确保图表容器有足够宽度以显示完整标签
  if (isMobile.value && chartRef.value) {
    const container = chartRef.value
    // 计算所需的最小宽度：左侧标签区域（35%）+ 图表区域
    // 根据实际标签长度动态调整，这里设置一个合理的最小值
    const hasStoreNames = currentStore.value === 'all' && chartStaffData.value.some(item => item.store_name)
    const minWidth = hasStoreNames ? Math.max(700, window.innerWidth) : Math.max(600, window.innerWidth)
    container.style.minWidth = `${minWidth}px`
  }
  chart?.resize()
  // 窗口大小变化时重新更新图表配置，确保移动端/桌面端配置正确
  updateChart()
  // 移动端：窗口大小变化后重新居中滚动
  scrollChartToCenter()
}

onMounted(async () => {
  initChart()
  const saved = readSessionJSON(dateRangeStorageKey, null)
  if (isValidDateRange(saved)) {
    dateRange.value = saved
  } else {
    await initDateRange()
    if (isValidDateRange(dateRange.value)) {
      writeSessionJSON(dateRangeStorageKey, dateRange.value)
    }
  }
  await fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style lang="scss" scoped>
.staff-analysis {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: wrap;
  }

  .header-title {
    font-weight: 600;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .filter-label {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
  }

  .date-range {
    width: 360px;
    max-width: 100%;
  }

  // TOP 3 荣誉领奖台
  .top-three-podium {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    gap: 20px;
    padding: 30px 20px 20px;
    background: linear-gradient(180deg, #f8f9ff 0%, #fff 100%);
    border-radius: 12px;
    margin-bottom: 20px;

    .podium-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px 15px;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
      transition: transform 0.3s ease;
      position: relative;
      min-width: 140px;

      &:hover {
        transform: translateY(-5px);
      }

      &.first {
        order: 2;
        padding: 25px 20px;
        min-width: 160px;
        background: linear-gradient(135deg, #fff9e6 0%, #fff 100%);
        box-shadow: 0 6px 20px rgba(255, 193, 7, 0.25);
        
        .crown {
          position: absolute;
          top: -20px;
          font-size: 32px;
          animation: bounce 2s infinite;
        }

        .avatar {
          width: 70px;
          height: 70px;
          font-size: 28px;
        }

        .amount {
          font-size: 20px;
        }
      }

      &.second {
        order: 1;
        background: linear-gradient(135deg, #f8f9ff 0%, #fff 100%);
      }

      &.third {
        order: 3;
        background: linear-gradient(135deg, #fff5f0 0%, #fff 100%);
      }

      .rank-badge {
        font-size: 24px;
        margin-bottom: 8px;
      }

      .avatar {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        font-weight: 600;
        margin-bottom: 10px;

        &.champion {
          background: linear-gradient(135deg, #ffd700 0%, #ffaa00 100%);
        }
      }

      .name {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
        margin-bottom: 4px;
        text-align: center;
      }

      .podium-store {
        font-size: 11px;
        color: #909399;
        font-weight: normal;
        margin-top: 2px;
      }

      .metric-label {
        font-size: 12px;
        color: #909399;
        margin-bottom: 2px;
      }

      .amount {
        font-size: 18px;
        font-weight: bold;
        color: #667eea;
      }

      .sub-info {
        display: flex;
        gap: 10px;
        margin-top: 8px;
        font-size: 12px;
        color: #909399;
      }
    }
  }

  @keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
  }

  // 排名维度切换
  .rank-toggle-section {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;

    .toggle-label {
      font-size: 14px;
      color: #606266;
      font-weight: 500;
    }
  }

  // 汇总统计卡片
  .summary-cards {
    margin-bottom: 20px;

    .summary-item {
      border-radius: 10px;
      padding: 16px;
      color: #fff;
      text-align: center;

      .label {
        font-size: 13px;
        opacity: 0.9;
        margin-bottom: 6px;
      }

      .value {
        font-size: 20px;
        font-weight: bold;
      }

      &.primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      }
      &.success {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
      }
      &.info {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      }
      &.warning {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      }
    }
  }
  
  .chart-wrapper {
    // 移动端：支持横向滚动以显示完整的纵坐标标签
    @media (max-width: 768px) {
      overflow-x: auto;
      overflow-y: hidden;
      -webkit-overflow-scrolling: touch;
      width: 100%;
      position: relative;
      
      .chart-container {
        // 最小宽度由 JavaScript 动态设置，这里只作为后备
        min-width: 600px;
      }
    }
  }
  
  .chart-container {
    height: 400px;
    width: 100%;
  }

  // 表格增强样式
  .rank-icon {
    font-size: 18px;
    
    &.gold { filter: drop-shadow(0 2px 3px rgba(255, 193, 7, 0.4)); }
    &.silver { filter: drop-shadow(0 2px 3px rgba(192, 192, 192, 0.4)); }
    &.bronze { filter: drop-shadow(0 2px 3px rgba(205, 127, 50, 0.4)); }
  }

  .rank-number {
    font-weight: 600;
    color: #606266;
  }

  .name-cell {
    display: flex;
    align-items: center;
    gap: 6px;

    .staff-name {
      font-weight: 500;
    }

    .top-tag {
      font-size: 10px;
      padding: 0 4px;
      height: 18px;
      line-height: 18px;
    }
  }

  .highlight-value {
    font-weight: 600;
    color: #667eea;
  }

  .conversion-high {
    color: #67c23a;
    font-weight: 600;
  }
  .conversion-medium {
    color: #e6a23c;
    font-weight: 500;
  }
  .conversion-low {
    color: #909399;
  }

  .contribution-cell {
    display: flex;
    align-items: center;
    gap: 8px;

    :deep(.el-progress) {
      flex: 1;
    }

    .pct-text {
      font-size: 12px;
      color: #606266;
      min-width: 40px;
      text-align: right;
    }
  }

  .text-danger {
    color: #f56c6c;
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
    width: 100%;
  }
  
  .empty-hint {
    text-align: center;
    padding: 40px 0;
    color: #999;
  }

  // 移动端优化
  @media (max-width: 768px) {
    .card-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .header-right {
      width: 100%;
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
    }

    .filter-label {
      font-size: 12px;
    }

    .date-range {
      width: 100%;
    }

    // 时间范围选择器样式优化
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

    // TOP 3 领奖台移动端
    .top-three-podium {
      flex-wrap: wrap;
      gap: 12px;
      padding: 20px 10px;

      .podium-item {
        min-width: 100px;
        padding: 15px 10px;

        &.first {
          min-width: 120px;
          padding: 18px 12px;

          .crown {
            font-size: 24px;
            top: -15px;
          }

          .avatar {
            width: 55px;
            height: 55px;
            font-size: 22px;
          }

          .amount {
            font-size: 16px;
          }
        }

        .rank-badge {
          font-size: 20px;
        }

        .avatar {
          width: 45px;
          height: 45px;
          font-size: 18px;
        }

        .name {
          font-size: 14px;
        }

        .amount {
          font-size: 15px;
        }

        .sub-info {
          flex-direction: column;
          gap: 2px;
          font-size: 11px;
        }
      }
    }

    // 排名切换移动端
    .rank-toggle-section {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;

      :deep(.el-radio-group) {
        width: 100%;
        display: flex;
        flex-wrap: wrap;

        .el-radio-button {
          flex: 1;
          min-width: 0;

          .el-radio-button__inner {
            width: 100%;
            padding: 8px 6px;
            font-size: 12px;
          }
        }
      }
    }

    // 汇总卡片移动端
    .summary-cards {
      :deep(.el-col) {
        margin-bottom: 10px;
      }

      .summary-item {
        padding: 12px;

        .label {
          font-size: 12px;
        }

        .value {
          font-size: 16px;
        }
      }
    }

    .chart-wrapper {
    .chart-container {
      height: 300px;
      }
    }

    :deep(.el-table) {
      font-size: 12px;

      .el-table__header th,
      .el-table__body td {
        padding: 8px 5px;
      }
    }

    .contribution-cell {
      .pct-text {
        font-size: 11px;
        min-width: 35px;
      }
    }

    .table-pagination {
      justify-content: center !important;
      margin-top: 10px;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;

      :deep(.el-pagination) {
        flex-wrap: wrap;
        justify-content: center;
        font-size: 12px;

        .el-pagination__total,
        .el-pagination__sizes,
        .el-pagination__jump {
          margin-right: 8px;
          font-size: 12px;
        }

        .btn-prev,
        .btn-next {
          min-width: 26px;
          height: 26px;
          line-height: 26px;
          padding: 0 6px;
        }

        .el-pager {
          li {
            min-width: 26px;
            height: 26px;
            line-height: 26px;
            font-size: 12px;
            margin: 0 2px;
          }
        }

        .el-pagination__sizes {
          .el-select {
            .el-input {
              .el-input__inner {
                height: 26px;
                line-height: 26px;
                font-size: 12px;
                padding: 0 20px 0 8px;
              }
            }
          }
        }

        .el-pagination__jump {
          .el-input {
            .el-input__inner {
              height: 26px;
              line-height: 26px;
              font-size: 12px;
              width: 40px;
            }
          }
        }
      }
    }
  }

  @media (max-width: 480px) {
    :deep(.el-card__header) {
      padding: 12px 15px;
    }

    :deep(.el-card__body) {
      padding: 12px;
    }

    // TOP 3 极小屏幕
    .top-three-podium {
      padding: 15px 8px;

      .podium-item {
        min-width: 85px;
        padding: 12px 8px;

        &.first {
          min-width: 95px;
          padding: 14px 10px;

          .crown {
            font-size: 20px;
            top: -12px;
          }

          .avatar {
            width: 45px;
            height: 45px;
            font-size: 18px;
          }

          .amount {
            font-size: 14px;
          }
        }

        .rank-badge {
          font-size: 16px;
          margin-bottom: 4px;
        }

        .avatar {
          width: 38px;
          height: 38px;
          font-size: 15px;
          margin-bottom: 6px;
        }

        .name {
          font-size: 12px;
        }

        .metric-label {
          font-size: 10px;
        }

        .amount {
          font-size: 13px;
        }

        .sub-info {
          font-size: 10px;
          margin-top: 4px;
        }
      }
    }

    .summary-cards {
      .summary-item {
        padding: 10px;

        .label {
          font-size: 11px;
        }

        .value {
          font-size: 14px;
        }
      }
    }

    .chart-wrapper {
    .chart-container {
      height: 250px;
      }
    }

    .rank-icon {
      font-size: 15px;
    }

    .name-cell {
      .staff-name {
        font-size: 12px;
      }

      .top-tag {
        font-size: 9px;
        padding: 0 3px;
        height: 16px;
        line-height: 16px;
      }
    }

    :deep(.el-table) {
      font-size: 11px;

      .el-table__header th,
      .el-table__body td {
        padding: 6px 3px;
      }
    }

    .table-pagination {
      margin-top: 8px;

      :deep(.el-pagination) {
        font-size: 11px;
        gap: 4px;

        .el-pagination__total {
          font-size: 11px;
          margin-right: 4px;
        }

        .el-pagination__sizes {
          margin-right: 4px;
          
          .el-select {
            .el-input {
              .el-input__inner {
                height: 24px;
                line-height: 24px;
                font-size: 11px;
                padding: 0 18px 0 6px;
              }
            }
          }
        }

        .btn-prev,
        .btn-next {
          min-width: 24px;
          height: 24px;
          line-height: 24px;
          padding: 0 4px;
        }

        .el-pager {
          li {
            min-width: 24px;
            height: 24px;
            line-height: 24px;
            font-size: 11px;
            margin: 0 1px;
          }
        }

        .el-pagination__jump {
          margin-left: 4px;
          font-size: 11px;
          
          .el-input {
            .el-input__inner {
              height: 24px;
              line-height: 24px;
              font-size: 11px;
              width: 35px;
            }
          }
        }
      }
    }

    .empty-hint {
      padding: 30px 0;
      font-size: 14px;
    }
  }
}
</style>

