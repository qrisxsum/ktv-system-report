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

        <div class="toolbar-actions">
          <el-button-group>
            <el-button
              type="primary"
              plain
              size="small"
              @click="handleFinancialDailyPreset"
            >
              财务日报
            </el-button>
            <el-button
              type="success"
              plain
              size="small"
              @click="handleProductDailyPreset"
            >
              商品日报
            </el-button>
            <el-button
              type="warning"
              plain
              size="small"
              @click="handleRoomDailyPreset"
            >
              包厢运营日报
            </el-button>
          </el-button-group>
        </div>

        <!-- 自动查询：选满条件后自动触发，无需手动“查询”按钮 -->
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
          <!-- 移动端放大按钮 -->
          <el-button
            v-if="hasChartData && isMobile"
            class="chart-fullscreen-btn"
            type="primary"
            circle
            @click="openFullscreenChart"
          >
            <el-icon><FullScreen /></el-icon>
          </el-button>
          <!-- 移动端数据截断提示 -->
          <div v-if="isMobile && isChartTruncated" class="chart-truncate-tip">
            <el-tag type="info" size="small">
              竖屏显示前 {{ MOBILE_CHART_LIMIT }} 项，点击放大查看全部
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 全屏横屏图表弹窗（CSS强制横屏） -->
      <teleport to="body">
        <div
          v-if="showFullscreenChart"
          class="fullscreen-chart-overlay"
        >
          <div class="fullscreen-chart-rotated">
            <div class="fullscreen-chart-container">
              <div class="fullscreen-chart-header">
                <span class="fullscreen-chart-title">{{ currentMetricLabel }}</span>
                <el-button
                  type="danger"
                  circle
                  size="small"
                  @click="closeFullscreenChart"
                >
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
              <div ref="fullscreenChartRef" class="fullscreen-chart-body"></div>
            </div>
          </div>
        </div>
      </teleport>

      <el-table
        ref="tableRef"
        class="result-table"
        :data="renderedTableData"
        border
        stripe
        v-loading="loading"
        :empty-text="loading ? '数据加载中…' : '暂无数据，请先执行查询'"
        @sort-change="handleSortChange"
      >
        <template v-for="(column, colIndex) in tableColumns" :key="columnKey(column)">
          <el-table-column
            v-if="column.children"
            :label="column.label"
            :align="column.align || 'center'"
          >
            <el-table-column
              v-for="child in column.children"
              :key="columnKey(child)"
              :prop="child.prop"
              :label="child.label"
              :min-width="child.minWidth || 120"
              :align="child.align || 'left'"
              sortable="custom"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                <span
                  v-if="child.format === 'percent'"
                  :class="buildPercentCellClass(child, row)"
                >
                  {{ formatPercentCell(row[child.prop], child.digits) }}
                </span>
                <span v-else-if="child.format === 'currency'">
                  {{ formatCurrencyCell(row[child.prop], child.digits, child) }}
                </span>
                <span v-else>
                  {{ formatDefaultCell(row[child.prop]) }}
                </span>
              </template>
            </el-table-column>
          </el-table-column>
          <el-table-column
            v-else
            :prop="column.prop"
            :label="column.label"
            :min-width="column.minWidth || 120"
            :align="column.align || 'left'"
            :fixed="column.fixed"
            :sortable="colIndex !== 0 || queryParams.dimension === 'date' ? 'custom' : false"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <span
                v-if="column.format === 'percent'"
                :class="buildPercentCellClass(column, row)"
              >
                {{ formatPercentCell(row[column.prop], column.digits) }}
              </span>
              <span v-else-if="column.format === 'currency'">
                {{ formatCurrencyCell(row[column.prop], column.digits, column) }}
              </span>
              <span v-else>
                {{ formatDefaultCell(row[column.prop]) }}
              </span>
            </template>
          </el-table-column>
        </template>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          background
          :layout="paginationLayout"
          :current-page="pagination.page"
          :page-size="pagination.pageSize"
          :page-sizes="pageSizeOptions"
          :total="renderedTableTotal"
          :disabled="paginationDisabled"
          :pager-count="pagerCount"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>

    </el-card>
  </div>
</template>

