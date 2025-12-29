<template>
  <div class="room-analysis">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="header-title">🎤 包厢效能分析</span>
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
              @change="handleDateChange"
            />
          </div>
        </div>
      </template>

      <el-row :gutter="20" class="summary-cards">
        <el-col
          v-for="card in summaryCards"
          :key="card.key"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
          :xl="4"
        >
          <div class="summary-item">
            <div class="label">
              <span>{{ card.label }}</span>
              <el-tooltip
                v-if="card.tooltip"
                :content="card.tooltip"
                placement="top"
                effect="dark"
              >
                <el-icon class="label-icon">
                  <QuestionFilled />
                </el-icon>
              </el-tooltip>
            </div>
            <div class="value">{{ card.display }}</div>
            <div v-if="card.helper" class="helper-text">{{ card.helper }}</div>
          </div>
        </el-col>
      </el-row>

      <div class="time-slot-container">
        <div class="time-slot-header">
          <div>
            <p class="time-slot-title">24 小时开台负荷分析</p>
            <p class="time-slot-subtitle">按小时洞察不同场次的开台峰谷与利用率</p>
          </div>
          <el-tag effect="plain" size="small" type="info">
            {{ activeRoomCountText }}
          </el-tag>
        </div>
        <div class="time-slot-chart-wrapper" v-loading="chartLoading">
          <div ref="timeSlotChartRef" class="time-slot-chart"></div>
          <div v-if="!hasTimeSlotData && !chartLoading" class="chart-empty">
            暂无时段数据，请调整时间或门店筛选条件
          </div>
        </div>
      </div>

      <el-table
        ref="tableRef"
        :data="roomData"
        stripe
        border
        class="room-table"
        v-loading="loading"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="room_name" label="包厢名称" min-width="150" />
        <el-table-column
          v-if="currentStore === 'all'"
          prop="store_name"
          label="所属门店"
          min-width="120"
        />
        <el-table-column
          prop="order_count"
          label="开台次数"
          min-width="100"
          align="right"
          sortable="custom"
        />
        <el-table-column
          prop="gmv"
          label="GMV（应收）"
          min-width="130"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatCurrencyValue(row.gmv, 0) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="bill_total"
          label="账单合计"
          min-width="130"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatCurrencyValue(row.bill_total, 0) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="actual"
          label="实收金额"
          min-width="130"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatCurrencyValue(row.actual, 0) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="min_consumption"
          label="最低消费"
          min-width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ row.min_consumption ? formatCurrencyValue(row.min_consumption, 0) : '--' }}
          </template>
        </el-table-column>
        <el-table-column
          prop="low_consume_diff"
          label="低消差额"
          min-width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatCurrencyValue(row.low_consume_diff, 0) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="low_consume_rate"
          label="低消达成率"
          min-width="130"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            <span class="percent-text">
              {{ row.low_consume_rate !== null ? formatPercentValue(row.low_consume_rate, 1) : '--' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column
          prop="room_discount"
          label="包厢折扣"
          min-width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatCurrencyValue(row.room_discount) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="beverage_discount"
          label="酒水折扣"
          min-width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatCurrencyValue(row.beverage_discount) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="gift_amount"
          label="赠送金额"
          min-width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            {{ formatCurrencyValue(row.gift_amount) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="gift_ratio"
          label="赠送比例"
          min-width="120"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            <span
              class="percent-text"
              :class="{ 'is-warning': row.gift_ratio_warn }"
            >
              {{ row.gift_ratio !== null ? formatPercentValue(row.gift_ratio, 1) : '--' }}
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

      <div v-if="!roomData.length && !loading" class="empty-hint">
        暂无数据，请先上传包厢消费数据
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, inject, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { queryStats, getDateRange } from '@/api/stats'
import { useChart, chartColors } from '@/components/charts/useChart'
import { usePagination } from '@/composables/usePagination'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'

const formatCurrencyValue = (value, digits = 2) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '--'
  }
  return `¥${numeric.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`
}

const formatPercentValue = (value, digits = 1) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return '--'
  }
  return `${(numeric * 100).toFixed(digits)}%`
}

const formatDurationValue = (minutes) => {
  const numeric = Number(minutes)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return '--'
  }
  const hours = Math.floor(numeric / 60)
  const mins = Math.round(numeric % 60)
  if (hours === 0) {
    return `${mins} 分钟`
  }
  if (mins === 0) {
    return `${hours} 小时`
  }
  return `${hours} 小时 ${mins} 分`
}

