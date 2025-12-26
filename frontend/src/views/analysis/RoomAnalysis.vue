<template>
  <div class="room-analysis">
    <el-card class="filter-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-row">
            <div class="title-text">
              <h2>🎤 包厢效能分析</h2>
              <p class="card-subtitle">包厢使用率、营收表现与折扣分析</p>
            </div>
            <el-tag type="primary" effect="light">数据源：Booking</el-tag>
          </div>
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
            :editable="false"
            @change="handleDateChange"
          />
        </div>
      </div>
    </el-card>
      
    <el-card class="summary-card" shadow="never">
      <el-row :gutter="20" class="summary-cards">
        <el-col :xs="24" :sm="12" :md="6" :span="6">
          <div class="summary-item">
            <div class="label">总开台数</div>
            <div class="value">{{ summary.totalOrders }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :span="6">
          <div class="summary-item">
            <div class="label">总GMV</div>
            <div class="value">¥{{ summary.totalGmv.toLocaleString() }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :span="6">
          <div class="summary-item">
            <div class="label">总实收</div>
            <div class="value">¥{{ summary.totalActual.toLocaleString() }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :span="6">
          <div class="summary-item">
            <div class="label">平均实收</div>
            <div class="value">¥{{ summary.avgActual.toFixed(2) }}</div>
          </div>
        </el-col>
      </el-row>
      
      <el-table
        ref="tableRef"
        :data="roomData"
        stripe
        border
        style="margin-top: 20px"
        v-loading="loading"
      >
        <el-table-column prop="room_name" label="包厢名称" min-width="150" fixed="left" />
        <el-table-column prop="order_count" label="开台次数" min-width="100" align="right" />
        <el-table-column prop="gmv" label="GMV（应收金额）" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.gmv || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="actual" label="实收金额" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.actual || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="room_discount" label="包厢折扣" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.room_discount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="beverage_discount" label="酒水折扣" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.beverage_discount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_amount" label="赠送金额" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.gift_amount || 0).toFixed(2) }}
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
import { ref, onMounted, computed, inject, watch, reactive, nextTick } from 'vue'
import { queryStats, getDateRange } from '@/api/stats'
import { ElMessage } from 'element-plus'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'
import { usePagination } from '@/composables/usePagination'

const loading = ref(false)
const dateRange = ref([])
const tableRef = ref(null)
const dateRangeStorageKey = 'viewState:RoomAnalysis:dateRange'

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const tableRows = ref([])
const summaryRows = ref([])
const total = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20
})

// 使用分页优化 Composable
const { pageSizeOptions, paginationLayout, pagerCount } = usePagination({
  desktopPageSizes: [20, 50, 100],
  mobilePageSizes: [20, 50]
})

// 汇总统计
const summary = computed(() => {
  const source = summaryRows.value.length ? summaryRows.value : tableRows.value
  const totalOrders = source.reduce((sum, item) => sum + (item.orders || 0), 0)
  const totalGmv = source.reduce((sum, item) => sum + (item.gmv || 0), 0)
  const totalActual = source.reduce((sum, item) => sum + (item.actual || 0), 0)
  const avgActual = totalOrders > 0 ? totalActual / totalOrders : 0
  
  return {
    totalOrders,
    totalGmv,
    totalActual,
    avgActual
  }
})

// 处理后的包厢数据
const roomData = computed(() => {
  return tableRows.value.map(item => ({
    room_name: item.dimension_label || '未知包厢',
    order_count: item.orders || 0,
    gmv: item.gmv || 0,
    actual: item.actual || 0,
    room_discount: item.room_discount || 0,
    beverage_discount: item.beverage_discount || 0,
    gift_amount: item.gift_amount || 0
  }))
})

// 初始化日期范围（使用数据库中的最新日期）
const initDateRange = async () => {
  try {
    const rangeRes = await getDateRange('room')
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
      table: 'room',
      start_date: startDate,
      end_date: endDate,
      dimension: 'room',
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
      summaryRows.value = seriesRows
      const parsedTotal = Number(response.data.total)
      total.value = Number.isFinite(parsedTotal) ? parsedTotal : rows.length
    } else {
      tableRows.value = []
      summaryRows.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('获取包厢分析数据失败:', error)
    ElMessage.error('获取包厢分析数据失败')
    tableRows.value = []
    summaryRows.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// 监听门店变化，重新获取数据
watch(currentStore, () => {
  pagination.page = 1
  fetchData()
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
  await fetchData()
})
</script>

<style lang="scss" scoped>
.room-analysis {
  display: flex;
  flex-direction: column;
  gap: 20px;

  .card-header {
    .title-row {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      flex-wrap: wrap;

      .title-text {
        h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }

        .card-subtitle {
          margin: 4px 0 0;
          color: #909399;
          font-size: 13px;
        }
      }

      .el-tag {
        flex-shrink: 0;
        margin-top: 2px;
      }
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
      gap: 12px;

      :deep(.el-date-editor--daterange) {
        width: 360px;
      }
    }

    .filter-label {
      font-size: 13px;
      color: #606266;
      white-space: nowrap;
    }
  }

  .date-range {
    width: 360px;
    max-width: 100%;
  }

  @media (max-width: 768px) {
    :deep(.el-card__header) {
      padding: 12px 15px;
    }

    :deep(.el-card__body) {
      padding: 12px;
    }

    .card-header {
      .title-row {
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;

        .title-text {
          h2 {
            font-size: 16px;
          }

          .card-subtitle {
            font-size: 12px;
          }
        }
      }
    }

    .filters {
      flex-direction: column;
      align-items: stretch;
      gap: 14px;

      .filter-item {
        width: 100%;
        flex-wrap: wrap;
        gap: 8px;

        :deep(.el-date-editor--daterange) {
          width: 100% !important;
        }
      }
    }

    .filter-label {
      font-size: 12px;
    }

    .date-range {
      width: 100%;
    }

    // 时间范围选择器样式优化（与财务专项一致）
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
  
  .summary-cards {
    .summary-item {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 8px;
      padding: 20px;
      color: #fff;
      text-align: center;
      
      .label {
        font-size: 14px;
        opacity: 0.9;
        margin-bottom: 8px;
      }
      
      .value {
        font-size: 24px;
        font-weight: bold;
      }
    }
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
      flex-wrap: wrap;
      gap: 10px;

      :deep(.el-date-editor) {
        width: 100%;
      }
    }

    .summary-cards {
      // 移动端每个卡片占满一行，增加底部间距
      :deep(.el-col) {
        margin-bottom: 12px;
      }

      .summary-item {
        padding: 15px;

        .label {
          font-size: 13px;
        }

        .value {
          font-size: 20px;
        }
      }
    }

    .metrics-row {
      :deep(.el-col) {
        margin-bottom: 12px;
      }

      .metric-card {
        padding: 15px;

        .label {
          font-size: 13px;
        }

        .value {
          font-size: 20px;
        }
      }
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

    .card-header {
      font-size: 14px;
    }

    .summary-cards {
      // 极小屏幕下确保每个卡片占满一行
      :deep(.el-col) {
        margin-bottom: 10px;
      }

      .summary-item {
        padding: 12px;

        .label {
          font-size: 12px;
        }

        .value {
          font-size: 18px;
        }
      }
    }

    .metrics-row {
      .metric-card {
        padding: 12px;

        .label {
          font-size: 12px;
        }

        .value {
          font-size: 18px;
        }
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

