<template>
  <div class="general-analysis">
    <el-card class="analysis-card" shadow="never">
      <template #header>
        <div class="card-header">
          <h2>通用数据分析</h2>
        </div>
      </template>

      <div class="query-toolbar">
        <div class="toolbar-item">
          <span class="toolbar-label">数据源</span>
          <el-select v-model="queryParams.table" placeholder="选择数据源">
            <el-option
              v-for="option in tableOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>

        <div class="toolbar-item">
          <span class="toolbar-label">时间范围</span>
          <el-date-picker
            v-model="queryParams.dateRange"
            type="daterange"
            unlink-panels
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </div>

        <div class="toolbar-item">
          <span class="toolbar-label">门店</span>
          <!-- 管理员：显示下拉选择器 -->
          <el-select
            v-if="currentUser?.role === 'admin'"
            v-model="queryParams.store_id"
            placeholder="全部门店"
            clearable
          >
            <el-option
              v-for="store in storeOptions"
              :key="store.id"
              :label="store.name"
              :value="store.id"
            />
          </el-select>
          <!-- 店长：显示固定门店名称 -->
          <el-input
            v-else
            :model-value="managerStoreName"
            readonly
            placeholder="我的门店"
            style="width: 100%"
          />
        </div>

        <div class="toolbar-item">
          <span class="toolbar-label">分析维度</span>
          <el-select v-model="queryParams.dimension" placeholder="选择维度">
            <el-option
              v-for="option in dimensionOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>

        <div
          v-if="showGranularity"
          class="toolbar-item"
        >
          <span class="toolbar-label">时间粒度</span>
          <el-select v-model="queryParams.granularity" placeholder="选择粒度">
            <el-option
              v-for="option in granularityOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>

        <div class="toolbar-item toolbar-action">
          <el-button type="primary" @click="handleQuery">查询</el-button>
        </div>
      </div>

      <div class="chart-section">
        <div class="chart-header">
          <div class="chart-info">
            <h3>可视化分析</h3>
            <p v-if="currentMetricLabel" class="chart-subtitle">
              当前指标：{{ currentMetricLabel }}
            </p>
          </div>
          <el-radio-group
            v-if="metricOptions.length"
            v-model="selectedMetric"
            size="small"
            class="metric-selector"
          >
            <el-radio-button
              v-for="metric in metricOptions"
              :key="metric.prop"
              :label="metric.prop"
            >
              {{ metric.label }}
            </el-radio-button>
          </el-radio-group>
          <span v-else class="metric-placeholder">暂无可选指标</span>
          <div
            v-if="chartNeedsDataZoom"
            class="chart-actions"
          >
            <el-button
              size="small"
              text
              @click="handleResetZoom"
            >
              重置缩放
            </el-button>
          </div>
        </div>
        <div
          v-if="chartNotices.length"
          class="chart-notice-list"
        >
          <el-alert
            v-for="(notice, index) in chartNotices"
            :key="index"
            :title="notice.message"
            :type="notice.type"
            :closable="false"
            show-icon
          />
        </div>
        <div class="chart-body">
          <div ref="chartRef" class="chart-container"></div>
          <div v-if="!hasChartData" class="chart-empty">
            暂无可视化数据，请先执行查询
          </div>
        </div>
      </div>

      <el-table
        ref="tableRef"
        class="result-table"
        :data="renderedTableData"
        border
        stripe
        v-loading="loading"
        :empty-text="loading ? '数据加载中…' : '暂无数据，请先执行查询'"
      >
        <el-table-column
          v-for="column in tableColumns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :min-width="column.minWidth || 120"
          :align="column.align || 'left'"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ row[column.prop] ?? '--' }}
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="pageSizeOptions"
          :total="renderedTableTotal"
          :disabled="paginationDisabled"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>

    </el-card>
  </div>
</template>