const toNumber = (value) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const extractActiveRoomCount = (meta = {}, summary = {}) => {
  const keys = ['active_room_count', 'room_count', 'total_rooms']
  for (const key of keys) {
    const candidate = meta?.[key] ?? summary?.[key]
    const numeric = Number(candidate)
    if (Number.isFinite(numeric) && numeric > 0) {
      return numeric
    }
  }
  const fallback = Number(meta?.count)
  if (Number.isFinite(fallback) && fallback > 0) {
    return fallback
  }
  return 0
}

const resolveHourFromKey = (key) => {
  if (key === null || key === undefined || String(key).toLowerCase() === 'null' || String(key).trim() === '') {
    return null
  }
  if (typeof key === 'number' && key >= 0) return key
  const match = String(key).match(/(\d{1,2})/)
  if (!match) return null
  const hour = Number(match[1])
  if (!Number.isFinite(hour) || hour < 0 || hour > 23) return null
  return hour
}

const getBusinessSlotLabel = (hour) => {
  if (hour >= 18) return '晚场'
  if (hour >= 12) return '下午场'
  if (hour >= 6) return '上午场'
  return '凌晨场'
}

const getDateRangeDaySpan = (range) => {
  if (!Array.isArray(range) || range.length < 2) {
    return 1
  }
  const [start, end] = range
  if (!start || !end) return 1
  const startDate = new Date(`${start}T00:00:00`)
  const endDate = new Date(`${end}T00:00:00`)
  if (!(startDate instanceof Date) || Number.isNaN(startDate.getTime())) {
    return 1
  }
  if (!(endDate instanceof Date) || Number.isNaN(endDate.getTime())) {
    return 1
  }
  const diffDays = Math.floor((endDate - startDate) / (24 * 60 * 60 * 1000))
  return Math.max(diffDays + 1, 1)
}

const buildTimeSlotDataset = (rows, activeRooms, range) => {
  const hours = Array.from({ length: 24 }, (_, index) => index)
  const hourMap = new Map()

  rows.forEach((row) => {
    const hour = resolveHourFromKey(row.dimension_key)
    if (hour === null) return
    const bucket = hourMap.get(hour) || { orders: 0, gmv: 0, occupiedMinutes: 0 }
    bucket.orders += toNumber(row.orders ?? row.order_count ?? 0)
    bucket.gmv += toNumber(row.gmv ?? row.bill_total ?? row.actual ?? 0)
    bucket.occupiedMinutes += toNumber(row.occupied_minutes ?? row.duration ?? row.duration_min ?? 0)
    hourMap.set(hour, bucket)
  })

  const labels = hours.map((hour) => `${String(hour).padStart(2, '0')}:00`)
  const orders = hours.map((hour) => hourMap.get(hour)?.orders || 0)
  const gmv = hours.map((hour) => hourMap.get(hour)?.gmv || 0)
  const occupiedMinutes = hours.map((hour) => hourMap.get(hour)?.occupiedMinutes || 0)
  const daySpan = Math.max(getDateRangeDaySpan(range), 1)
  const normalizedRoomCount = Math.max(activeRooms, 0)
  const scenes = hours.map((hour) => getBusinessSlotLabel(hour))

  const roomFactor = normalizedRoomCount > 0 ? normalizedRoomCount : 0
  const utilizationRatio = occupiedMinutes.map((minutes) => {
    if (!roomFactor) return 0
    const ratio = minutes / (daySpan * roomFactor * 60)
    return Number(Math.max(ratio, 0).toFixed(4))
  })
  const utilizationPercent = utilizationRatio.map((ratio) =>
    Number((ratio * 100).toFixed(1))
  )

  return { labels, orders, gmv, occupiedMinutes, scenes, utilizationRatio, utilizationPercent }
}