<script setup>
import { reactive, computed, watch, ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { FullScreen, Close } from '@element-plus/icons-vue'
import { queryStats } from '@/api/stats'
import { listStores } from '@/api/store'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'
import { usePagination } from '@/composables/usePagination'

const EMPTY_DATASET = Object.freeze([])
const PAGINATION_CONFIG = Object.freeze({
  defaultPage: 1,
  defaultPageSize: 50,
  pageSizeOptions: [20, 50, 100, 200],
  maxPageSize: 200
})

// 移动端图表限制配置
const MOBILE_CHART_LIMIT = 15
const MOBILE_BREAKPOINT = 768

const queryParams = reactive({
  table: 'sales',
  dateRange: [],
  dimension: 'date',
  granularity: 'day',
  store_id: null
})
const generalAnalysisStateKey = 'viewState:GeneralAnalysis:state'
// 兼容旧版本仅保存 dateRange 的 key
const legacyDateRangeStorageKey = 'viewState:GeneralAnalysis:dateRange'
const route = useRoute()

const pagination = reactive({
  page: PAGINATION_CONFIG.defaultPage,
  pageSize: PAGINATION_CONFIG.defaultPageSize
})

const sortState = reactive({
  prop: null,
  order: null
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
    { label: '商品', value: 'product' },
    { label: '商品类别', value: 'category' }
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
    { label: '包厢类型', value: 'room_type' },
    { label: '订房人', value: 'booker' },
    { label: '业务时段', value: 'time_slot' }
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
  date: { label: '日期', prop: 'dimension_value', minWidth: 140, fixed: 'left' },
  store: { label: '门店', prop: 'dimension_value', minWidth: 160, fixed: 'left' },
  employee: { label: '员工', prop: 'dimension_value', minWidth: 160, fixed: 'left' },
  product: { label: '商品名称', prop: 'dimension_value', minWidth: 160, fixed: 'left' },
  category: { label: '商品类别', prop: 'dimension_value', minWidth: 160, fixed: 'left' },
  room: { label: '包厢', prop: 'dimension_value', minWidth: 140, fixed: 'left' },
  room_type: { label: '包厢类型', prop: 'dimension_value', minWidth: 160, fixed: 'left' },
  booker: { label: '订房人', prop: 'dimension_value', minWidth: 160, fixed: 'left' },
  time_slot: { label: '业务时段', prop: 'dimension_value', minWidth: 140, fixed: 'left' }
}

const COLUMN_CONFIG = {
  booking: [
    { prop: 'orders', label: '订单数', align: 'right', minWidth: 100 },
    { prop: 'actual', label: '实收金额', align: 'right', minWidth: 140 },
    { prop: 'performance', label: '业绩', align: 'right', minWidth: 120 },
    { prop: 'credit_amount', label: '挂账金额', align: 'right', minWidth: 120 },
    { prop: 'sales_amount', label: '销售金额(应收)', align: 'right', minWidth: 140 },
    { prop: 'avg_order_amount', label: '单均消费', align: 'right', minWidth: 120 },
    { prop: 'service_fee', label: '服务费', align: 'right', minWidth: 120 },
    { prop: 'actual_rate', label: '实收转化率', align: 'right', minWidth: 140, format: 'percent' },
    { prop: 'credit_rate', label: '挂账率', align: 'right', minWidth: 140, format: 'percent' },
    { prop: 'free_amount', label: '免单金额', align: 'right', minWidth: 120 },
    { prop: 'round_off_amount', label: '抹零金额', align: 'right', minWidth: 120 },
    { prop: 'discount_amount', label: '折扣金额', align: 'right', minWidth: 120 },
    { prop: 'gift_amount', label: '赠送金额', align: 'right', minWidth: 120 },
    { prop: 'adjustment_amount', label: '调整金额', align: 'right', minWidth: 120 },
    { prop: 'pay_wechat', label: '微信支付', align: 'right', minWidth: 120 },
    { prop: 'pay_alipay', label: '支付宝支付', align: 'right', minWidth: 120 },
    { prop: 'pay_scan', label: '扫码支付', align: 'right', minWidth: 120 },
    { prop: 'pay_cash', label: '现金支付', align: 'right', minWidth: 120 },
    { prop: 'pay_pos', label: 'POS银行卡', align: 'right', minWidth: 120 },
    { prop: 'pay_member', label: '会员支付', align: 'right', minWidth: 120 },
    { prop: 'pay_deposit', label: '定金消费', align: 'right', minWidth: 120 },
    { prop: 'pay_douyin', label: '抖音核销', align: 'right', minWidth: 120 },
    { prop: 'pay_meituan', label: '美团核销', align: 'right', minWidth: 120 }
  ],
  sales: [
    { prop: 'sales_qty', label: '销量', align: 'right', minWidth: 100 },
    { prop: 'sales_amount', label: '销售额', align: 'right', minWidth: 120 },
    { prop: 'actual_amount', label: '实收金额', align: 'right', minWidth: 120 },
    { prop: 'gift_amount', label: '赠送金额', align: 'right', minWidth: 120 },
    { prop: 'gift_rate', label: '赠送率', align: 'right', minWidth: 120, format: 'percent' },
    { prop: 'cost', label: '成本', align: 'right', minWidth: 100 },
    { prop: 'profit', label: '毛利', align: 'right', minWidth: 100 },
    { prop: 'unit_profit', label: '单品毛利', align: 'right', minWidth: 120 },
    { prop: 'profit_rate', label: '成本利润率', align: 'right', minWidth: 140, format: 'percent' },
    { prop: 'actual_rate', label: '实收转化率', align: 'right', minWidth: 140, format: 'percent' }
  ],
  room: [
    { prop: 'orders', label: '开台数', align: 'right', minWidth: 100 },
    { prop: 'gmv', label: 'GMV（应收）', align: 'right', minWidth: 140, format: 'currency', digits: 0 },
    { prop: 'bill_total', label: '账单合计', align: 'right', minWidth: 140, format: 'currency', digits: 0 },
    { prop: 'actual', label: '实收金额', align: 'right', minWidth: 140, format: 'currency', digits: 0 },
    {
      prop: 'min_consumption',
      label: '最低消费',
      align: 'right',
      minWidth: 140,
      format: 'currency',
      digits: 0,
      nullWhenZero: true
    },
    {
      prop: 'min_consumption_diff',
      label: '低消差额',
      align: 'right',
      minWidth: 140,
      format: 'currency',
      digits: 0
    },
    {
      prop: 'low_consume_rate',
      label: '低消达成率',
      align: 'right',
      minWidth: 140,
      format: 'percent',
      digits: 2,
      bold: true
    },
    { prop: 'gift_amount', label: '赠送金额', align: 'right', minWidth: 140, format: 'currency', digits: 0 },
    {
      prop: 'gift_ratio',
      label: '赠送比例',
      align: 'right',
      minWidth: 140,
      format: 'percent',
      digits: 2,
      bold: true,
      warnThreshold: 0.2
    },
    { prop: 'room_discount', label: '房费折扣', align: 'right', minWidth: 120, format: 'currency', digits: 0 },
    { prop: 'beverage_discount', label: '酒水折扣', align: 'right', minWidth: 120, format: 'currency', digits: 0 },
    { prop: 'free_amount', label: '免单金额', align: 'right', minWidth: 140, format: 'currency', digits: 0 },
    { prop: 'credit_amount', label: '挂账金额', align: 'right', minWidth: 140, format: 'currency', digits: 0 },
    { prop: 'duration', label: '时长 (分钟)', align: 'right', minWidth: 120 }
  ]
}

const BOOKING_COLUMN_GROUPS = Object.freeze([
  {
    label: '基础指标区',
    columns: ['orders', 'performance', 'avg_order_amount', 'service_fee']
  },
  {
    label: '财务对账区',
    columns: ['sales_amount', 'actual', 'actual_rate', 'credit_amount', 'credit_rate']
  },
  {
    label: '损耗明细区',
    columns: ['free_amount', 'round_off_amount', 'discount_amount', 'gift_amount', 'adjustment_amount']
  },
  {
    label: '支付渠道区',
    columns: [
      'pay_wechat',
      'pay_alipay',
      'pay_scan',
      'pay_cash',
      'pay_pos',
      'pay_member',
      'pay_deposit',
      'pay_douyin',
      'pay_meituan'
    ]
  }
])

const tableOptions = TABLE_OPTIONS

const dimensionOptions = computed(() => {
  const options = DIMENSION_OPTIONS_MAP[queryParams.table] || []
  // 当数据源为包厢时，暂时隐藏包厢维度选项
  if (queryParams.table === 'room') {
    return options.filter(option => option.value !== 'room')
  }
  return options
})

const showGranularity = computed(() => queryParams.dimension === 'date')

const granularityOptions = GRANULARITY_OPTIONS

// 使用分页优化 Composable
const { pageSizeOptions, paginationLayout, pagerCount, checkDevice } = usePagination({
  desktopPageSizes: PAGINATION_CONFIG.pageSizeOptions,
  mobilePageSizes: [20, 50]
})

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
const fullscreenChartRef = ref(null)
let chartInstance = null
let fullscreenChartInstance = null
let activeQueryController = null
let latestRequestToken = 0
const storeOptions = ref([])
const currentUser = ref(null)

// 移动端相关状态
const isMobile = ref(false)
const showFullscreenChart = ref(false)

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

// 移动端图表是否被截断
const isChartTruncated = computed(() => {
  return isMobile.value && chartSourceRows.value.length > MOBILE_CHART_LIMIT
})

// 移动端竖屏显示的数据（限制数量）
const mobileChartData = computed(() => {
  if (!isMobile.value) {
    return chartSourceRows.value
  }
  return chartSourceRows.value.slice(0, MOBILE_CHART_LIMIT)
})

// 检测是否为移动设备
const checkMobile = () => {
  isMobile.value = window.innerWidth <= MOBILE_BREAKPOINT
}

const snapshotCurrentQuery = () => ({
  table: queryParams.table,
  dimension: queryParams.dimension,
  granularity: queryParams.dimension === 'date' ? queryParams.granularity : undefined,
  store_id: queryParams.store_id ?? null,
  dateRange: Array.isArray(queryParams.dateRange) ? [...queryParams.dateRange] : []
})

const buildViewState = () => ({
  query: snapshotCurrentQuery(),
  selectedMetric: selectedMetric.value || '',
  pageSize: pagination.pageSize
})

const applyViewState = (state) => {
  const query = state?.query
  if (!query) return
  if (query.table) queryParams.table = query.table
  if (query.dimension) queryParams.dimension = query.dimension
  if (query.granularity) queryParams.granularity = query.granularity
  queryParams.store_id = query.store_id ?? null
  queryParams.dateRange = Array.isArray(query.dateRange) ? [...query.dateRange] : []

  const size = Number(state?.pageSize)
  if (Number.isFinite(size) && size > 0) {
    pagination.pageSize = size
  }
  const metric = state?.selectedMetric
  if (typeof metric === 'string') {
    selectedMetric.value = metric
  }
}

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
  
  // 如果是带门店名的员工标签格式：员工名(门店名)
  const storeNameMatch = label.match(/^(.+?)\((.+?)\)$/)
  if (storeNameMatch) {
    const employeeName = storeNameMatch[1]
    const storeName = storeNameMatch[2]
    
    // 如果总长度超过限制，优先保留员工名，门店名可适当截断
    const maxLength = 20
    if (label.length > maxLength) {
      // 计算员工名长度 + 括号 + 门店名可用空间
      const availableStoreNameLength = maxLength - employeeName.length - 3 // 3 = "()" + "…"
      if (availableStoreNameLength > 0) {
        const truncatedStoreName = storeName.length > availableStoreNameLength
          ? `${storeName.slice(0, availableStoreNameLength)}…`
          : storeName
        return `${employeeName}(${truncatedStoreName})`
      } else {
        // 如果员工名本身就很长，只显示员工名
        return employeeName.length > maxLength 
          ? `${employeeName.slice(0, maxLength - 1)}…`
          : employeeName
      }
    }
    return label
  }
  
  // 普通标签处理
  return label.length > 20 ? `${label.slice(0, 18)}…` : label
}

const toFiniteNumber = (value, fallback = 0) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

const computeRatio = (numerator, denominator, digits = 4) => {
  if (!denominator) return 0
  const ratio = numerator / denominator
  return Number.isFinite(ratio) ? Number(ratio.toFixed(digits)) : 0
}

const computeAverage = (sum, count, digits = 2) => {
  if (!count) return 0
  const avg = sum / count
  return Number.isFinite(avg) ? Number(avg.toFixed(digits)) : 0
}

const withBookingDerivedMetrics = (row) => {
  const actual = toFiniteNumber(row.actual)
  const credit = toFiniteNumber(row.credit_amount)
  const sales = toFiniteNumber(row.sales_amount)
  const orders = toFiniteNumber(row.orders)

  return {
    ...row,
    avg_order_amount: computeAverage(actual, orders, 2),
    credit_rate: computeRatio(credit, actual, 4),
    actual_rate: computeRatio(actual, sales, 4)
  }
}

const withSalesDerivedMetrics = (row) => {
  const profit = toFiniteNumber(row.profit)
  const cost = toFiniteNumber(row.cost ?? row.cost_total)
  const salesAmount = toFiniteNumber(row.sales_amount)
  const salesQty = toFiniteNumber(row.sales_qty)
  const giftQty = toFiniteNumber(row.gift_qty)
  const totalQty = salesQty + giftQty
  const actualAmount = toFiniteNumber(row.actual ?? row.actual_amount, salesAmount)
  const billTotal = toFiniteNumber(row.bill_total ?? row.sales_amount, salesAmount)

  return {
    ...row,
    cost,
    actual_amount: actualAmount,
    gift_rate: computeRatio(giftQty, totalQty, 4),
    profit_rate: computeRatio(profit, cost, 4),
    unit_profit: computeAverage(profit, salesQty, 2),
    actual_rate: computeRatio(actualAmount, billTotal, 4)
  }
}

const withRoomDerivedMetrics = (row) => {
  const billTotal = toFiniteNumber(row.bill_total ?? row.gmv ?? row.receivable_amount)
  const hasMinConsumption = row.min_consumption !== null && row.min_consumption !== undefined
  const minConsumption = hasMinConsumption ? toFiniteNumber(row.min_consumption) : null
  const minDiffSource = row.min_consumption_diff ?? row.low_consume_diff
  const computedDiff =
    minConsumption !== null && minConsumption > 0
      ? Number(Math.max(minConsumption - billTotal, 0).toFixed(2))
      : 0
  const minConsumptionDiff =
    minDiffSource !== null && minDiffSource !== undefined
      ? toFiniteNumber(minDiffSource)
      : computedDiff
  const giftAmount =
    row.gift_amount !== null && row.gift_amount !== undefined
      ? toFiniteNumber(row.gift_amount)
      : 0
  const freeAmount =
    row.free_amount !== null && row.free_amount !== undefined
      ? toFiniteNumber(row.free_amount)
      : 0
  const creditAmount =
    row.credit_amount !== null && row.credit_amount !== undefined
      ? toFiniteNumber(row.credit_amount)
      : 0

  // 低消达成率：优先使用后端计算好的值（后端已按正确逻辑计算平均值）
  // 如果后端未返回，则使用聚合值计算（作为兜底，但这种情况应该很少见）
  const lowConsumeRate = row.low_consume_rate !== null && row.low_consume_rate !== undefined
    ? Number(Number(row.low_consume_rate).toFixed(4))
    : (minConsumption !== null && minConsumption > 0
        ? Number((billTotal / minConsumption).toFixed(4))
        : null)

  return {
    ...row,
    bill_total: billTotal,
    min_consumption: minConsumption,
    min_consumption_diff: minConsumptionDiff,
    low_consume_rate: lowConsumeRate,
    gift_amount: giftAmount,
    gift_ratio:
      billTotal > 0 && Number.isFinite(giftAmount)
        ? Number((giftAmount / billTotal).toFixed(4))
        : null,
    free_amount: freeAmount,
    credit_amount: creditAmount
  }
}

const normalizeRow = (item, table) => {
  const baseRow = {
    ...item,
    dimension_value: item.dimension_label || item.dimension_key || '--'
  }
  if (table === 'booking') {
    return withBookingDerivedMetrics(baseRow)
  }
  if (table === 'sales') {
    return withSalesDerivedMetrics(baseRow)
  }
  if (table === 'room') {
    return withRoomDerivedMetrics(baseRow)
  }
  return baseRow
}

const formatCurrencyValue = (value, digits = 2) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '--'
  }
  return `¥${numeric.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  })}`
}

