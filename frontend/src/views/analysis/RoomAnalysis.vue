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
              :editable="false"
              @change="handleDateChange"
            />
          </div>
        </div>
      </template>

      <el-row :gutter="24" class="summary-cards">
        <el-col
          v-for="card in summaryCards"
          :key="card.key"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
          :xl="4"
        >
          <div class="summary-card-wrapper">
            <div class="summary-card" :class="`summary-card--${card.type}`">
              <div class="summary-card__icon">
                <el-icon :size="24">
                  <component :is="card.icon" />
                </el-icon>
              </div>
              <div class="summary-card__content">
                <div class="summary-card__label">
                  <span>{{ card.label }}</span>
                  <el-tooltip
                    v-if="card.tooltip"
                    :content="card.tooltip"
                    placement="top"
                    effect="dark"
                  >
                    <el-icon class="summary-card__help">
                      <QuestionFilled />
                    </el-icon>
                  </el-tooltip>
                </div>
                <div class="summary-card__value">{{ card.display }}</div>
                <div v-if="card.helper" class="summary-card__helper">{{ card.helper }}</div>
              </div>
            </div>
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
          <div class="chart-scroll-wrapper" ref="timeSlotChartWrapperRef">
            <div ref="timeSlotChartRef" class="time-slot-chart"></div>
          </div>
          <div v-if="!hasTimeSlotData && !chartLoading" class="chart-empty">
            <el-empty
              description="暂无时段数据"
              :image-size="80"
            >
              <template #description>
                <p class="empty-description">
                  暂无时段数据，请调整时间或门店筛选条件
                </p>
              </template>
            </el-empty>
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
        <el-table-column prop="room_name" label="包厢名称" min-width="150" fixed="left" />
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
            <span class="table-value--emphasis">
              {{ formatCurrencyValue(row.actual, 0) }}
            </span>
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
          min-width="130"
          align="right"
          sortable="custom"
        >
          <template #header>
            <span>低消达成率</span>
            <el-tooltip
              content="低消达成率 = 账单合计 ÷ 最低消费。先计算每次开台的达成率，再取平均值。≥90%为优秀（绿色），70-90%为良好（橙色），<70%需关注（红色）"
              placement="top"
              effect="dark"
            >
              <el-icon class="table-header-help">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span 
              class="percent-text"
              :class="{
                'percent-text--success': row.low_consume_rate_type === 'success',
                'percent-text--warning': row.low_consume_rate_type === 'warning',
                'percent-text--danger': row.low_consume_rate_type === 'danger'
              }"
            >
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
          min-width="120"
          align="right"
          sortable="custom"
        >
          <template #header>
            <span>赠送比例</span>
            <el-tooltip
              content="赠送比例 = 赠送金额 ÷ 账单合计 × 100%。>20%时显示红色警告，表示赠送比例过高"
              placement="top"
              effect="dark"
            >
              <el-icon class="table-header-help">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span
              class="percent-text"
              :class="{ 'percent-text--danger': row.gift_ratio_warn }"
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
        <el-empty
          description="暂无数据"
          :image-size="100"
        >
          <template #description>
            <p class="empty-description">
              暂无数据，请先上传包厢消费数据
            </p>
          </template>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, inject, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  QuestionFilled,
  Document,
  Money,
  Wallet,
  TrendCharts,
  Refresh,
  Timer
} from '@element-plus/icons-vue'
import { queryStats, getDateRange } from '@/api/stats'
import { useChart } from '@/components/charts/useChart'
import { usePagination } from '@/composables/usePagination'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'
import { chartColors as designChartColors, spacing } from '@/utils/designTokens'
import * as echarts from 'echarts'

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