<script setup>
import { reactive, computed, watch, ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { queryStats } from '@/api/stats'
import { listStores } from '@/api/store'

const EMPTY_DATASET = Object.freeze([])
const PAGINATION_CONFIG = Object.freeze({
  defaultPage: 1,
  defaultPageSize: 50,
  pageSizeOptions: [20, 50, 100, 200],
  maxPageSize: 200
})

const queryParams = reactive({
  table: 'sales',
  dateRange: [],
  dimension: 'date',
  granularity: 'day',
  store_id: null
})

const pagination = reactive({
  page: PAGINATION_CONFIG.defaultPage,
  pageSize: PAGINATION_CONFIG.defaultPageSize
})

const TABLE_OPTIONS = [
  { label: '商品 (Sales)', value: 'sales' },
  { label: '预订 (Booking)', value: 'booking' },
  { label: '包厢 (Room)', value: 'room' }
]

const DIMENSION_OPTIONS_MAP = {
  sales: [
    { label: '日期', value: 'date' },
    { label: '门店', value: 'store' },
    { label: '商品', value: 'product' }
  ],
  booking: [
    { label: '日期', value: 'date' },
    { label: '门店', value: 'store' },
    { label: '员工', value: 'employee' }
  ],
  room: [
    { label: '日期', value: 'date' },
    { label: '门店', value: 'store' },
    { label: '包厢', value: 'room' },
    { label: '包厢类型', value: 'room_type' }
  ]
}

const DEFAULT_DIMENSION_MAP = {
  sales: 'date',
  booking: 'date',
  room: 'date'
}

const GRANULARITY_OPTIONS = [
  { label: '按日 (Day)', value: 'day' },
  { label: '按周 (Week)', value: 'week' },
  { label: '按月 (Month)', value: 'month' }
]

const DIMENSION_COLUMN_MAP = {
  date: { label: '日期', prop: 'dimension_value', minWidth: 140 },
  store: { label: '门店', prop: 'dimension_value', minWidth: 160 },
  employee: { label: '员工', prop: 'dimension_value', minWidth: 160 },
  product: { label: '商品', prop: 'dimension_value', minWidth: 160 },
  room: { label: '包厢', prop: 'dimension_value', minWidth: 140 },
  room_type: { label: '包厢类型', prop: 'dimension_value', minWidth: 160 }
}

const COLUMN_CONFIG = {
  booking: [
    { prop: 'orders', label: '订单数', align: 'right', minWidth: 100 },
    { prop: 'sales_amount', label: '销售额', align: 'right', minWidth: 120 },
    { prop: 'actual', label: '实收', align: 'right', minWidth: 120 },
    { prop: 'performance', label: '业绩', align: 'right', minWidth: 120 }
  ],
  sales: [
    { prop: 'sales_qty', label: '销量', align: 'right', minWidth: 100 },
    { prop: 'sales_amount', label: '销售额', align: 'right', minWidth: 120 },
    { prop: 'gift_amount', label: '赠送金额', align: 'right', minWidth: 120 },
    { prop: 'cost', label: '成本', align: 'right', minWidth: 100 },
    { prop: 'profit', label: '毛利', align: 'right', minWidth: 100 }
  ],
  room: [
    { prop: 'orders', label: '开台数', align: 'right', minWidth: 100 },
    { prop: 'gmv', label: 'GMV', align: 'right', minWidth: 120 },
    { prop: 'actual', label: '实收', align: 'right', minWidth: 120 },
    { prop: 'duration', label: '时长', align: 'right', minWidth: 100 } // 假设后端字段为 duration
  ]
}

const tableOptions = TABLE_OPTIONS

const dimensionOptions = computed(() => DIMENSION_OPTIONS_MAP[queryParams.table] || [])

const showGranularity = computed(() => queryParams.dimension === 'date')

const granularityOptions = GRANULARITY_OPTIONS

const pageSizeOptions = PAGINATION_CONFIG.pageSizeOptions

const metricOptions = computed(() => COLUMN_CONFIG[queryParams.table] || [])

const tableData = ref([])
const chartSeriesRows = ref([])
const chartMeta = ref({})
const tableTotal = ref(0)
const appliedParams = ref(null)
const tableColumns = ref([])
const loading = ref(false)
const selectedMetric = ref('')
const chartRef = ref(null)
const tableRef = ref(null)
let chartInstance = null
let activeQueryController = null
let latestRequestToken = 0
const storeOptions = ref([])
const currentUser = ref(null)

// 获取当前用户信息
const loadCurrentUser = () => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      currentUser.value = JSON.parse(userStr)
    }
  } catch (error) {
    console.error('加载用户信息失败:', error)
  }
}

// 获取店长的门店名称
const managerStoreName = computed(() => {
  if (!currentUser.value || currentUser.value.role !== 'manager') {
    return ''
  }
  if (!currentUser.value.store_id || !storeOptions.value.length) {
    return '我的门店'
  }
  const userStore = storeOptions.value.find(store => store.id === currentUser.value.store_id)
  return userStore ? userStore.name : '我的门店'
})