const formatPercentValue = (value, digits = 2) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '--'
  }
  return `${(numeric * 100).toFixed(digits)}%`
}

const formatDefaultCell = (value) => {
  if (value === null || value === undefined || value === '') {
    return '--'
  }
  return value
}

const shouldShowPlaceholder = (value, column) => {
  if (value === null || value === undefined || value === '') {
    return true
  }
  if (column?.nullWhenZero && Number(value) === 0) {
    return true
  }
  return false
}

const formatCurrencyCell = (value, digits = 2, column) => {
  if (shouldShowPlaceholder(value, column)) {
    return '--'
  }
  const decimalDigits = Number.isFinite(Number(digits)) ? Number(digits) : 2
  return formatCurrencyValue(value, decimalDigits)
}

const formatPercentCell = (value, digits = 2) => {
  const numeric = toFiniteNumber(value, NaN)
  if (!Number.isFinite(numeric)) {
    return '--'
  }
  const decimalDigits = Number.isFinite(Number(digits)) ? Number(digits) : 2
  return formatPercentValue(numeric, decimalDigits)
}

const buildPercentCellClass = (column, row) => {
  const classes = ['percent-text']
  if (column?.bold) {
    classes.push('percent-strong')
  }
  if (column?.warnThreshold !== undefined) {
    const numeric = toFiniteNumber(row?.[column.prop], NaN)
    if (Number.isFinite(numeric) && numeric > column.warnThreshold) {
      classes.push('is-warning')
    }
  }
  return classes
}

