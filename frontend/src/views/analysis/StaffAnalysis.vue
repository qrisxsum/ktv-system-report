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
          :layout="isSmallScreen ? 'sizes, prev, pager, next' : (isMobile ? 'total, sizes, prev, pager, next' : 'total, sizes, prev, pager, next, jumper')"
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="pageSizeOptions"
          :total="total"
          :disabled="loading"
          :pager-count="isSmallScreen ? 3 : (isMobile ? 5 : 7)"
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

const loading = ref(false)
const dateRange = ref([])
const chartRef = ref(null)
const tableRef = ref(null)
let chart = null
const dateRangeStorageKey = 'viewState:StaffAnalysis:dateRange'

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const tableRows = ref([])
const chartRows = ref([])
const total = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20
})

// 根据屏幕宽度动态设置分页选项
const isMobile = ref(false)
const isSmallScreen = ref(false)
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
  isSmallScreen.value = window.innerWidth <= 480
}

const pageSizeOptions = computed(() => {
  // 移动端只显示较少的选项，避免超出屏幕
  return isMobile.value ? [20, 50] : [20, 50, 100]
})

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
  
  // 根据设备类型调整配置
  const gridConfig = isMobile.value 
    ? { left: '20%', right: '5%', top: '5%', bottom: '10%' } // 移动端：减少右侧空间，增加底部空间给横坐标
    : { left: '15%', right: '15%', top: '5%', bottom: '5%' }
  
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
        fontSize: 10, // 移动端字体更小
        margin: 8 // 增加标签与轴线的距离
      }
    : {
        formatter: (value) => '¥' + (value / 1000).toFixed(0) + 'K'
      }
  
  chart.setOption({
    tooltip: { 
      trigger: 'axis', 
      formatter: '{b}: ¥{c}',
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
        fontSize: isMobile.value ? 11 : undefined // 移动端Y轴标签也稍微缩小
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
        show: !isMobile.value, // 移动端隐藏柱状图右侧的数值标签，避免拥挤
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
  if (isValidDateRange(dateRange.value)) {
    writeSessionJSON(dateRangeStorageKey, dateRange.value)
  }
  fetchData()
}

const handleResize = () => {
  checkMobile()
  chart?.resize()
  // 窗口大小变化时重新更新图表配置，确保移动端/桌面端配置正确
  updateChart()
}

onMounted(async () => {
  checkMobile()
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
    align-items: center;
  }
  
  .chart-container {
    height: 400px;
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
      gap: 10px;

      :deep(.el-radio-group) {
        width: 100%;

        .el-radio-button {
          flex: 1;

          :deep(.el-radio-button__inner) {
            width: 100%;
          }
        }
      }
    }

    .chart-container {
      height: 300px;
    }

    :deep(.el-table) {
      font-size: 12px;

      .el-table__header th,
      .el-table__body td {
        padding: 8px 5px;
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
    :deep(.el-card__header) {
      padding: 12px 15px;
    }

    :deep(.el-card__body) {
      padding: 12px;
    }

    .chart-container {
      height: 250px;
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

    .empty-hint {
      padding: 30px 0;
      font-size: 14px;
    }
  }
}
</style>