const chartType = computed(() => (queryParams.dimension === 'date' ? 'line' : 'bar'))

const snapshotCurrentQuery = () => ({
  table: queryParams.table,
  dimension: queryParams.dimension,
  granularity: queryParams.dimension === 'date' ? queryParams.granularity : undefined,
  store_id: queryParams.store_id ?? null,
  dateRange: Array.isArray(queryParams.dateRange) ? [...queryParams.dateRange] : []
})

const normalizeRangeKey = (range) =>
  Array.isArray(range) && range.length === 2 ? range.join('|') : ''

const isViewSynced = computed(() => {
  if (!appliedParams.value) {
    return false
  }
  const targetGranularity = queryParams.dimension === 'date' ? queryParams.granularity : undefined
  return (
    appliedParams.value.table === queryParams.table &&
    appliedParams.value.dimension === queryParams.dimension &&
    appliedParams.value.granularity === targetGranularity &&
    appliedParams.value.store_id === (queryParams.store_id ?? null) &&
    normalizeRangeKey(appliedParams.value.dateRange) === normalizeRangeKey(queryParams.dateRange)
  )
})

const renderedTableData = computed(() =>
  isViewSynced.value ? tableData.value : EMPTY_DATASET
)

const renderedTableTotal = computed(() =>
  isViewSynced.value ? tableTotal.value : 0
)

const chartSourceRows = computed(() =>
  isViewSynced.value ? chartSeriesRows.value : EMPTY_DATASET
)

const chartPointCount = computed(() => chartSourceRows.value.length)

const CHART_CONFIG = Object.freeze({
  dataZoomThreshold: 80,
  sliderWindowThreshold: 120,
  defaultWindowSize: 100,
  safeSymbolThreshold: 300,
  denseThreshold: 1200,
  heavyThreshold: 3000
})

const GRANULARITY_LABEL_MAP = {
  day: '按日',
  week: '按周',
  month: '按月'
}

const detectChartMode = (count) => {
  if (count === 0) return 'empty'
  if (count <= CHART_CONFIG.safeSymbolThreshold) return 'normal'
  if (count <= CHART_CONFIG.denseThreshold) return 'dense'
  if (count <= CHART_CONFIG.heavyThreshold) return 'heavy'
  return 'overload'
}

const chartMode = computed(() => detectChartMode(chartPointCount.value))

const chartNeedsDataZoom = computed(
  () => chartPointCount.value > CHART_CONFIG.dataZoomThreshold
)

const formatDimensionLabel = (value) => {
  const label = value ?? '--'
  if (typeof label !== 'string') {
    return String(label)
  }
  return label.length > 20 ? `${label.slice(0, 18)}…` : label
}

const normalizeRow = (item) => ({
  ...item,
  dimension_value: item.dimension_label || item.dimension_key || '--'
})

const hasChartData = computed(
  () =>
    isViewSynced.value &&
    chartSourceRows.value.length > 0 &&
    Boolean(selectedMetric.value)
)

const paginationDisabled = computed(() => !appliedParams.value || !isViewSynced.value)

const currentMetricLabel = computed(() => {
  const current = metricOptions.value.find((item) => item.prop === selectedMetric.value)
  return current?.label || ''
})

const buildTableColumns = () => {
  const dimensionKey = queryParams.dimension
  const dimensionColumn = DIMENSION_COLUMN_MAP[dimensionKey] || {
    label: '当前维度',
    prop: 'dimension_value',
    minWidth: 140
  }
  const metrics = COLUMN_CONFIG[queryParams.table] || []
  tableColumns.value = [dimensionColumn, ...metrics]
}

const resetResultState = () => {
  tableData.value = []
  chartSeriesRows.value = []
  tableTotal.value = 0
  chartMeta.value = {}
  appliedParams.value = null
}

const cloneSnapshot = (snapshot) => {
  if (!snapshot) {
    return null
  }
  return {
    ...snapshot,
    dateRange: Array.isArray(snapshot.dateRange) ? [...snapshot.dateRange] : []
  }
}

const cancelActiveQuery = () => {
  if (activeQueryController) {
    activeQueryController.abort()
    activeQueryController = null
  }
}