const columnKey = (column) => {
  if (!column) return ''
  return column.prop || column.label || ''
}

const hasChartData = computed(
  () =>
    isViewSynced.value &&
    chartSourceRows.value.length > 0 &&
    Boolean(selectedMetric.value)
)

const paginationDisabled = computed(() => !appliedParams.value || !isViewSynced.value)

  const currentMetricLabel = computed(() => {
    const current = metricOptions.value.find((item) => item.prop === selectedMetric.value)
    let label = current?.label || ''
    if (queryParams.dimension === 'booker' && label) {
      label += ' (已排除散户数据)'
    }
    return label
  })

const buildTableColumns = () => {
  const dimensionKey = queryParams.dimension
  const baseDimensionColumn = DIMENSION_COLUMN_MAP[dimensionKey] || {
    label: '当前维度',
    prop: 'dimension_value',
    minWidth: 140,
    fixed: 'left'
  }
  
  // 创建列配置副本，避免修改原始对象
  const dimensionColumn = { ...baseDimensionColumn }
  
  // 手机端且维度为商品时，固定商品名称列
  if (isMobile.value && queryParams.dimension === 'product') {
    dimensionColumn.fixed = 'left'
  }
  
  // 员工维度且全部门店时，增加"所属门店"列
  const shouldShowStoreColumn = 
    queryParams.dimension === 'employee' && 
    queryParams.store_id === null &&
    queryParams.table === 'booking'
  
  if (queryParams.table === 'booking') {
    const metricMap = new Map(
      (COLUMN_CONFIG.booking || []).map((item) => [item.prop, item])
    )
    const groupedColumns = BOOKING_COLUMN_GROUPS.map((group) => {
      const children = group.columns
        .map((prop) => metricMap.get(prop))
        .filter(Boolean)
      return {
        label: group.label,
        children
      }
    }).filter((group) => group.children.length)
    
    // 如果显示全部门店，在员工列后插入门店列
    if (shouldShowStoreColumn) {
      const storeColumn = {
        prop: 'store_name',
        label: '所属门店',
        align: 'left',
        minWidth: 140
      }
      tableColumns.value = [dimensionColumn, storeColumn, ...groupedColumns]
    } else {
      tableColumns.value = [dimensionColumn, ...groupedColumns]
    }
    return
  }
  const metrics = COLUMN_CONFIG[queryParams.table] || []
  
  // 如果显示全部门店，在员工列后插入门店列
  if (shouldShowStoreColumn) {
    const storeColumn = {
      prop: 'store_name',
      label: '所属门店',
      align: 'left',
      minWidth: 140
    }
    tableColumns.value = [dimensionColumn, storeColumn, ...metrics]
  } else {
    tableColumns.value = [dimensionColumn, ...metrics]
  }
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
    ),
    sort_by: sortState.prop ?? undefined,
    sort_order: sortState.order === 'ascending' ? 'asc' : sortState.order === 'descending' ? 'desc' : undefined
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
      tableData.value = rows.map((row) => normalizeRow(row, snapshot.table))
      chartSeriesRows.value = seriesRows.map((row) => normalizeRow(row, snapshot.table))
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

