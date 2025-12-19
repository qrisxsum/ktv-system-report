<template>
  <div class="room-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="header-title">🎤 包厢效能分析</span>
          <div class="header-right">
            <span class="filter-label">时间</span>
            <el-date-picker
              class="date-range"
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="MM-DD"
              value-format="YYYY-MM-DD"
              @change="handleDateChange"
              size="default"
            />
          </div>
        </div>
      </template>
      
      <el-row :gutter="20" class="summary-cards">
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">总开台数</div>
            <div class="value">{{ summary.totalOrders }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">总GMV</div>
            <div class="value">¥{{ summary.totalGmv.toLocaleString() }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="label">总实收</div>
            <div class="value">¥{{ summary.totalActual.toLocaleString() }}</div>
          </div>
        </el-col>
        <el-col :span="6">
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
        <el-table-column prop="room_name" label="包厢名称" width="180" />
        <el-table-column prop="order_count" label="开台次数" width="120" align="right" />
        <el-table-column prop="gmv" label="GMV（应收金额）" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.gmv || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="actual" label="实收金额" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.actual || 0).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="room_discount" label="包厢折扣" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.room_discount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="beverage_discount" label="酒水折扣" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.beverage_discount || 0).toFixed(2) }}
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

const loading = ref(false)
const dateRange = ref([])
const tableRef = ref(null)

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const tableRows = ref([])
const summaryRows = ref([])
const total = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20
})

const pageSizeOptions = [20, 50, 100]

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
    if (currentStore.value !== 'all') {
      params.store_id = parseInt(currentStore.value)
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
  fetchData()
}

onMounted(async () => {
  await initDateRange()
  await fetchData()
})
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
    flex: 0 0 auto;
  }

  .filter-label {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
  }

  .date-range {
    width: 320px;
    max-width: 100%;
  }

  @media (max-width: 768px) {
    .header-right {
      width: 100%;
    }

    .date-range {
      width: 100%;
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
  }
  
  .empty-hint {
    text-align: center;
    padding: 40px 0;
    color: #999;
  }
}
</style>