const isAbortError = (error) =>
  error?.code === 'ERR_CANCELED' ||
  error?.name === 'CanceledError' ||
  error?.message === 'canceled'

const scrollTableToTop = () => {
  nextTick(() => {
    if (tableRef.value?.setScrollTop) {
      tableRef.value.setScrollTop(0)
    }
  })
}

const performQuery = async ({ resetPage = false, source = 'query', paramsSnapshot } = {}) => {
  const snapshotSource =
    paramsSnapshot ||
    (source === 'query'
      ? snapshotCurrentQuery()
      : appliedParams.value)

  const snapshot = cloneSnapshot(snapshotSource)

  if (!snapshot) {
    if (source === 'query') {
      ElMessage.warning('请选择完整的时间范围后再查询')
    }
    return
  }

  const [startDate, endDate] = snapshot.dateRange || []
  if (!startDate || !endDate) {
    if (source === 'query') {
      ElMessage.warning('请选择完整的时间范围后再查询')
    }
    return
  }

  if (resetPage) {
    pagination.page = PAGINATION_CONFIG.defaultPage
  }

  const rawParams = {
    table: snapshot.table,
    dimension: snapshot.dimension,
    granularity: snapshot.dimension === 'date' ? snapshot.granularity : undefined,
    start_date: startDate,
    end_date: endDate,
    store_id: snapshot.store_id ?? undefined,
    page: pagination.page,
    page_size: Math.min(
      pagination.pageSize || PAGINATION_CONFIG.defaultPageSize,
      PAGINATION_CONFIG.maxPageSize
    )
  }
  const requestParams = Object.fromEntries(
    Object.entries(rawParams).filter(([, value]) => value !== undefined && value !== null && value !== '')
  )

  cancelActiveQuery()
  const controller = new AbortController()
  activeQueryController = controller
  const requestId = ++latestRequestToken
  loading.value = true

  try {
    const response = await queryStats(requestParams, { signal: controller.signal })
    const payload = response?.data || {}
    if (response?.success) {
      const rows = Array.isArray(payload.rows) ? payload.rows : []
      const seriesRows = Array.isArray(payload.series_rows) ? payload.series_rows : []
      tableData.value = rows.map(normalizeRow)
      chartSeriesRows.value = seriesRows.map(normalizeRow)
      const parsedTotal = Number(payload.total)
      tableTotal.value = Number.isFinite(parsedTotal) ? parsedTotal : rows.length || 0
      chartMeta.value = payload.meta || {}
      appliedParams.value = snapshot
      if (source === 'pagination' || source === 'pageSize') {
        scrollTableToTop()
      }
    } else {
      resetResultState()
    }
  } catch (error) {
    if (isAbortError(error)) {
      return
    }
    console.error('[GeneralAnalysis] 查询失败:', error)
    ElMessage.error('查询失败，请稍后重试')
    resetResultState()
  } finally {
    if (activeQueryController === controller) {
      activeQueryController = null
    }
    if (requestId === latestRequestToken) {
      loading.value = false
    }
  }
}

const handleQuery = () => {
  performQuery({ resetPage: true, source: 'query' })
}

const handlePageChange = (page) => {
  if (!appliedParams.value || !isViewSynced.value || page === pagination.page) {
    return
  }
  pagination.page = page
  performQuery({ source: 'pagination', paramsSnapshot: appliedParams.value })
}

const handlePageSizeChange = (size) => {
  if (!appliedParams.value || !isViewSynced.value || size === pagination.pageSize) {
    return
  }
  pagination.pageSize = size
  pagination.page = PAGINATION_CONFIG.defaultPage
  performQuery({ source: 'pageSize', paramsSnapshot: appliedParams.value })
}

const fetchStoreOptions = async () => {
  try {
    const response = await listStores(true)
    if (Array.isArray(response?.data)) {
      storeOptions.value = response.data
      // 如果是店长，自动设置门店ID
      if (currentUser.value?.role === 'manager' && currentUser.value.store_id) {
        queryParams.store_id = currentUser.value.store_id
      }
    } else {
      storeOptions.value = []
    }
  } catch (error) {
    console.error('[GeneralAnalysis] 门店列表获取失败:', error)
    storeOptions.value = []
  }
}

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