const handleSortChange = ({ prop, order }) => {
  // 更新排序状态
  sortState.prop = prop || null
  sortState.order = order || null
  // 排序变化时重置到第一页
  pagination.page = PAGINATION_CONFIG.defaultPage
  // 重新查询
  if (appliedParams.value && isViewSynced.value) {
    performQuery({ source: 'sort', paramsSnapshot: appliedParams.value })
  }
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
  checkDevice()
  checkMobile()
  if (chartInstance) {
    chartInstance.resize()
  }
  if (fullscreenChartInstance) {
    fullscreenChartInstance.resize()
  }
}

const buildChartOption = (isFullscreen = false) => {
  if (!hasChartData.value) {
    return null
  }

  const metric = metricOptions.value.find((item) => item.prop === selectedMetric.value)
  if (!metric) {
    return null
  }

  // 如果是订房人维度，过滤掉散户数据，避免大值淹没小值，方便对比员工能力
  let sourceData = chartSourceRows.value
  if (queryParams.dimension === 'booker') {
    sourceData = sourceData.filter(item => item.dimension_value !== '散户')
  }

  // 移动端竖屏（非全屏）时限制显示数量
  if (isMobile.value && !isFullscreen) {
    sourceData = sourceData.slice(0, MOBILE_CHART_LIMIT)
  }

  // 员工维度且全部门店时，在员工名字后括号备注门店
  const shouldAppendStoreName = 
    queryParams.dimension === 'employee' && 
    queryParams.store_id === null

  const xData = sourceData.map((item) => {
    let label = item.dimension_value ?? '--'
    if (shouldAppendStoreName && item.store_name) {
      label = `${label}(${item.store_name})`
    }
    return label
  })
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
    sampling,
    barMinHeight: 5, // 确保小数值在柱状图中依然可见
    label: {
      show: xData.length <= 30, // 数据点较少时直接显示数值
      position: 'top',
      fontSize: 10,
      color: '#909399',
      formatter: (params) => params.value > 0 ? params.value : ''
    }
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
  // 全屏模式或数据量较大时启用 dataZoom
  const needsDataZoom = isFullscreen || chartNeedsDataZoom.value
  if (needsDataZoom) {
    dataZoom.push({
      type: 'inside',
      moveOnMouseWheel: true,
      zoomOnMouseWheel: 'shift',
      moveOnMouseMove: true,
      minSpan: 5
    })
    const slider = {
      type: 'slider',
      height: isFullscreen ? 24 : 18,
      bottom: isFullscreen ? 10 : 6,
      showDetail: isFullscreen,
      brushSelect: true,
      handleSize: isFullscreen ? 16 : 10
    }
    const totalPoints = xData.length
    if (totalPoints > CHART_CONFIG.sliderWindowThreshold) {
      slider.startValue = Math.max(
        0,
        totalPoints - CHART_CONFIG.defaultWindowSize
      )
      slider.endValue = totalPoints - 1
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

  const isCountMetric = ['orders', 'sales_qty', 'gift_qty'].includes(metric.prop)

  // 全屏模式下的配置调整
  const gridConfig = isFullscreen
    ? { left: 20, right: 20, top: 50, bottom: 60, containLabel: true }
    : { left: 20, right: 20, top: 60, bottom: 20, containLabel: true }

  // 全屏模式下标签显示更多
  const fullscreenLabelInterval = (() => {
    const count = xData.length
    if (count <= 30) return 0
    if (count <= 60) return 1
    if (count <= 100) return 2
    return Math.ceil(count / 40)
  })()

  // 全屏模式下的标签格式化函数
  const fullscreenLabelFormatter = (value) => {
    if (typeof value !== 'string') return String(value ?? '--')
    
    // 如果是带门店名的员工标签格式：员工名(门店名)
    const storeNameMatch = value.match(/^(.+?)\((.+?)\)$/)
    if (storeNameMatch) {
      const employeeName = storeNameMatch[1]
      const storeName = storeNameMatch[2]
      
      // 全屏模式下允许显示更多字符（25个字符）
      const maxLength = 25
      if (value.length > maxLength) {
        const availableStoreNameLength = maxLength - employeeName.length - 3 // 3 = "()" + "…"
        if (availableStoreNameLength > 0) {
          const truncatedStoreName = storeName.length > availableStoreNameLength
            ? `${storeName.slice(0, availableStoreNameLength)}…`
            : storeName
          return `${employeeName}(${truncatedStoreName})`
        } else {
          return employeeName.length > maxLength 
            ? `${employeeName.slice(0, maxLength - 1)}…`
            : employeeName
        }
      }
      return value
    }
    
    // 普通标签处理，全屏模式显示更多字符
    return value.length > 25 ? `${value.slice(0, 23)}…` : value
  }

  const xAxisLabelConfig = isFullscreen
    ? {
        rotate: 45,
        interval: fullscreenLabelInterval,
        fontSize: 11,
        formatter: fullscreenLabelFormatter
      }
    : {
        rotate: 45,
        interval: axisLabelInterval,
        formatter: formatDimensionLabel,
        width: 100,
        overflow: 'truncate',
        ellipsis: '...'
      }

  return {
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: isFullscreen
        ? (params) => {
            const point = params[0]
            if (!point) return ''
            return `<strong>${point.name}</strong><br/>${metric.label}: ${point.value}`
          }
        : undefined
    },
    grid: gridConfig,
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: chartType.value === 'bar',
      axisLabel: xAxisLabelConfig
    },
    yAxis: {
      type: 'value',
      minInterval: isCountMetric ? 1 : undefined,
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

// 全屏图表相关函数（使用CSS强制横屏）
const openFullscreenChart = () => {
  showFullscreenChart.value = true
  // 锁定背景滚动
  document.body.style.overflow = 'hidden'
  
  nextTick(() => {
    // 延迟初始化图表，等待DOM渲染完成
    setTimeout(() => {
      initFullscreenChart()
    }, 100)
  })
}

const closeFullscreenChart = () => {
  showFullscreenChart.value = false
  // 恢复背景滚动
  document.body.style.overflow = ''
  
  if (fullscreenChartInstance) {
    fullscreenChartInstance.dispose()
    fullscreenChartInstance = null
  }
}

const initFullscreenChart = () => {
  if (!fullscreenChartRef.value) {
    return
  }
  if (fullscreenChartInstance) {
    fullscreenChartInstance.dispose()
  }
  fullscreenChartInstance = echarts.init(fullscreenChartRef.value)
  const option = buildChartOption(true)
  if (option) {
    fullscreenChartInstance.setOption(option)
  }
}

// 监听屏幕方向变化，更新全屏图表尺寸
const handleOrientationChange = () => {
  if (showFullscreenChart.value && fullscreenChartInstance) {
    setTimeout(() => {
      fullscreenChartInstance.resize()
    }, 300)
  }
}


const chartNotices = computed(() => {
  // 已取消所有警告信息显示
  return []
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
    // 重置排序状态
    sortState.prop = null
    sortState.order = null
    cancelActiveQuery()
    const defaultDimension = DEFAULT_DIMENSION_MAP[nextTable] || 'date'
    // 使用过滤后的维度选项（已排除包厢维度）
    const dimensionCandidates = dimensionOptions.value
    const dimensionValid = dimensionCandidates.some((item) => item.value === queryParams.dimension)
    // 如果当前维度无效，或者数据源为包厢且当前维度为包厢，则切换到默认维度
    if (!dimensionValid || (nextTable === 'room' && queryParams.dimension === 'room')) {
      queryParams.dimension = defaultDimension
    }
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
  () => isMobile.value,
  () => {
    // 移动端状态变化时，重新构建列配置以更新固定列设置
    buildTableColumns()
  }
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

const suppressAutoQuery = ref(false)
let autoQueryTimer = null

const canAutoQuery = () => {
  if (!queryParams.table) return false
  if (!queryParams.dimension) return false
  if (queryParams.dimension === 'date' && !queryParams.granularity) return false
  return isValidDateRange(queryParams.dateRange)
}

const scheduleAutoQuery = ({ resetPage = true, source = 'auto' } = {}) => {
  if (suppressAutoQuery.value) return
  if (!canAutoQuery()) return

  if (autoQueryTimer) {
    clearTimeout(autoQueryTimer)
  }

  autoQueryTimer = setTimeout(() => {
    autoQueryTimer = null
    if (resetPage) {
      pagination.page = PAGINATION_CONFIG.defaultPage
    }
    performQuery({
      resetPage: false,
      source,
      paramsSnapshot: snapshotCurrentQuery()
    })
  }, 250)
}

const formatDateToYMD = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const getYesterdayDateRange = () => {
  const today = new Date()
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1)
  const formatted = formatDateToYMD(yesterday)
  return [formatted, formatted]
}

const handleFinancialDailyPreset = ({ triggerQuery = true, source = 'preset:financial' } = {}) => {
  suppressAutoQuery.value = true
  queryParams.table = 'booking'
  queryParams.dimension = 'employee'
  queryParams.granularity = 'day'
  nextTick(() => {
    suppressAutoQuery.value = false
    if (triggerQuery) {
      scheduleAutoQuery({ resetPage: true, source })
    }
  })
}

const handleProductDailyPreset = ({ triggerQuery = true, source = 'preset:product' } = {}) => {
  suppressAutoQuery.value = true
  queryParams.table = 'sales'
  queryParams.dimension = 'product'
  queryParams.granularity = 'day'
  nextTick(() => {
    suppressAutoQuery.value = false
    if (triggerQuery) {
      scheduleAutoQuery({ resetPage: true, source })
    }
  })
}

const handleRoomDailyPreset = ({ triggerQuery = true, source = 'preset:room' } = {}) => {
  suppressAutoQuery.value = true
  queryParams.table = 'room'
  queryParams.dimension = 'date'
  queryParams.granularity = 'day'
  queryParams.dateRange = getYesterdayDateRange()
  nextTick(() => {
    suppressAutoQuery.value = false
    if (triggerQuery) {
      scheduleAutoQuery({ resetPage: true, source })
    }
  })
}

const applyRoutePresetIfNeeded = () => {
  if (route.query?.preset === 'financial_daily') {
    handleFinancialDailyPreset({ source: 'preset:financial:route' })
    return true
  }
  if (route.query?.preset === 'product_daily') {
    handleProductDailyPreset({ source: 'preset:product:route' })
    return true
  }
  if (route.query?.preset === 'room_daily') {
    handleRoomDailyPreset({ source: 'preset:room:route' })
    return true
  }
  return false
}

onMounted(() => {
  // 初始化移动端检测
  checkMobile()
  
  const savedState = readSessionJSON(generalAnalysisStateKey, null)
  if (savedState?.query) {
    suppressAutoQuery.value = true
    applyViewState(savedState)
    nextTick(() => {
      suppressAutoQuery.value = false
      if (!applyRoutePresetIfNeeded()) {
        scheduleAutoQuery({ resetPage: true, source: 'restore' })
      }
    })
  } else {
    const legacyRange = readSessionJSON(legacyDateRangeStorageKey, null)
    if (isValidDateRange(legacyRange)) {
      queryParams.dateRange = legacyRange
    }
    nextTick(() => {
      applyRoutePresetIfNeeded()
    })
  }
  loadCurrentUser()
  fetchStoreOptions()
  nextTick(() => {
    initChart()
  })
  
  // 监听屏幕方向变化
  window.addEventListener('orientationchange', handleOrientationChange)
})

watch(
  () => [queryParams.table, queryParams.dimension, queryParams.granularity, queryParams.store_id, queryParams.dateRange],
  () => {
    writeSessionJSON(generalAnalysisStateKey, buildViewState())
    // 选项选满自动查询
    scheduleAutoQuery({ resetPage: true, source: 'auto' })
  },
  { deep: true }
)

watch(
  () => selectedMetric.value,
  () => {
    writeSessionJSON(generalAnalysisStateKey, buildViewState())
  }
)

watch(
  () => route.query?.preset,
  (preset, previous) => {
    if (preset === 'financial_daily' && preset !== previous) {
      handleFinancialDailyPreset({ source: 'preset:financial:navigate' })
    } else if (preset === 'product_daily' && preset !== previous) {
      handleProductDailyPreset({ source: 'preset:product:navigate' })
    } else if (preset === 'room_daily' && preset !== previous) {
      handleRoomDailyPreset({ source: 'preset:room:navigate' })
    }
  }
)

onBeforeUnmount(() => {
  cancelActiveQuery()
  if (autoQueryTimer) {
    clearTimeout(autoQueryTimer)
    autoQueryTimer = null
  }
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('orientationchange', handleOrientationChange)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  if (fullscreenChartInstance) {
    fullscreenChartInstance.dispose()
    fullscreenChartInstance = null
  }
  // 确保关闭时恢复滚动
  if (showFullscreenChart.value) {
    document.body.style.overflow = ''
  }
})

</script>

<style lang="scss" scoped>
.general-analysis {
  // 移除 padding，使用 MainLayout 的统一 padding

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

    .toolbar-actions {
      display: flex;
      align-items: flex-end;
      margin-left: auto;

      .el-button {
        align-self: flex-end;
      }
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

      .chart-fullscreen-btn {
        position: absolute;
        right: 12px;
        bottom: 12px;
        z-index: 10;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      }

      .chart-truncate-tip {
        position: absolute;
        left: 12px;
        bottom: 12px;
        z-index: 10;
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

  .percent-text {
    display: inline-block;
    min-width: 70px;
    text-align: right;
  }

  .percent-strong {
    font-weight: 600;
  }

  .percent-text.is-warning {
    color: #f56c6c;
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
    width: 100%;
  }

  // 移动端优化
  @media (max-width: 768px) {
    // 移除 padding，使用 MainLayout 的统一 padding

    .analysis-card {
      :deep(.el-card__body) {
        padding: 15px 12px;
      }
    }

    .query-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;

      .toolbar-item {
        margin-bottom: 0;
        width: calc(50% - 7px); // 两列布局
        min-width: 0; // 允许缩小

        // 使用 order 调整移动端显示顺序
        // 数据源（第1个）：第二行左侧
        &:nth-child(1) {
          order: 2;
        }
        // 时间范围（第2个）：首行，独占一行
        &:nth-child(2) {
          order: 1;
          width: 100%;
        }
        // 门店（第3个）：第二行右侧
        &:nth-child(3) {
          order: 3;
        }
        // 分析维度（第4个）：第三行左侧
        &:nth-child(4) {
          order: 4;
        }
        // 时间粒度（第5个）：第三行右侧
        &:nth-child(5) {
          order: 5;
        }

        .toolbar-label {
          font-size: 12px;
          margin-bottom: 6px;
        }

        :deep(.el-select),
        :deep(.el-input) {
          width: 100% !important;
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
      }
    }

    .result-table {
      :deep(.el-table__empty-text) {
        width: 100%;
        line-height: 20px; // 优化多行文本显示
        white-space: normal; // 允许换行
        padding: 0 20px;
      }

      :deep(.percent-text) {
        min-width: 50px;
      }
    }

    .filter-section {
      :deep(.el-form) {
        .el-form-item {
          margin-right: 0;
          margin-bottom: 12px;
          width: 100%;
          
          .el-form-item__content {
            .el-date-editor,
            .el-select {
              width: 100% !important;
            }

            .el-button {
              width: 100%;
              margin-top: 8px;
            }
          }
        }
      }
    }

    .result-section {
      :deep(.el-table) {
        font-size: 12px;

        .el-table__header th,
        .el-table__body td {
          padding: 8px 5px;
        }
      }
    }

    .table-pagination {
      justify-content: center !important;
      margin-top: 10px;
      overflow-x: auto; // 允许横向滚动作为后备方案
      -webkit-overflow-scrolling: touch;

      :deep(.el-pagination) {
        flex-wrap: wrap; // 允许换行
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

        // 每页条数选择器优化
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

        // 跳转输入框优化
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
    .filter-section {
      :deep(.el-card__body) {
        padding: 12px;
      }
    }

    .result-section {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 12px;
      }

      .card-header {
        h2 {
          font-size: 16px;
        }

        .card-subtitle {
          font-size: 12px;
        }
      }

      :deep(.el-table) {
        font-size: 11px;

        .el-table__header th,
        .el-table__body td {
          padding: 6px 3px;
        }

        .percent-text {
          min-width: 40px;
        }
      }

      .table-pagination {
        margin-top: 8px;

        :deep(.el-pagination) {
          font-size: 11px;
          gap: 4px; // 元素间距更小

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
    }
  }

}

// 全屏图表弹窗样式（独立于 .general-analysis）
// 使用 CSS transform 强制横屏显示
.fullscreen-chart-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background-color: #000;

  // 旋转容器 - 在竖屏时强制横屏显示
  .fullscreen-chart-rotated {
    position: absolute;
    background-color: #fff;
    
    // 默认（竖屏时）：旋转90度显示为横屏
    @media screen and (orientation: portrait) {
      // 旋转后宽高互换
      width: 100vh;
      height: 100vw;
      // 先移动到中心，再旋转
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%) rotate(90deg);
      transform-origin: center center;
    }

    // 横屏时：正常显示，不旋转
    @media screen and (orientation: landscape) {
      width: 100%;
      height: 100%;
      top: 0;
      left: 0;
      transform: none;
    }
  }

  .fullscreen-chart-container {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .fullscreen-chart-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      border-bottom: 1px solid #ebeef5;
      flex-shrink: 0;
      background-color: #fff;

      .fullscreen-chart-title {
        font-size: 14px;
        font-weight: 600;
        color: #303133;
        // 防止标题过长
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: calc(100% - 50px);
      }
    }

    .fullscreen-chart-body {
      flex: 1;
      width: 100%;
      min-height: 0;
      padding: 8px 12px 12px;
      background-color: #fff;
    }
  }
}
</style>