const buildTimeSlotChartOption = (dataset) => {
  if (!dataset) return null
  const maxUtilPercent = Math.max(...dataset.utilizationPercent, 0)
  const yAxisMax =
    maxUtilPercent > 0 ? Math.min(Math.max(maxUtilPercent * 1.2, 40), 150) : 40
  return {
    color: [chartColors.primary],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        if (!params?.length) return ''
        const index = params[0].dataIndex
        const hourLabel = dataset.labels[index]
        const scene = dataset.scenes[index]
        const orders = dataset.orders[index]
        const gmv = dataset.gmv[index]
        const occupiedMinutes = dataset.occupiedMinutes?.[index] ?? 0
        const utilizationRatio = dataset.utilizationRatio[index] || 0
        return [
          `<strong>${hourLabel} (${scene})</strong>`,
          `开台数：${orders.toLocaleString('zh-CN')} 单`,
          `GMV：${formatCurrencyValue(gmv, 0)}`,
          `占用时长：${formatDurationValue(occupiedMinutes)}`,
          `时段利用率：${formatPercentValue(utilizationRatio, 1)}`,
        ].join('<br/>')
      },
    },
    grid: {
      top: 40,
      left: 50,
      right: 30,
      bottom: 50,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: dataset.labels,
      axisLabel: {
        color: '#606266',
        formatter: (value, idx) => `${value}\n${dataset.scenes[idx]}`,
      },
      axisLine: { lineStyle: { color: '#E0E6ED' } },
    },
    yAxis: {
      type: 'value',
      name: '时段利用率 (%)',
      min: 0,
      max: yAxisMax,
      axisLabel: {
        color: '#909399',
        formatter: (val) => `${Number(val).toFixed(0)}%`,
      },
      splitLine: { lineStyle: { color: '#F2F3F5' } },
    },
    visualMap: {
      show: false,
      min: 0,
      max: Math.max(maxUtilPercent, 20),
      inRange: {
        color: ['#dbeafe', '#60a5fa', '#1d4ed8'],
      },
      seriesIndex: 0,
    },
    series: [
      {
        name: '时段利用率',
        type: 'bar',
        barWidth: '55%',
        data: dataset.utilizationPercent,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
}

const computeSummaryMetrics = (summaryData, summaryRows, tableRows) => {
  const pickValue = (key) => {
    if (summaryData && summaryData[key] !== undefined) {
      return toNumber(summaryData[key])
    }
    if (summaryRows?.length) {
      return summaryRows.reduce((sum, item) => sum + toNumber(item[key]), 0)
    }
    return tableRows.reduce((sum, item) => sum + toNumber(item[key]), 0)
  }

  const totalOrders = pickValue('orders')
  const totalGmv = pickValue('gmv')
  const totalActual = pickValue('actual')
  const totalDuration = pickValue('duration')
  const avgActual = totalOrders > 0 ? totalActual / totalOrders : 0
  const avgDurationMinutes = totalOrders > 0 ? totalDuration / totalOrders : 0

  return {
    totalOrders,
    totalGmv,
    totalActual,
    avgActual,
    avgDurationMinutes,
  }
}

const buildSummaryCards = (metrics, activeRooms) => {
  const turnoverRate =
    activeRooms > 0 && metrics.totalOrders > 0
      ? metrics.totalOrders / activeRooms
      : null
  return [
    {
      key: 'totalOrders',
      label: '总开台数',
      display: metrics.totalOrders
        ? metrics.totalOrders.toLocaleString('zh-CN')
        : '--',
      tooltip: '统计周期内所有包厢的开台次数',
    },
    {
      key: 'totalGmv',
      label: '总GMV',
      display: formatCurrencyValue(metrics.totalGmv, 0),
      tooltip: '账单合计（应收金额）总和',
    },
    {
      key: 'totalActual',
      label: '总实收',
      display: formatCurrencyValue(metrics.totalActual, 0),
      tooltip: '实收金额（扣除折扣与赠送后）总和',
    },
    {
      key: 'avgActual',
      label: '平均实收',
      display: formatCurrencyValue(metrics.avgActual, 2),
      tooltip: '平均每单实收 = 总实收 / 总开台数',
    },
    {
      key: 'turnoverRate',
      label: '平均翻台率',
      display: turnoverRate !== null ? formatPercentValue(turnoverRate, 1) : '--',
      tooltip:
        activeRooms > 0
          ? `= 总开台数 (${metrics.totalOrders}) ÷ 活跃包厢数 (${activeRooms} 间)`
          : '由于未关联到包厢基础信息，无法获取活跃包厢总数，暂无法计算翻台率',
      helper: activeRooms > 0 ? `活跃包厢：${activeRooms} 间` : '缺少包厢档案数据',
    },
    {
      key: 'avgDuration',
      label: '平均消费时长',
      display: formatDurationValue(metrics.avgDurationMinutes),
      tooltip: '将总时长（分钟）转换为小时 + 分钟形式展示',
      helper:
        metrics.avgDurationMinutes > 0
          ? `≈ ${metrics.avgDurationMinutes.toFixed(1)} 分钟/单`
          : '',
    },
  ]
}

const formatRatio = (numerator, denominator) => {
  if (!denominator) return null
  const ratio = numerator / denominator
  return Number.isFinite(ratio) ? Number(ratio.toFixed(4)) : null
}

const transformRoomRows = (rows) =>
  rows.map((item) => {
    const gmv = toNumber(item.gmv ?? item.bill_total)
    const billTotal = toNumber(item.bill_total ?? item.gmv)
    const minConsumption = toNumber(item.min_consumption)
    const minDiff = toNumber(item.min_consumption_diff)
    const giftAmount = toNumber(item.gift_amount)
    // 优先使用后端返回的字段，如果没有则前端计算（兼容旧数据）
    const giftRatio = item.gift_ratio !== undefined ? toNumber(item.gift_ratio) : formatRatio(giftAmount, billTotal)
    const lowConsumeRate = item.low_consume_rate !== undefined ? toNumber(item.low_consume_rate) : formatRatio(billTotal, minConsumption)
    return {
      room_name: item.dimension_label || '未知包厢',
      store_name: item.store_name || '--',
      order_count: toNumber(item.orders ?? item.order_count),
      gmv,
      bill_total: billTotal,
      actual: toNumber(item.actual),
      min_consumption: minConsumption || null,
      low_consume_diff: minDiff,
      low_consume_rate: lowConsumeRate,
      room_discount: toNumber(item.room_discount),
      beverage_discount: toNumber(item.beverage_discount),
      gift_amount: giftAmount,
      gift_ratio: giftRatio,
      gift_ratio_warn: Number.isFinite(giftRatio) && giftRatio > 0.2,
    }
  })

const dateRangeStorageKey = 'viewState:RoomAnalysis:dateRange'
const currentStore = inject('currentStore', ref('all'))

function useRoomAnalysis(storeRef) {
  const loading = ref(false)
  const chartLoading = ref(false)
  const dateRange = ref([])
  const tableRef = ref(null)
  const pagination = reactive({ page: 1, pageSize: 20 })
  const sortState = reactive({ prop: null, order: null })
  
  // 前端字段名到后端字段名的映射
  const SORT_FIELD_MAP = {
    order_count: 'orders',
    low_consume_diff: 'min_consumption_diff',
    low_consume_rate: 'low_consume_rate',
    gift_ratio: 'gift_ratio'
  }
  const tableRows = ref([])
  const summaryRows = ref([])
  const summaryData = ref(null)
  const total = ref(0)
  const timeSlotRows = ref([])
  const activeRoomCount = ref(0)

  const { pageSizeOptions, paginationLayout, pagerCount } = usePagination({
    desktopPageSizes: [20, 50, 100],
    mobilePageSizes: [20, 50],
  })

  const timeSlotChartRef = ref(null)
  const timeSlotChartData = computed(() =>
    buildTimeSlotDataset(timeSlotRows.value, activeRoomCount.value, dateRange.value)
  )
  const { updateChart: updateTimeSlotChart } = useChart(
    timeSlotChartRef,
    () => buildTimeSlotChartOption(timeSlotChartData.value)
  )
  watch(
    timeSlotChartData,
    (data) => {
      const option = buildTimeSlotChartOption(data)
      if (option) {
        updateTimeSlotChart(option, true)
      }
    },
    { deep: true }
  )

  const summaryMetrics = computed(() =>
    computeSummaryMetrics(summaryData.value, summaryRows.value, tableRows.value)
  )
  const summaryCards = computed(() =>
    buildSummaryCards(summaryMetrics.value, activeRoomCount.value)
  )
  const roomData = computed(() => transformRoomRows(tableRows.value))
  const hasTimeSlotData = computed(() =>
    timeSlotChartData.value.orders.some((value) => value > 0)
  )
  const activeRoomCountText = computed(() =>
    activeRoomCount.value > 0
      ? `活跃包厢 ${activeRoomCount.value} 间`
      : '活跃包厢数待确认'
  )

  const resolveStoreId = () => {
    if (!storeRef.value || storeRef.value === 'all') {
      return null
    }
    const parsed = Number(storeRef.value)
    return Number.isFinite(parsed) ? parsed : null
  }

  const fetchRoomTable = async (showLoading = true) => {
    if (!isValidDateRange(dateRange.value)) {
      return
    }
    if (showLoading) {
      loading.value = true
    }
    try {
      const [startDate, endDate] = dateRange.value
      // 将前端字段名映射到后端字段名
      const backendSortField = sortState.prop ? (SORT_FIELD_MAP[sortState.prop] || sortState.prop) : undefined
      
      const params = {
        table: 'room',
        start_date: startDate,
        end_date: endDate,
        dimension: 'room',
        granularity: 'day',
        page: pagination.page,
        page_size: pagination.pageSize,
        sort_by: backendSortField,
        sort_order: sortState.order === 'ascending' ? 'asc' : sortState.order === 'descending' ? 'desc' : undefined,
      }
      const storeId = resolveStoreId()
      if (storeId) {
        params.store_id = storeId
      }
      // 过滤掉 undefined 值
      const filteredParams = Object.fromEntries(
        Object.entries(params).filter(([, value]) => value !== undefined)
      )
      const response = await queryStats(filteredParams)
      if (response.success && response.data) {
        const { rows, series_rows, summary, total: totalCount, meta } = response.data
        tableRows.value = Array.isArray(rows) ? rows : []
        summaryRows.value = Array.isArray(series_rows) ? series_rows : []
        summaryData.value = summary || null
        const parsedTotal = Number(totalCount)
        total.value = Number.isFinite(parsedTotal)
          ? parsedTotal
          : tableRows.value.length
        activeRoomCount.value = extractActiveRoomCount(meta || {}, summary || {})
      } else {
        tableRows.value = []
        summaryRows.value = []
        summaryData.value = null
        total.value = 0
        activeRoomCount.value = 0
      }
    } catch (error) {
      console.error('获取包厢分析数据失败:', error)
      ElMessage.error('获取包厢分析数据失败')
      tableRows.value = []
      summaryRows.value = []
      summaryData.value = null
      total.value = 0
      activeRoomCount.value = 0
    } finally {
      if (showLoading) {
        loading.value = false
      }
    }
  }

  const fetchTimeSlotSeries = async () => {
    if (!isValidDateRange(dateRange.value)) {
      timeSlotRows.value = []
      return
    }
    chartLoading.value = true
    try {
      const [startDate, endDate] = dateRange.value
      const params = {
        table: 'room',
        start_date: startDate,
        end_date: endDate,
        dimension: 'hour',
        granularity: 'day',
        page: 1,
        page_size: 48,
        top_n: 48,
      }
      const storeId = resolveStoreId()
      if (storeId) {
        params.store_id = storeId
      }
      const response = await queryStats(params)
      if (response.success && response.data) {
        const rows =
          (Array.isArray(response.data.rows) && response.data.rows.length
            ? response.data.rows
            : null) ??
          (Array.isArray(response.data.series_rows)
            ? response.data.series_rows
            : [])
        timeSlotRows.value = rows || []
      } else {
        timeSlotRows.value = []
      }
    } catch (error) {
      console.error('获取开台时段数据失败:', error)
      ElMessage.error('获取开台时段数据失败')
      timeSlotRows.value = []
    } finally {
      chartLoading.value = false
    }
  }

  const fetchData = async () => {
    await Promise.all([fetchRoomTable(true), fetchTimeSlotSeries()])
  }

  const scrollTableToTop = () => {
    nextTick(() => {
      if (tableRef.value?.setScrollTop) {
        tableRef.value.setScrollTop(0)
      }
    })
  }

  const handlePageChange = async (page) => {
    pagination.page = page
    await fetchRoomTable(true)
    scrollTableToTop()
  }

  const handlePageSizeChange = async (size) => {
    pagination.pageSize = size
    pagination.page = 1
    await fetchRoomTable(true)
    scrollTableToTop()
  }

  const handleSortChange = async ({ prop, order }) => {
    // 更新排序状态
    sortState.prop = prop || null
    sortState.order = order || null
    // 排序变化时重置到第一页
    pagination.page = 1
    await fetchRoomTable(true)
    // 注意：排序时不需要滚动表格，保持用户当前查看位置
  }

  const handleDateChange = () => {
    pagination.page = 1
    if (isValidDateRange(dateRange.value)) {
      writeSessionJSON(dateRangeStorageKey, dateRange.value)
      fetchData()
    }
  }

  const initDateRange = async () => {
    try {
      const rangeRes = await getDateRange('room')
      if (rangeRes.success && rangeRes.suggested_start && rangeRes.suggested_end) {
        dateRange.value = [rangeRes.suggested_start, rangeRes.suggested_end]
      } else {
        const today = new Date()
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
        dateRange.value = [
          firstDay.toISOString().split('T')[0],
          today.toISOString().split('T')[0],
        ]
      }
    } catch (error) {
      console.error('获取日期范围失败:', error)
      const today = new Date()
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
      dateRange.value = [
        firstDay.toISOString().split('T')[0],
        today.toISOString().split('T')[0],
      ]
    }
  }

  watch(storeRef, () => {
    pagination.page = 1
    fetchData()
  })

  onMounted(async () => {
    const saved = readSessionJSON(dateRangeStorageKey, null)
    if (isValidDateRange(saved)) {
      dateRange.value = saved
    } else {
      await initDateRange()
      if (isValidDateRange(dateRange.value)) {
        writeSessionJSON(dateRangeStorageKey, dateRange.value)
      }
    }
    if (isValidDateRange(dateRange.value)) {
      await fetchData()
    }
  })

  return {
    loading,
    chartLoading,
    dateRange,
    tableRef,
    pagination,
    pageSizeOptions,
    paginationLayout,
    pagerCount,
    total,
    summaryCards,
    roomData,
    hasTimeSlotData,
    activeRoomCountText,
    timeSlotChartRef,
    handlePageChange,
    handlePageSizeChange,
    handleSortChange,
    handleDateChange,
  }
}

const {
  loading,
  chartLoading,
  dateRange,
  tableRef,
  pagination,
  pageSizeOptions,
  paginationLayout,
  pagerCount,
  total,
  summaryCards,
  roomData,
  hasTimeSlotData,
  activeRoomCountText,
  timeSlotChartRef,
  handlePageChange,
  handlePageSizeChange,
  handleSortChange,
  handleDateChange,
} = useRoomAnalysis(currentStore)
</script>

<style lang="scss" scoped>
.room-analysis {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

  .summary-cards {
    margin-bottom: 16px;

    :deep(.el-col) {
      margin-bottom: 16px;
    }

    .summary-item {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 8px;
      padding: 18px;
      color: #fff;
      min-height: 110px;

      .label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        opacity: 0.85;
        margin-bottom: 8px;
      }

      .label-icon {
        font-size: 16px;
        cursor: pointer;
      }

      .value {
        font-size: 24px;
        font-weight: 600;
      }

      .helper-text {
        margin-top: 6px;
        font-size: 12px;
        opacity: 0.85;
      }
    }
  }

  .time-slot-container {
    border: 1px solid #ebeef5;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;
    background: #f9fafb;

    .time-slot-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;

      .time-slot-title {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }

      .time-slot-subtitle {
        margin: 4px 0 0;
        font-size: 13px;
        color: #909399;
      }
    }

    .time-slot-chart-wrapper {
      position: relative;
      margin-top: 12px;
      min-height: 320px;
    }

    .time-slot-chart {
      width: 100%;
      height: 320px;
    }

    .chart-empty {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      color: #909399;
    }
  }

  .room-table {
    margin-top: 12px;
  }

  .percent-text {
    display: inline-block;
    min-width: 70px;
    text-align: right;
  }

  .percent-text.is-warning {
    color: #f56c6c;
    font-weight: 600;
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }

  .empty-hint {
    text-align: center;
    padding: 40px 0;
    color: #999;
  }

  @media (max-width: 768px) {
    .card-header {
      flex-direction: column;
      align-items: flex-start;
    }

    .header-right {
      width: 100%;
      flex-direction: column;
      align-items: flex-start;
    }

    .date-range {
      width: 100%;
    }

    :deep(.el-date-editor--daterange) {
      width: 100%;
    }

    .time-slot-chart {
      height: 260px;
    }

    .percent-text {
      min-width: 50px;
    }

    .table-pagination {
      justify-content: center;
    }
  }
}
</style>