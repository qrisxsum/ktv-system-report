<template>
  <div class="member-analysis">
    <el-card class="filter-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <h2>💳 会员变动分析</h2>
            <p class="card-subtitle">会员充值、消费及积分成长趋势分析</p>
          </div>
          <el-tag type="success" effect="light">数据源：会员变动明细</el-tag>
        </div>
      </template>

      <div class="filters">
        <div class="filter-item">
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
            @change="handleDateRangeChange"
          />
        </div>

        <div class="filter-item dimension-switch">
          <span class="filter-label">分析维度</span>
          <el-radio-group
            v-model="queryFilters.dimension"
            @change="handleDimensionChange"
            size="small"
          >
            <el-radio-button value="date">按日期</el-radio-button>
            <el-radio-button value="store">按门店</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </el-card>

    <!-- 汇总卡片 -->
    <div class="summary-cards" v-loading="loading">
      <div class="summary-card recharge">
        <div class="card-icon">
          <el-icon><CreditCard /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-title">充值实收</div>
          <div class="card-value">¥{{ formatNumber(summaryData.recharge_real_income) }}</div>
          <div class="card-sub">
            <span>充值笔数 {{ summaryData.recharge_count || 0 }} 笔</span>
          </div>
        </div>
      </div>

      <div class="summary-card principal">
        <div class="card-icon">
          <el-icon><Wallet /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-title">本金变动</div>
          <div class="card-value">¥{{ formatNumber(totalPrincipal) }}</div>
          <div class="card-sub">
            <span>房费 {{ formatNumber(summaryData.room_amount_principal) }}</span>
            <span>酒水 {{ formatNumber(summaryData.drink_amount_principal) }}</span>
          </div>
        </div>
      </div>

      <div class="summary-card gift">
        <div class="card-icon">
          <el-icon><Present /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-title">赠送变动</div>
          <div class="card-value">¥{{ formatNumber(totalGift) }}</div>
          <div class="card-sub">
            <span>房费赠送 {{ formatNumber(summaryData.room_amount_gift) }}</span>
            <span>酒水赠送 {{ formatNumber(summaryData.drink_amount_gift) }}</span>
          </div>
        </div>
      </div>

      <div class="summary-card points">
        <div class="card-icon">
          <el-icon><Star /></el-icon>
        </div>
        <div class="card-content">
          <div class="card-title">积分 / 成长值</div>
          <div class="card-value">{{ formatNumber(summaryData.points_delta, 0) }}</div>
          <div class="card-sub">
            <span>积分变动 {{ formatNumber(summaryData.points_delta, 0) }}</span>
            <span>成长值 {{ formatNumber(summaryData.growth_delta, 0) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 趋势图表 -->
    <el-card class="chart-card" shadow="never">
      <template #header>
        <div class="chart-header">
          <span class="chart-title">📈 {{ queryFilters.dimension === 'date' ? '充值趋势' : '门店充值对比' }}</span>
        </div>
      </template>
      <div class="chart-wrapper" ref="trendChartWrapperRef">
        <div class="chart-container" ref="trendChartRef" v-loading="loading"></div>
      </div>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <span class="table-title">📊 明细数据</span>
        </div>
      </template>

      <el-table
        ref="tableRef"
        :data="tableData"
        stripe
        border
        v-loading="loading"
        @sort-change="handleSortChange"
      >
        <el-table-column
          :prop="queryFilters.dimension === 'date' ? 'dimension_key' : 'dimension_label'"
          :label="queryFilters.dimension === 'date' ? '日期' : '门店'"
          :width="isMobile ? 100 : 150"
          :fixed="isMobile ? 'left' : false"
          :sortable="queryFilters.dimension === 'date' ? 'custom' : false"
          show-overflow-tooltip
        />
        <el-table-column prop="recharge_real_income" label="充值实收" align="right" sortable="custom" :min-width="isMobile ? 100 : 110">
          <template #default="{ row }">
            <span class="amount positive">¥{{ formatNumber(row.recharge_real_income) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="recharge_count" label="充值笔数" align="right" sortable="custom" :width="isMobile ? 80 : 100" />
        <el-table-column prop="room_amount_principal" label="房费本金" align="right" sortable="custom" :min-width="isMobile ? 100 : 110">
          <template #default="{ row }">
            ¥{{ formatNumber(row.room_amount_principal) }}
          </template>
        </el-table-column>
        <el-table-column prop="drink_amount_principal" label="酒水本金" align="right" sortable="custom" :min-width="isMobile ? 100 : 110">
          <template #default="{ row }">
            ¥{{ formatNumber(row.drink_amount_principal) }}
          </template>
        </el-table-column>
        <el-table-column prop="room_amount_gift" label="房费赠送" align="right" sortable="custom" :min-width="isMobile ? 100 : 110">
          <template #default="{ row }">
            <span class="amount gift">¥{{ formatNumber(row.room_amount_gift) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="drink_amount_gift" label="酒水赠送" align="right" sortable="custom" :min-width="isMobile ? 100 : 110">
          <template #default="{ row }">
            <span class="amount gift">¥{{ formatNumber(row.drink_amount_gift) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="points_delta" label="积分变动" align="right" sortable="custom" :width="isMobile ? 80 : 100" />
        <el-table-column prop="growth_delta" label="成长值" align="right" sortable="custom" :width="isMobile ? 80 : 100" />
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
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, inject, nextTick } from 'vue'
import { CreditCard, Wallet, Present, Star } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { queryStats, getDateRange } from '@/api/stats'
import { ElMessage } from 'element-plus'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'
import { usePagination } from '@/composables/usePagination'

const loading = ref(false)
const dateRange = ref([])
const trendChartRef = ref(null)
const trendChartWrapperRef = ref(null)
const tableRef = ref(null)
let trendChart = null
const dateRangeStorageKey = 'viewState:MemberAnalysis:dateRange'

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const queryFilters = reactive({
  dimension: 'date'
})

const tableData = ref([])
const chartData = ref([])
const summaryData = ref({})
const total = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20
})

const sortState = reactive({
  prop: null,
  order: null
})

// 使用分页优化 Composable
const { isMobile, pageSizeOptions, paginationLayout, pagerCount, checkDevice } = usePagination({
  desktopPageSizes: [20, 50, 100],
  mobilePageSizes: [20, 50]
})

// 计算本金合计
const totalPrincipal = computed(() => {
  return (summaryData.value.room_amount_principal || 0) + (summaryData.value.drink_amount_principal || 0)
})

// 计算赠送合计
const totalGift = computed(() => {
  return (summaryData.value.room_amount_gift || 0) + (summaryData.value.drink_amount_gift || 0)
})

// 格式化数字
const formatNumber = (value, decimals = 2) => {
  if (value === null || value === undefined) return '0'
  const num = Number(value)
  if (isNaN(num)) return '0'
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

// 初始化日期范围
const initDateRange = async () => {
  try {
    const rangeRes = await getDateRange('member_change')
    if (rangeRes.success && rangeRes.suggested_start && rangeRes.suggested_end) {
      dateRange.value = [rangeRes.suggested_start, rangeRes.suggested_end]
    } else {
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

    const params = {
      table: 'member_change',
      start_date: startDate,
      end_date: endDate,
      dimension: queryFilters.dimension,
      granularity: 'day',
      page: pagination.page,
      page_size: pagination.pageSize,
      top_n: 50,
      sort_by: sortState.prop ?? undefined,
      sort_order: sortState.order === 'ascending' ? 'asc' : sortState.order === 'descending' ? 'desc' : undefined
    }

    // 使用全局门店筛选
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
      tableData.value = rows
      chartData.value = seriesRows
      summaryData.value = response.data.summary || {}
      total.value = Number(response.data.total) || rows.length
    } else {
      tableData.value = []
      chartData.value = []
      summaryData.value = {}
      total.value = 0
    }

    updateChart()
  } catch (error) {
    console.error('获取会员变动数据失败:', error)
    ElMessage.error('获取会员变动数据失败')
    tableData.value = []
    chartData.value = []
    summaryData.value = {}
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 初始化图表
const initChart = () => {
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    updateChart()
  }
}

// 更新图表
const updateChart = () => {
  if (!trendChart) return

  const data = chartData.value

  if (queryFilters.dimension === 'date') {
    // 时间趋势图
    const dates = data.map(d => d.dimension_key || d.dimension_label)
    const rechargeData = data.map(d => d.recharge_real_income || 0)

    trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const date = params[0]?.axisValue || ''
          let html = `<div style="font-weight:600;margin-bottom:8px">${date}</div>`
          params.forEach(p => {
            html += `<div style="display:flex;justify-content:space-between;gap:20px">
              <span>${p.marker} ${p.seriesName}</span>
              <span style="font-weight:600">¥${Number(p.value).toLocaleString()}</span>
            </div>`
          })
          return html
        }
      },
      legend: {
        data: ['充值实收'],
        bottom: 0
      },
      grid: {
        left: isMobile.value ? '10%' : '3%',
        right: isMobile.value ? '5%' : '4%',
        bottom: isMobile.value ? '20%' : '15%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          rotate: isMobile.value ? 45 : 0,
          fontSize: isMobile.value ? 10 : 12,
          // 移动端显示所有标签，桌面端根据数据量自动调整间隔避免重叠
          interval: isMobile.value ? 0 : 'auto'
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value) => {
            // 优化显示格式：数字+单位，避免多余的"0"
            if (value >= 10000) {
              const wan = value / 10000
              return wan % 1 === 0 ? `${wan}万` : `${wan.toFixed(1)}万`
            } else if (value >= 1000) {
              const k = value / 1000
              return k % 1 === 0 ? `${k}K` : `${k.toFixed(1)}K`
            } else {
              return value % 1 === 0 ? `${value}` : `${value.toFixed(1)}`
            }
          },
          fontSize: isMobile.value ? 10 : undefined
        }
      },
      series: [
        {
          name: '充值实收',
          type: 'line',
          data: rechargeData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 3,
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#36d399' },
              { offset: 1, color: '#22c55e' }
            ])
          },
          itemStyle: {
            color: '#22c55e'
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34, 197, 94, 0.3)' },
              { offset: 1, color: 'rgba(34, 197, 94, 0.05)' }
            ])
          }
        }
      ]
    }, true)
  } else {
    // 门店对比柱状图
    const stores = data.map(d => d.dimension_label || d.dimension_key || '未知门店')
    const rechargeData = data.map(d => d.recharge_real_income || 0)

    trendChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) => {
          const store = params[0]?.axisValue || ''
          let html = `<div style="font-weight:600;margin-bottom:8px">${store}</div>`
          params.forEach(p => {
            html += `<div style="display:flex;justify-content:space-between;gap:20px">
              <span>${p.marker} ${p.seriesName}</span>
              <span style="font-weight:600">¥${Number(p.value).toLocaleString()}</span>
            </div>`
          })
          return html
        }
      },
      legend: {
        data: ['充值实收'],
        bottom: 0
      },
      grid: {
        left: isMobile.value ? '25%' : '3%',
        right: isMobile.value ? '5%' : '4%',
        bottom: isMobile.value ? '20%' : '15%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: stores,
        axisLabel: {
          rotate: isMobile.value ? 45 : 30,
          fontSize: isMobile.value ? 10 : 12,
          interval: 0,
          width: isMobile.value ? 80 : undefined,
          overflow: isMobile.value ? 'none' : undefined,
          ellipsis: isMobile.value ? '' : undefined
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value) => {
            if (value >= 10000) {
              return (value / 10000).toFixed(0) + '万'
            }
            return value
          }
        }
      },
      series: [
        {
          name: '充值实收',
          type: 'bar',
          data: rechargeData,
          barMaxWidth: isMobile.value ? 30 : 50,
          barCategoryGap: isMobile.value ? '30%' : '20%',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#36d399' },
              { offset: 1, color: '#22c55e' }
            ]),
            borderRadius: [4, 4, 0, 0]
          }
        }
      ]
    }, true)
  }
  
  // 移动端：图表更新后，将滚动位置设置为中间
  if (isMobile.value && trendChartWrapperRef.value) {
    nextTick(() => {
      const wrapper = trendChartWrapperRef.value
      if (wrapper && wrapper.scrollWidth > wrapper.clientWidth) {
        const scrollLeft = (wrapper.scrollWidth - wrapper.clientWidth) / 2
        wrapper.scrollLeft = scrollLeft
      }
    })
  }
}

