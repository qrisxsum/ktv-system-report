<template>
  <div class="product-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="header-title">🍺 商品销售分析</span>
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
      
      <el-table
        ref="tableRef"
        :data="productData"
        stripe
        border
        v-loading="loading"
      >
        <el-table-column prop="product_name" label="商品名称" min-width="150" />
        <el-table-column prop="sales_qty" label="销售数量" min-width="100" align="right">
          <template #default="{ row }">
            {{ row.sales_qty || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="sales_amount" label="销售金额" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.sales_amount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_qty" label="赠送数量" min-width="100" align="right">
          <template #default="{ row }">
            {{ row.gift_qty || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_amount" label="赠送金额" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.gift_amount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.cost || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit" label="利润" min-width="120" align="right">
          <template #default="{ row }">
            ¥{{ (row.profit || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" label="利润率" min-width="100" align="right">
          <template #default="{ row }">
            {{ row.profit_rate ? row.profit_rate.toFixed(2) : '0.00' }}%
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
      
      <div v-if="!productData.length && !loading" class="empty-hint">
        暂无数据，请先上传商品销售数据
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
const dateRangeStorageKey = 'viewState:ProductAnalysis:dateRange'

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const tableRows = ref([])
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

// 处理后的商品数据
const productData = computed(() => {
  return tableRows.value.map(item => {
    const salesAmount = item.sales_amount || 0
    const cost = item.cost ?? item.cost_total ?? 0
    const profit = item.profit || 0
    const profitRate = item.profit_rate || 0  // 直接使用后端返回的利润率（成本利润率）
    
    return {
      product_name: item.dimension_label || '未知商品',
      sales_qty: item.sales_qty || 0,
      sales_amount: salesAmount,
      gift_qty: item.gift_qty || 0,
      gift_amount: item.gift_amount || 0,
      cost: cost,
      profit: profit,
      profit_rate: profitRate
    }
  }).sort((a, b) => b.sales_amount - a.sales_amount) // 按销售额降序排列
})

// 初始化日期范围（使用数据库中的最新日期）
const initDateRange = async () => {
  try {
    const rangeRes = await getDateRange('sales')
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
      table: 'sales',
      start_date: startDate,
      end_date: endDate,
      dimension: 'product',
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
      tableRows.value = rows
      const parsedTotal = Number(response.data.total)
      total.value = Number.isFinite(parsedTotal) ? parsedTotal : rows.length
    } else {
      tableRows.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('获取商品分析数据失败:', error)
    ElMessage.error('获取商品分析数据失败')
    tableRows.value = []
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
.product-analysis {
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

      .header-right {
        margin-top: 10px;
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
  
  .empty-hint {
    text-align: center;
    padding: 40px 0;
    color: #999;
  }

  .table-pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
    width: 100%;
  }
}
</style>