const buildTimeSlotChartOption = (dataset, mobile = false) => {
  if (!dataset) return null
  
  // 使用设计系统的颜色值（与 SCSS 变量保持一致）
  const CHART_COLORS = designChartColors
  
  const maxUtilPercent = Math.max(...dataset.utilizationPercent, 0)
  const yAxisMax =
    maxUtilPercent > 0 ? Math.min(Math.max(maxUtilPercent * 1.2, 40), 150) : 40
  
  // 计算平均值和峰值（用于标注和对比）
  const avgUtilization = dataset.utilizationPercent.length > 0
    ? dataset.utilizationPercent.reduce((a, b) => a + b, 0) / dataset.utilizationPercent.length
    : 0
  const maxUtilization = maxUtilPercent
  
  // 创建柱状图渐变色
  const barGradient = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: CHART_COLORS.primary },
    { offset: 1, color: CHART_COLORS.primaryLight }
  ])
  
  // 移动端配置调整（增加顶部空间以显示峰值标注，增加右侧空间以显示平均值标签）
  // 桌面端也需要足够的右侧空间显示"平均值"标签
  const gridConfig = mobile
    ? { top: 50, left: 40, right: 100, bottom: 60, containLabel: true }
    : { top: 50, left: 50, right: 100, bottom: 50, containLabel: true }
  
  // 优化横坐标显示格式：移动端简化显示
  const xAxisLabelFormatter = mobile
    ? (value, idx) => {
        // 移动端只显示小时，不显示场次，节省空间
        return value
      }
    : (value, idx) => `${value}\n${dataset.scenes[idx]}`
  
  // 优化 Y 轴显示格式：去掉多余的"0"
  const yAxisLabelFormatter = (val) => {
    const num = Number(val)
    if (!Number.isFinite(num)) return '0%'
    // 如果是整数，不显示小数
    return num % 1 === 0 ? `${num}%` : `${num.toFixed(1)}%`
  }
  
  return {
    color: [CHART_COLORS.primary],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: CHART_COLORS.bgPrimary,
      borderColor: CHART_COLORS.borderLight,
      borderWidth: 1,
      borderRadius: 8,
      padding: spacing.md,
      textStyle: {
        color: CHART_COLORS.textPrimary,
        fontSize: 13,
      },
      formatter: (params) => {
        if (!params?.length) return ''
        const index = params[0].dataIndex
        const hourLabel = dataset.labels[index]
        const scene = dataset.scenes[index]
        const orders = dataset.orders[index]
        const utilizationPercent = dataset.utilizationPercent[index] || 0
        
        // 计算与平均值的差值
        const diff = utilizationPercent - avgUtilization
        const diffText = diff !== 0
          ? diff > 0
            ? `<span style="color: ${CHART_COLORS.success};">+${diff.toFixed(1)}%</span>`
            : `<span style="color: ${CHART_COLORS.danger};">${diff.toFixed(1)}%</span>`
          : ''
        
        return [
          `<div style="font-weight: 600; margin-bottom: ${spacing.sm}px; color: ${CHART_COLORS.textPrimary};">${hourLabel} · ${scene}</div>`,
          `<div style="margin: ${spacing.xs}px 0; color: ${CHART_COLORS.textRegular};">开台数：<strong>${orders.toLocaleString('zh-CN')}</strong> 单</div>`,
          `<div style="margin: ${spacing.xs}px 0; color: ${CHART_COLORS.textRegular};">时段利用率：<strong style="color: ${CHART_COLORS.primary};">${utilizationPercent.toFixed(1)}%</strong>${diffText ? ` (${diffText})` : ''}</div>`,
        ].join('')
      },
    },
    grid: gridConfig,
    xAxis: {
      type: 'category',
      data: dataset.labels,
      axisLabel: {
        color: CHART_COLORS.textRegular,
        formatter: xAxisLabelFormatter,
        fontSize: mobile ? 10 : undefined,
        interval: 0
      },
      axisLine: { lineStyle: { color: CHART_COLORS.borderBase } },
    },
    yAxis: {
      type: 'value',
      name: '时段利用率 (%)',
      min: 0,
      max: yAxisMax,
      axisLabel: {
        color: CHART_COLORS.textSecondary,
        formatter: yAxisLabelFormatter,
        fontSize: mobile ? 10 : undefined
      },
      splitLine: { lineStyle: { color: CHART_COLORS.borderLighter } },
    },
    visualMap: {
      show: false,
      min: 0,
      max: Math.max(maxUtilPercent, 20),
      inRange: {
        color: [
          CHART_COLORS.primaryLight10,
          CHART_COLORS.primaryLight40,
          CHART_COLORS.primary
        ],
      },
      seriesIndex: 0,
    },
    series: [
      {
        name: '时段利用率',
        type: 'bar',
        barWidth: '55%',
        data: dataset.utilizationPercent,
        itemStyle: { 
          color: barGradient,
          borderRadius: [4, 4, 0, 0] 
        },
        markPoint: {
          data: [
            {
              type: 'max',
              name: '峰值',
              itemStyle: {
                color: CHART_COLORS.primary,
                borderColor: CHART_COLORS.bgPrimary,
                borderWidth: 1.5,
                shadowBlur: 3,
                shadowColor: CHART_COLORS.shadowColor,
              },
              label: {
                show: false,
              },
              symbol: 'pin',
              symbolSize: mobile ? 40 : 45,
              symbolOffset: [0, -5],
            },
          ],
        },
        markLine: {
          data: [
            {
              type: 'average',
              name: '平均值',
              lineStyle: {
                type: 'dashed',
                color: CHART_COLORS.textSecondary,
                width: 2,
              },
              label: {
                formatter: `平均值: ${avgUtilization.toFixed(1)}%`,
                position: 'end',
                color: CHART_COLORS.textSecondary,
                fontSize: 12,
              },
            },
          ],
        },
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
      type: 'primary',
      icon: Document,
    },
    {
      key: 'totalGmv',
      label: '总GMV',
      display: formatCurrencyValue(metrics.totalGmv, 0),
      tooltip: '账单合计（应收金额）总和',
      type: 'success',
      icon: Money,
    },
    {
      key: 'totalActual',
      label: '总实收',
      display: formatCurrencyValue(metrics.totalActual, 0),
      tooltip: '实收金额（扣除折扣与赠送后）总和',
      type: 'success',
      icon: Wallet,
    },
    {
      key: 'avgActual',
      label: '平均实收',
      display: formatCurrencyValue(metrics.avgActual, 2),
      tooltip: '平均每单实收 = 总实收 / 总开台数',
      type: 'primary',
      icon: TrendCharts,
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
      type: 'warning',
      icon: Refresh,
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
      type: 'primary',
      icon: Timer,
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
    
    // 计算低消达成率颜色类型
    let lowConsumeRateType = null
    if (Number.isFinite(lowConsumeRate)) {
      if (lowConsumeRate >= 0.9) {
        lowConsumeRateType = 'success'  // ≥90%：绿色
      } else if (lowConsumeRate >= 0.7) {
        lowConsumeRateType = 'warning'  // 70-90%：橙色
      } else {
        lowConsumeRateType = 'danger'   // <70%：红色
      }
    }
    
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
      low_consume_rate_type: lowConsumeRateType,
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

  // 移动端检测
  const isMobile = ref(false)
  const checkMobile = () => {
    isMobile.value = window.innerWidth <= 768
  }
  
  const timeSlotChartRef = ref(null)
  const timeSlotChartWrapperRef = ref(null)
  const timeSlotChartData = computed(() =>
    buildTimeSlotDataset(timeSlotRows.value, activeRoomCount.value, dateRange.value)
  )
  const { updateChart: updateTimeSlotChart } = useChart(
    timeSlotChartRef,
    () => buildTimeSlotChartOption(timeSlotChartData.value, isMobile.value)
  )
  // 将图表滚动到合适位置
  // 移动端：滚动到中间位置
  // 桌面端：滚动到右侧，确保能看到"平均值"标签
  const scrollTimeSlotChartToCenter = () => {
    if (timeSlotChartWrapperRef.value) {
      nextTick(() => {
        const wrapper = timeSlotChartWrapperRef.value
        if (wrapper && wrapper.scrollWidth > wrapper.clientWidth) {
          if (isMobile.value) {
            // 移动端：滚动到中间
            const scrollLeft = (wrapper.scrollWidth - wrapper.clientWidth) / 2
            wrapper.scrollLeft = scrollLeft
          } else {
            // 桌面端：滚动到右侧，确保能看到"平均值"标签
            wrapper.scrollLeft = wrapper.scrollWidth - wrapper.clientWidth
          }
        }
      })
    }
  }
  
  watch(
    timeSlotChartData,
    (data) => {
      const option = buildTimeSlotChartOption(data, isMobile.value)
      if (option) {
        updateTimeSlotChart(option, true)
        // 移动端：图表更新后，将滚动位置设置为中间
        scrollTimeSlotChartToCenter()
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

  const handleResize = () => {
    checkMobile()
    // 窗口大小变化后重新调整滚动位置
    scrollTimeSlotChartToCenter()
  }
  
  onMounted(async () => {
    checkMobile()
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
    window.addEventListener('resize', handleResize)
  })
  
  onBeforeUnmount(() => {
    window.removeEventListener('resize', handleResize)
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
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';

.room-analysis {
  padding-top: $spacing-lg; // 添加顶部留白

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: $spacing-md;
    flex-wrap: wrap;
  }

  .header-title {
    font-weight: $font-weight-semibold;
    font-size: $font-size-lg;
    color: $text-primary;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
  }

  .filter-label {
    font-size: $font-size-sm;
    color: $text-regular;
    white-space: nowrap;
    font-weight: $font-weight-normal;
  }

  .date-range {
    // 桌面端宽度：360px（设计规范）
    width: calc($spacing-xxl * 7.5); // 48 * 7.5 = 360px
    max-width: 100%;
  }

  .summary-cards {
    margin-bottom: $spacing-lg;

    // 确保 el-col 使用 flex 布局，使卡片高度一致
    :deep(.el-col) {
      margin-bottom: $spacing-md;
      display: flex;
    }

    // 卡片包装器，确保高度一致
    .summary-card-wrapper {
      display: flex;
      width: 100%;
      height: 100%;
      min-height: calc($spacing-xxl * 2.5); // 48 * 2.5 = 120px
    }

    // 卡片基础样式
    .summary-card {
      display: flex;
      align-items: flex-start;
      background-color: $bg-primary;
      border: 1px solid $border-light;
      border-radius: $border-radius-md;
      box-shadow: $shadow-md;
      padding: $spacing-md;
      width: 100%;
      height: 100%;
      @include transition(box-shadow);

      &:hover {
        box-shadow: $shadow-hover;
      }

      // 图标区域
      &__icon {
        @include flex-center;
        width: $spacing-xxl; // 48px
        height: $spacing-xxl;
        border-radius: 50%;
        flex-shrink: 0;
      }

      // 内容区域
      &__content {
        @include flex-column;
        flex: 1;
        margin-left: $spacing-md;
      }

      // 标签样式
      &__label {
        @include flex-between;
        font-size: $font-size-base;
        color: $text-regular;
        margin-bottom: $spacing-sm;
      }

      // 帮助图标
      &__help {
        font-size: $font-size-lg;
        cursor: pointer;
        color: $text-secondary;
        margin-left: $spacing-xs;
      }

      // 数值样式
      &__value {
        font-size: $font-size-xxxl;
        font-weight: $font-weight-semibold;
        color: $text-primary;
        line-height: $line-height-tight;
      }

      // 辅助文字样式
      &__helper {
        margin-top: $spacing-xs;
        font-size: $font-size-xs;
        color: $text-secondary;
      }

      // 语义化类型样式
      &--primary {
        .summary-card__icon {
          background-color: $brand-primary-light-10;
          color: $brand-primary;
        }
      }

      &--success {
        .summary-card__icon {
          background-color: $brand-success-light-10;
          color: $brand-success;
        }
      }

      &--warning {
        .summary-card__icon {
          background-color: $brand-warning-light-10;
          color: $brand-warning;
        }
      }

      &--info {
        .summary-card__icon {
          background-color: $brand-info-light-10;
          color: $brand-info;
        }
      }

      // 响应式适配
      @include respond-to-max(sm) {
        padding: $spacing-sm;

        &__icon {
          width: 40px;
          height: 40px;
        }

        &__value {
          font-size: $font-size-xxl;
        }
      }
    }

    // 移动端：调整最小高度
    @include respond-to-max(sm) {
      .summary-card-wrapper {
        min-height: 100px;
      }
    }
  }

  .time-slot-container {
    border: 1px solid $border-light;
    border-radius: $border-radius-lg;
    padding: $spacing-md;
    margin-bottom: $spacing-xl; // 增加间距，增强区块感
    background: $bg-secondary;

    .time-slot-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: $spacing-md;
      flex-wrap: wrap;

      .time-slot-title {
        margin: 0;
        font-size: $font-size-xl;
        font-weight: $font-weight-semibold;
        color: $text-primary;
      }

      .time-slot-subtitle {
        margin: $spacing-xs 0 0;
        font-size: $font-size-sm;
        color: $text-secondary;
      }
    }

    .time-slot-chart-wrapper {
      position: relative;
      margin-top: $spacing-md;
      min-height: calc($spacing-xxl * 6.67); // 48 * 6.67 ≈ 320px
    }

    .chart-scroll-wrapper {
      // 支持横向滚动以显示完整的24小时数据和"平均值"标签
      overflow-x: auto;
      overflow-y: hidden;
      -webkit-overflow-scrolling: touch;
      width: 100%;
      
      .time-slot-chart {
        // 增加最小宽度，确保右侧有足够空间显示"平均值"标签
        min-width: calc($spacing-xxl * 20.83); // 48 * 20.83 ≈ 1000px
      }
    }

    .time-slot-chart {
      width: 100%;
      height: calc($spacing-xxl * 6.67); // 48 * 6.67 ≈ 320px
    }

    .chart-empty {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: calc($spacing-xxl * 6.67); // 48 * 6.67 ≈ 320px
      width: 100%;
    }
  }

  .room-table {
    margin-top: $spacing-xl; // 增加间距，增强区块感

    // 表头样式
    :deep(.el-table__header-wrapper) {
      .el-table__header {
        th {
          background-color: $bg-secondary;
          color: $text-primary;
          font-size: $font-size-base;
          font-weight: $font-weight-semibold;
          height: $spacing-xxl; // 48px
          padding: $spacing-sm $spacing-md;
        }
      }
    }

    // 表格主体样式
    :deep(.el-table__body-wrapper) {
      .el-table__body {
        td {
          padding: $spacing-sm $spacing-md;
          height: $spacing-xxl; // 48px
          border-color: $border-light;
        }

        // 斑马纹已在 Element Plus 中启用，这里可以微调颜色
        tr.el-table__row--striped {
          background-color: $bg-tertiary;
        }
      }
    }

    // 边框样式
    :deep(.el-table) {
      border: 1px solid $border-light;
      border-radius: $border-radius-md;
      overflow: hidden;
    }

    // 响应式适配
    @include respond-to-max(sm) {
      :deep(.el-table__header-wrapper) {
        .el-table__header {
          th {
            height: calc($spacing-xxl - $spacing-xs); // 48 - 4 = 44px
            padding: $spacing-sm $spacing-md;
            font-size: $font-size-sm;
          }
        }
      }

      :deep(.el-table__body-wrapper) {
        .el-table__body {
          td {
            height: calc($spacing-xxl - $spacing-xs); // 48 - 4 = 44px
            padding: $spacing-sm $spacing-md;
            font-size: $font-size-sm;
          }
        }
      }
    }
  }

  // 百分比文字样式
  .percent-text {
    display: inline-block;
    min-width: 70px;
    text-align: right;

    // 成功状态（绿色）
    &--success {
      color: $brand-success;
      font-weight: $font-weight-medium;
    }

    // 警告状态（橙色）
    &--warning {
      color: $brand-warning;
      font-weight: $font-weight-medium;
    }

    // 危险状态（红色）
    &--danger {
      color: $brand-danger;
      font-weight: $font-weight-semibold;
    }

    // 兼容旧的警告类名
    &.is-warning {
      color: $brand-danger;
      font-weight: $font-weight-semibold;
    }

    // 响应式适配
    @include respond-to-max(sm) {
      min-width: 50px;
    }
  }

  // 强调数值样式
  .table-value--emphasis {
    font-weight: $font-weight-semibold;
    color: $text-primary;
  }

  // 表头帮助图标样式
  .table-header-help {
    margin-left: $spacing-xs;
    font-size: $font-size-sm;
    color: $text-secondary;
    cursor: pointer;
    
    &:hover {
      color: $brand-primary;
    }
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: $spacing-md;
    padding: $spacing-sm 0;
  }

  .empty-hint {
    text-align: center;
    padding: $spacing-xxl 0;
  }

  .empty-description {
    color: $text-secondary;
    margin: 0;
    font-size: $font-size-base;
  }

  @include respond-to-max(sm) {
    .card-header {
      flex-direction: column;
      align-items: flex-start;
      gap: $spacing-md;
    }

    .header-right {
      width: 100%;
      flex-direction: column;
      align-items: flex-start;
      gap: $spacing-xs;
    }

    .filter-label {
      font-size: $font-size-xs;
    }

    .date-range {
      width: 100%;
    }

    // 时间范围选择器移动端优化
    :deep(.el-date-editor--daterange) {
      width: 100% !important;
      padding: $spacing-xs $spacing-xs; // 4px 4px，接近原值但符合8px网格
      
      .el-range-separator {
        padding: 0 $spacing-xs;
        font-size: $font-size-xs;
        width: auto;
      }
      
      .el-range-input {
        font-size: $font-size-xs;
        width: 42%;
      }

      .el-range__icon,
      .el-range__close-icon {
        font-size: $font-size-xs;
        width: calc($spacing-sm * 2.25); // 8 * 2.25 = 18px
      }
    }

    .time-slot-chart {
      height: 260px;
    }

    .percent-text {
      min-width: 50px;
    }

    .table-pagination {
      justify-content: center;
      margin-top: $spacing-md;
    }

    // 优化移动端分页组件内部样式
    :deep(.el-pagination) {
      .el-pagination__sizes,
      .el-pagination__total {
        display: none; // 移动端隐藏部分信息，节省空间
      }
    }
  }
}
</style>