// 事件处理
const handleDateRangeChange = () => {
  pagination.page = 1
  if (isValidDateRange(dateRange.value)) {
    writeSessionJSON(dateRangeStorageKey, dateRange.value)
  }
  fetchData()
}

const handleDimensionChange = () => {
  pagination.page = 1
  // 维度变化时重置排序
  sortState.prop = null
  sortState.order = null
  fetchData()
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

// 将图表滚动到中间位置
const scrollTrendChartToCenter = () => {
  if (isMobile.value && trendChartWrapperRef.value) {
    nextTick(() => {
      const wrapper = trendChartWrapperRef.value
      if (wrapper && wrapper.scrollWidth > wrapper.clientWidth) {
        const scrollLeft = (wrapper.scrollWidth - wrapper.clientWidth) / 2
        wrapper.scrollLeft = scrollLeft
      }
    })
  }
}

const handleResize = () => {
  checkDevice()
  trendChart?.resize()
  updateChart()
  // 移动端：窗口大小变化后重新居中滚动
  scrollTrendChartToCenter()
}

// 监听门店变化
watch(currentStore, () => {
  pagination.page = 1
  fetchData()
})

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
  trendChart?.dispose()
})
</script>

<style lang="scss" scoped>
.member-analysis {
  .filter-card {
    margin-bottom: 16px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 12px;

    h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }

    .card-subtitle {
      margin: 4px 0 0;
      font-size: 13px;
      color: #909399;
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
      gap: 8px;

      .filter-label {
        font-size: 13px;
        color: #606266;
        white-space: nowrap;
      }

      .date-range {
        width: 360px;
        max-width: 100%;
      }
    }

    .dimension-switch {
      display: flex;
      align-items: center;
      gap: 12px;
    }
  }

  // 汇总卡片
  .summary-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 16px;
  }

  .summary-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    color: #fff;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    transition: transform 0.2s, box-shadow 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    &.recharge {
      background: linear-gradient(135deg, #36d399 0%, #22c55e 100%);
      box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3);
      &:hover {
        box-shadow: 0 6px 20px rgba(34, 197, 94, 0.4);
      }
    }

    &.principal {
      background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
      box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
      &:hover {
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
      }
    }

    &.gift {
      background: linear-gradient(135deg, #f472b6 0%, #db2777 100%);
      box-shadow: 0 4px 15px rgba(244, 114, 182, 0.3);
      &:hover {
        box-shadow: 0 6px 20px rgba(244, 114, 182, 0.4);
      }
    }

    &.points {
      background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
      box-shadow: 0 4px 15px rgba(251, 191, 36, 0.3);
      &:hover {
        box-shadow: 0 6px 20px rgba(251, 191, 36, 0.4);
      }
    }

    .card-icon {
      width: 50px;
      height: 50px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
    }

    .card-content {
      flex: 1;
      min-width: 0;

      .card-title {
        font-size: 13px;
        opacity: 0.9;
        margin-bottom: 4px;
      }

      .card-value {
        font-size: 24px;
        font-weight: 700;
        line-height: 1.2;
      }

      .card-sub {
        margin-top: 8px;
        font-size: 12px;
        opacity: 0.8;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }
    }
  }

  // 图表卡片
  .chart-card {
    margin-bottom: 16px;

    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .chart-title {
      font-weight: 600;
    }

    .chart-wrapper {
      // 移动端：支持横向滚动以显示完整的横坐标标签
      @media (max-width: 768px) {
        overflow-x: auto;
        overflow-y: hidden;
        -webkit-overflow-scrolling: touch;
        width: 100%;
        
        .chart-container {
          min-width: 600px; // 确保图表有足够宽度显示完整标签
        }
      }
    }

    .chart-container {
      height: 350px;
      width: 100%;
    }
  }

  // 表格卡片
  .table-card {
    .table-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .table-title {
      font-weight: 600;
    }

    .amount {
      &.positive {
        color: #22c55e;
        font-weight: 600;
      }

      &.gift {
        color: #f472b6;
      }
    }

    .table-pagination {
      display: flex;
      justify-content: flex-end;
      margin-top: 16px;
    }
  }

  // 移动端适配
  @media (max-width: 1200px) {
    .summary-cards {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 768px) {
    .card-header {
      flex-direction: column;
      align-items: flex-start;
    }

    .filters {
      flex-direction: column;
      align-items: stretch;

      .filter-item {
        width: 100%;
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;

        .filter-label {
          font-size: 12px;
        }

        .date-range {
          width: 100%;
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
        width: 100%;
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;

        :deep(.el-radio-group) {
          width: 100%;

          .el-radio-button {
            flex: 1;

            .el-radio-button__inner {
              width: 100%;
              padding: 8px 12px;
            }
          }
        }
      }
    }

    .summary-cards {
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .summary-card {
      padding: 14px;

      .card-icon {
        width: 40px;
        height: 40px;
        font-size: 18px;
      }

      .card-content {
        .card-value {
          font-size: 18px;
        }

        .card-sub {
          flex-direction: column;
          gap: 2px;
        }
      }
    }

      .chart-wrapper {
        .chart-container {
          height: 280px !important;
        }
      }

    :deep(.el-table) {
      font-size: 12px;

      // 防止数字换行
      .el-table__header th,
      .el-table__body td {
        white-space: nowrap;
        padding: 8px 4px;
      }

      // 金额列确保不换行
      .amount {
        white-space: nowrap;
        display: inline-block;
      }

      // 右对齐列的内容不换行
      .el-table__cell {
        &[style*="text-align: right"] {
          white-space: nowrap;
        }
      }
    }

    .table-pagination {
      justify-content: center !important;
    }
  }

  @media (max-width: 480px) {
    .summary-cards {
      grid-template-columns: 1fr;
    }

    .summary-card {
      .card-icon {
        display: none;
      }
    }

      .chart-wrapper {
        .chart-container {
          height: 220px !important;
        }
      }
  }
}
</style>