const buildChartOption = () => {
  if (!hasChartData.value) {
    return null
  }

  const metric = metricOptions.value.find((item) => item.prop === selectedMetric.value)
  if (!metric) {
    return null
  }

  const sourceData = chartSourceRows.value
  const xData = sourceData.map((item) => item.dimension_value ?? '--')
  const yData = sourceData.map((item) => Number(item[metric.prop]) || 0)
  const mode = chartMode.value
  const isLine = chartType.value === 'line'
  const showSymbol = isLine && mode === 'normal'
  const smooth = isLine && mode === 'normal'
  const sampling = mode === 'heavy' || mode === 'overload' ? 'lttb' : undefined

  const series = {
    name: metric.label,
    type: chartType.value,
    data: yData,
    smooth,
    showSymbol,
    symbol: showSymbol ? 'circle' : 'none',
    symbolSize: showSymbol ? 6 : 0,
    sampling
  }

  if (isLine) {
    series.areaStyle = showSymbol ? { opacity: 0.12 } : undefined
    series.lineStyle = {
      width: mode === 'normal' ? 2 : mode === 'dense' ? 1.5 : 1,
      opacity: mode === 'overload' ? 0.9 : 1
    }
  } else {
    series.showBackground = true
    series.backgroundStyle = {
      color: 'rgba(64, 158, 255, 0.05)'
    }
    series.barMaxWidth = mode === 'overload' ? 14 : 24
  }

  const axisLabelInterval = (() => {
    const count = chartPointCount.value
    if (count <= 40) return 0
    if (mode === 'dense') return Math.ceil(count / 12)
    if (mode === 'heavy') return Math.ceil(count / 18)
    if (mode === 'overload') return Math.ceil(count / 24)
    return 0
  })()

  const dataZoom = []
  if (chartNeedsDataZoom.value) {
    dataZoom.push({
      type: 'inside',
      moveOnMouseWheel: true,
      zoomOnMouseWheel: 'shift',
      moveOnMouseMove: true,
      minSpan: 5
    })
    const slider = {
      type: 'slider',
      height: 18,
      bottom: 6,
      showDetail: false,
      brushSelect: true,
      handleSize: 10
    }
    if (chartPointCount.value > CHART_CONFIG.sliderWindowThreshold) {
      slider.startValue = Math.max(
        0,
        chartPointCount.value - CHART_CONFIG.defaultWindowSize
      )
      slider.endValue = chartPointCount.value - 1
    }
    dataZoom.push(slider)
  }

  const toolbox =
    dataZoom.length > 0
      ? {
          feature: {
            restore: { title: '重置缩放' },
            saveAsImage: { show: false }
          },
          top: 8,
          right: 12
        }
      : undefined

  return {
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      left: 20,
      right: 20,
      top: 60,
      bottom: 20,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: chartType.value === 'bar',
      axisLabel: {
        rotate: 45,
        interval: axisLabelInterval,
        formatter: formatDimensionLabel,
        width: 100,
        overflow: 'truncate',
        ellipsis: '...'
      }
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    toolbox,
    dataZoom,
    series: [series],
    color: ['#409EFF']
  }
}

const updateChart = () => {
  if (!chartInstance) {
    return
  }

  const option = buildChartOption()
  if (!option) {
    chartInstance.clear()
    return
  }

  chartInstance.setOption(option, true)
}

const initChart = () => {
  if (!chartRef.value || chartInstance) {
    return
  }
  chartInstance = echarts.init(chartRef.value)
  window.addEventListener('resize', handleResize)
  updateChart()
}

const handleResetZoom = () => {
  if (!chartInstance || !chartNeedsDataZoom.value) {
    return
  }
  if (chartPointCount.value > CHART_CONFIG.sliderWindowThreshold) {
    const endValue = chartPointCount.value - 1
    const startValue = Math.max(0, endValue - CHART_CONFIG.defaultWindowSize)
    chartInstance.dispatchAction({
      type: 'dataZoom',
      startValue,
      endValue
    })
  } else {
    chartInstance.dispatchAction({
      type: 'dataZoom',
      start: 0,
      end: 100
    })
  }
}

