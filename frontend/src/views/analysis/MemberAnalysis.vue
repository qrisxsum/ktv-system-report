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
            v-model="dateRange"
            type="daterange"
            unlink-panels
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            @change="handleDateRangeChange"
          />
        </div>

        <div class="filter-item dimension-switch">
          <span class="filter-label">分析维度</span>
          <el-radio-group v-model="queryFilters.dimension" @change="handleDimensionChange">
            <el-radio-button value="date">按日期</el-radio-button>
            <el-radio-button value="store">按门店</el-radio-button>
          </el-radio-group>
        </div>

        <el-button type="primary" @click="fetchData" :loading="loading">
          <el-icon><Search /></el-icon>
          查询
        </el-button>
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
      <div class="chart-container" ref="trendChartRef" v-loading="loading"></div>
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
        :default-sort="{ prop: 'recharge_real_income', order: 'descending' }"
      >
        <el-table-column
          :prop="queryFilters.dimension === 'date' ? 'dimension_key' : 'dimension_label'"
          :label="queryFilters.dimension === 'date' ? '日期' : '门店'"
          width="150"
          fixed
        />
        <el-table-column prop="recharge_real_income" label="充值实收" align="right" sortable>
          <template #default="{ row }">
            <span class="amount positive">¥{{ formatNumber(row.recharge_real_income) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="recharge_count" label="充值笔数" align="right" sortable width="100" />
        <el-table-column prop="room_amount_principal" label="房费本金" align="right" sortable>
          <template #default="{ row }">
            ¥{{ formatNumber(row.room_amount_principal) }}
          </template>
        </el-table-column>
        <el-table-column prop="drink_amount_principal" label="酒水本金" align="right" sortable>
          <template #default="{ row }">
            ¥{{ formatNumber(row.drink_amount_principal) }}
          </template>
        </el-table-column>
        <el-table-column prop="room_amount_gift" label="房费赠送" align="right" sortable>
          <template #default="{ row }">
            <span class="amount gift">¥{{ formatNumber(row.room_amount_gift) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="drink_amount_gift" label="酒水赠送" align="right" sortable>
          <template #default="{ row }">
            <span class="amount gift">¥{{ formatNumber(row.drink_amount_gift) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="points_delta" label="积分变动" align="right" sortable width="100" />
        <el-table-column prop="growth_delta" label="成长值" align="right" sortable width="100" />
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
import { Search, CreditCard, Wallet, Present, Star } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { queryStats, getDateRange } from '@/api/stats'
import { ElMessage } from 'element-plus'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'
import { usePagination } from '@/composables/usePagination'

const loading = ref(false)
const dateRange = ref([])
const trendChartRef = ref(null)
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
      top_n: 50
    }

    // 使用全局门店筛选
    if (currentStore.value && currentStore.value !== 'all') {
      const parsedStoreId = parseInt(currentStore.value, 10)
      if (Number.isFinite(parsedStoreId)) {
        params.store_id = parsedStoreId
      }
    }

    const response = await queryStats(params)

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
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          rotate: isMobile.value ? 45 : 0,
          fontSize: isMobile.value ? 10 : 12
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
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: stores,
        axisLabel: {
          rotate: 30,
          fontSize: isMobile.value ? 10 : 12,
          interval: 0
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
          barMaxWidth: 50,
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

const handleResize = () => {
  checkDevice()
  trendChart?.resize()
  updateChart()
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
    gap: 16px;
    align-items: flex-end;

    .filter-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .filter-label {
        font-size: 13px;
        color: #606266;
      }
    }

    .dimension-switch {
      :deep(.el-radio-button__inner) {
        padding: 8px 16px;
      }
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

    .chart-container {
      height: 350px;
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
      }

      .dimension-switch {
        :deep(.el-radio-group) {
          width: 100%;
          display: flex;
        }

        :deep(.el-radio-button) {
          flex: 1;
        }

        :deep(.el-radio-button__inner) {
          width: 100%;
          padding: 10px 8px;
        }
      }

      > .el-button {
        width: 100%;
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

    .chart-container {
      height: 280px !important;
    }

    :deep(.el-table) {
      font-size: 12px;
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

    .chart-container {
      height: 220px !important;
    }
  }
}
</style>

