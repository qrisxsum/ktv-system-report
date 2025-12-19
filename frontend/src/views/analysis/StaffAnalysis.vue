<template>
  <div class="staff-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>👑 人员风云榜</span>
          <div class="filter-group">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="handleDateChange"
              style="margin-right: 10px"
            />
          </div>
        </div>
      </template>
      
      <div class="chart-container" ref="chartRef" v-loading="loading"></div>
      
      <el-table
        ref="tableRef"
        :data="staffData"
        stripe
        border
        style="margin-top: 20px"
        v-loading="loading"
      >
        <el-table-column type="index" label="排名" width="70" align="center" />
        <el-table-column prop="name" label="姓名" width="150" />
        <el-table-column prop="booking_count" label="订台数" width="120" align="right" />
        <el-table-column prop="sales_amount" label="销售金额" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.sales_amount || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="actual_amount" label="实收金额" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.actual_amount || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="base_performance" label="基本业绩" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.base_performance || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_amount" label="赠送金额" align="right">
          <template #default="{ row }">
            ¥{{ (row.gift_amount || 0).toFixed(2) }}
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="pageSizeOptions"
          :total="total"
          :disabled="loading"
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

const loading = ref(false)
const dateRange = ref([])
const chartRef = ref(null)
const tableRef = ref(null)
let chart = null

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const tableRows = ref([])
const chartRows = ref([])
const total = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20
})

const pageSizeOptions = [20, 50, 100]

const normalizeStaffRow = (item = {}) => ({
  name: item.dimension_label || '未知员工',
  booking_count: item.orders || 0,
  sales_amount: item.sales_amount || 0,
  actual_amount: item.actual || 0,
  base_performance: item.performance || 0,
  gift_amount: item.gift_amount || 0
})

// 处理后的员工数据（按实收金额排序）
const staffData = computed(() => {
  const data = tableRows.value.map(normalizeStaffRow)
  return data.sort((a, b) => b.actual_amount - a.actual_amount)
})

// 图表所用数据（不受分页影响）
const chartStaffData = computed(() => {
  const data = chartRows.value.map(normalizeStaffRow)
  return data.sort((a, b) => b.actual_amount - a.actual_amount)
})

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

    const params = {
      table: 'booking',
      start_date: startDate,
      end_date: endDate,
      dimension: 'employee',
      granularity: 'day',
      page: pagination.page,
      page_size: pagination.pageSize
    }

    // 根据当前门店选择设置store_id参数
    if (currentStore.value !== 'all') {
      params.store_id = parseInt(currentStore.value)
    }

    const response = await queryStats(params)

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
    updateChart()
  }
}

const updateChart = () => {
  if (!chart) return
  
  // 取前10名员工数据（不受分页影响）
  const data = chartStaffData.value
    .slice(0, 10)
    .map(item => ({ name: item.name, value: item.actual_amount }))
    .reverse() // 图表从下到上排列
  
  chart.setOption({
    tooltip: { 
      trigger: 'axis', 
      formatter: '{b}: ¥{c}',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: { left: '15%', right: '15%', top: '5%', bottom: '5%' },
    xAxis: { 
      type: 'value',
      axisLabel: {
        formatter: (value) => '¥' + (value / 1000).toFixed(0) + 'K'
      }
    },
    yAxis: {
      type: 'category',
      data: data.map(d => d.name),
      axisLabel: {
        interval: 0
      }
    },
    series: [{
      type: 'bar',
      data: data.map(d => d.value),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#667eea' },
          { offset: 1, color: '#764ba2' }
        ])
      },
      label: {
        show: true,
        position: 'right',
        formatter: (params) => '¥' + params.value.toLocaleString()
      }
    }]
  })
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

const handleDateChange = () => {
  pagination.page = 1
  fetchData()
}

const handleResize = () => chart?.resize()

onMounted(async () => {
  initChart()
  await initDateRange()
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
    align-items: center;
  }
  
  .chart-container {
    height: 400px;
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
}
</style>