const chartNotices = computed(() => {
  const notices = []
  const meta = chartMeta.value || {}

  if (meta.auto_adjusted) {
    const granularityText =
      GRANULARITY_LABEL_MAP[meta.series_granularity] ||
      meta.series_granularity ||
      ''
    notices.push({
      type: 'info',
      message: granularityText
        ? `已自动调整时间粒度为 ${granularityText} 展示`
        : '已自动调整时间粒度以保障可读性'
    })
  }

  if (meta.is_truncated) {
    notices.push({
      type: 'warning',
      message: '结果已按 Top-N 截断，图表仅展示受控范围内的数据。'
    })
  }

  const suggestions = Array.isArray(meta.suggestions)
    ? meta.suggestions
    : meta.suggestions
      ? [meta.suggestions]
      : []
  suggestions.slice(0, 3).forEach((tip) => {
    notices.push({
      type: 'warning',
      message: tip
    })
  })

  if (chartMode.value === 'heavy') {
    notices.push({
      type: 'warning',
      message: '数据点超过 1200 个，已开启降级渲染与默认缩放，建议缩小时间范围或提升粒度。'
    })
  } else if (chartMode.value === 'overload') {
    notices.push({
      type: 'error',
      message: '数据点超过 3000 个，当前仅展示最新窗口。请缩小查询范围或提升粒度以查看完整趋势。'
    })
  }

  return notices
})

watch(
  () => queryParams.table,
  (nextTable) => {
    tableData.value = []
    chartSeriesRows.value = []
    chartMeta.value = {}
    tableTotal.value = 0
    appliedParams.value = null
    pagination.page = PAGINATION_CONFIG.defaultPage
    cancelActiveQuery()
    const defaultDimension = DEFAULT_DIMENSION_MAP[nextTable] || 'date'
    queryParams.dimension = defaultDimension
  },
  { immediate: true }
)

watch(
  metricOptions,
  (options) => {
    if (!options.length) {
      selectedMetric.value = ''
      return
    }
    if (!options.some((item) => item.prop === selectedMetric.value)) {
      selectedMetric.value = options[0].prop
    }
  },
  { immediate: true }
)

watch(
  () => [queryParams.table, queryParams.dimension],
  () => {
    buildTableColumns()
  },
  { immediate: true }
)

watch(
  [chartSourceRows, selectedMetric, () => queryParams.dimension, isViewSynced],
  () => {
    nextTick(() => {
      if (!isViewSynced.value) {
        if (chartInstance) {
          chartInstance.clear()
        }
        return
      }
      updateChart()
    })
  },
  { deep: true }
)

// 确保店长的门店ID固定为其所属门店
watch(
  () => currentUser.value?.store_id,
  (storeId) => {
    if (currentUser.value?.role === 'manager' && storeId) {
      queryParams.store_id = storeId
    }
  },
  { immediate: true }
)

onMounted(() => {
  loadCurrentUser()
  fetchStoreOptions()
  nextTick(() => {
    initChart()
  })
})

onBeforeUnmount(() => {
  cancelActiveQuery()
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

</script>

<style lang="scss" scoped>
.general-analysis {
  padding: 16px;

  .analysis-card {
    min-height: 360px;
  }

  .query-toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;

    .toolbar-item {
      display: flex;
      flex-direction: column;
      min-width: 180px;

      .toolbar-label {
        font-size: 13px;
        color: #606266;
        margin-bottom: 6px;
      }
    }

    .toolbar-action {
      justify-content: flex-end;
      min-width: auto;
      align-items: flex-end;
      display: flex;
    }
  }

  .chart-section {
    margin-bottom: 16px;

    .chart-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 12px;

      .chart-info {
        display: flex;
        flex-direction: column;

        h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
        }

        .chart-subtitle {
          margin: 4px 0 0;
          font-size: 13px;
          color: #909399;
        }
      }

      .metric-placeholder {
        font-size: 13px;
        color: #c0c4cc;
      }

      .chart-actions {
        margin-left: auto;
      }
    }

    .chart-notice-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 12px;
    }

    .chart-body {
      position: relative;
      min-height: 350px;

      .chart-container {
        width: 100%;
        height: 350px;
      }

      .chart-empty {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #c0c4cc;
        font-size: 14px;
        background-color: rgba(255, 255, 255, 0.85);
        border: 1px dashed #ebeef5;
      }
    }
  }

  .card-header {
    display: flex;
    flex-direction: column;
    align-items: flex-start;

    h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #1d2129;
    }

    .card-subtitle {
      margin-top: 4px;
      font-size: 13px;
      color: #909399;
    }
  }

  .result-table {
    margin-bottom: 16px;
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }

}
</style>

