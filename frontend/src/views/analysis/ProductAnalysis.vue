<template>
  <div class="product-analysis">
    <el-card class="filter-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-row">
            <div class="title-text">
              <h2>🍺 商品销售分析</h2>
              <p class="card-subtitle">商品销量、滞销异常识别与SKU排名</p>
            </div>
            <el-tag type="info" effect="light">数据源：商品销售</el-tag>
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

        <div class="filter-item">
          <span class="filter-label">搜索商品</span>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索商品..."
            class="search-input"
            clearable
            @clear="handleSearch"
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <div class="filter-item exception-switch">
          <span class="filter-label">商品筛选</span>
          <el-switch
            v-model="showExceptionOnly"
            inline-prompt
            active-text="仅看滞销/异常"
            inactive-text="全部商品"
            @change="handleExceptionToggle"
          />
        </div>
      </div>
    </el-card>
      
    <div
      v-if="chartProductData.length"
      class="ranking-row"
    >
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="chart-card">
              <template #header>
                <span class="chart-title">🔥 爆款榜 (销售额 Top 10)</span>
              </template>
              <div class="chart-wrapper">
                <div ref="salesChartRef" class="chart-container"></div>
                <div
                  v-if="!topSalesData.length"
                  class="chart-empty"
                >
                  暂无数据
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="chart-card">
              <template #header>
                <span class="chart-title">💰 盈利榜 (毛利额 Top 10)</span>
              </template>
              <div class="chart-wrapper">
                <div ref="profitChartRef" class="chart-container"></div>
                <div
                  v-if="!topProfitData.length"
                  class="chart-empty"
                >
                  暂无数据
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="chart-card">
              <template #header>
                <span class="chart-title">⚠️ 损耗榜 (赠送金额 Top 10)</span>
              </template>
              <div class="chart-wrapper">
                <div ref="giftChartRef" class="chart-container"></div>
                <div
                  v-if="!topGiftData.length"
                  class="chart-empty"
                >
                  暂无数据
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <div
        v-if="chartProductData.length"
        class="category-structure"
      >
        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <el-card class="chart-card">
              <template #header>
                <span class="chart-title">📦 品类销售占比</span>
              </template>
              <div class="chart-wrapper">
                <div ref="categoryChartRef" class="chart-container"></div>
                <div
                  v-if="!categoryChartData.length"
                  class="chart-empty"
                >
                  暂无数据
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

    <el-card class="table-card" shadow="never">
      <el-table
        ref="tableRef"
        :data="tableProductData"
        stripe
        border
        v-loading="loading"
        :row-class-name="getRowClass"
        :default-sort="{ prop: 'sales_amount', order: 'descending' }"
      >
        <el-table-column prop="product_name" label="商品名称" min-width="150" fixed="left" />
        <el-table-column prop="sales_qty" label="销售数量" min-width="100" align="right" sortable>
          <template #default="{ row }">
            {{ formatInteger(row.sales_qty) }}
          </template>
        </el-table-column>
        <el-table-column prop="sales_amount" label="销售金额" min-width="120" align="right" sortable>
          <template #default="{ row }">
            {{ formatCurrency(row.sales_amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_qty" label="赠送数量" min-width="100" align="right" sortable>
          <template #default="{ row }">
            {{ formatInteger(row.gift_qty) }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_amount" label="赠送金额" min-width="120" align="right" sortable>
          <template #default="{ row }">
            {{ formatCurrency(row.gift_amount) }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_rate" label="赠送率" min-width="120" align="right" sortable>
          <template #default="{ row }">
            {{ formatPercent(row.gift_rate) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本" min-width="120" align="right" sortable>
          <template #default="{ row }">
            {{ formatCurrency(row.cost) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit" label="利润" min-width="120" align="right" sortable>
          <template #default="{ row }">
            {{ formatCurrency(row.profit) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" label="成本利润率" min-width="110" align="right" sortable>
          <template #default="{ row }">
            {{ formatPercent(row.profit_rate) }}
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
          :total="tableTotal"
          :disabled="loading"
          :pager-count="pagerCount"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
      
      <div v-if="!tableProductData.length && !loading" class="empty-hint">
        {{ showExceptionOnly ? '暂无滞销或异常赠送商品' : '暂无数据，请先上传商品销售数据' }}
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, inject, watch, reactive, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Search } from '@element-plus/icons-vue'
import { queryStats, getDateRange } from '@/api/stats'
import { ElMessage } from 'element-plus'
import { readSessionJSON, writeSessionJSON, isValidDateRange } from '@/utils/viewState'
import { usePagination } from '@/composables/usePagination'

const loading = ref(false)
const dateRange = ref([])
const showExceptionOnly = ref(false)
const searchKeyword = ref('')
const tableRef = ref(null)
const dateRangeStorageKey = 'viewState:ProductAnalysis:dateRange'

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

const tableRows = ref([])
const total = ref(0)
const fullRows = ref([])
const fullDataLoading = ref(false)
const lastFullQueryKey = ref('')
const FULL_DATA_PAGE_SIZE = 200
let pendingFullFetch = null

const pagination = reactive({
  page: 1,
  pageSize: 20
})

// 使用分页优化 Composable
const { pageSizeOptions, paginationLayout, pagerCount } = usePagination({
  desktopPageSizes: [20, 50, 100],
  mobilePageSizes: [20, 50]
})

const toSafeNumber = (value) => {
  const num = Number(value)
  return Number.isFinite(num) ? num : 0
}

const calcProfitRate = (profit, cost) => {
  if (!cost) return 0
  const ratio = profit / cost
  return Number.isFinite(ratio) ? ratio : 0
}

const calcGiftRate = (giftQty, salesQty) => {
  const total = giftQty + salesQty
  if (!total) return 0
  const ratio = giftQty / total
  return Number.isFinite(ratio) ? ratio : 0
}

const formatCurrency = (value) => {
  return `¥${toSafeNumber(value).toFixed(2)}`
}

const formatInteger = (value) => {
  return toSafeNumber(value)
}

const formatPercent = (value) => {
  return `${(toSafeNumber(value) * 100).toFixed(2)}%`
}

const formatAxisLabel = (value) => {
  const num = toSafeNumber(value)
  if (!Number.isFinite(num)) return '¥0'
  return `¥${num.toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  })}`
}

const formatDimensionLabel = (value) => {
  const label = value ?? '--'
  const text = typeof label === 'string' ? label : String(label)
  return text.length > 12 ? `${text.slice(0, 11)}…` : text
}

const normalizeCategoryLabel = (value) => {
  if (value === null || value === undefined) return '其他'
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length ? trimmed : '其他'
  }
  const stringified = String(value)
  return stringified.length ? stringified : '其他'
}

const mapRowToProduct = (item) => {
  const salesQty = toSafeNumber(item.sales_qty)
  const giftQty = toSafeNumber(item.gift_qty)
  const salesAmount = toSafeNumber(item.sales_amount)
  const giftAmount = toSafeNumber(item.gift_amount)
  const cost = toSafeNumber(item.cost ?? item.cost_total)
  const profit = toSafeNumber(item.profit)

  const profitRate = calcProfitRate(profit, cost)
  const giftRate = calcGiftRate(giftQty, salesQty)

  const category = normalizeCategoryLabel(
    item.category ??
      item.product_category ??
      item.dimension_category ??
      item.category_name
  )

  return {
    product_name: item.dimension_label || '未知商品',
    sales_qty: salesQty,
    sales_amount: salesAmount,
    gift_qty: giftQty,
    gift_amount: giftAmount,
    cost,
    profit,
    profit_rate: profitRate,
    gift_rate: giftRate,
    category
  }
}

const buildProductList = (rows = []) => {
  return rows
    .map(item => mapRowToProduct(item))
    .sort((a, b) => b.sales_amount - a.sales_amount)
}

const pagedProductData = computed(() => buildProductList(tableRows.value))
const fullProductData = computed(() => buildProductList(fullRows.value))

const baseProductData = computed(() => {
  return fullProductData.value.length ? fullProductData.value : pagedProductData.value
})

const exceptionProductData = computed(() => {
  return baseProductData.value.filter(item => {
    // 滞销预警：销量为 0 且有赠送（目前的 Fact 表局限性），或赠送率超过 30%
    const isStagnant = item.sales_qty === 0
    const isGiftAbnormal = item.gift_rate > 0.3
    return isStagnant || isGiftAbnormal
  })
})

const chartProductData = computed(() => {
  let data = showExceptionOnly.value ? exceptionProductData.value : baseProductData.value
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    data = data.filter(item => 
      item.product_name.toLowerCase().includes(kw) || 
      item.category.toLowerCase().includes(kw)
    )
  }
  return data
})

const tableProductData = computed(() => {
  const data = chartProductData.value
  const start = (pagination.page - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  
  if (showExceptionOnly.value || searchKeyword.value) {
    return data.slice(start, end)
  }
  return pagedProductData.value
})

const tableTotal = computed(() => {
  return chartProductData.value.length
})

const getTopData = (rows, key) => {
  return [...rows]
    .sort((a, b) => toSafeNumber(b[key]) - toSafeNumber(a[key]))
    .slice(0, 10)
    .reverse()
}

const topSalesData = computed(() => chartProductData.value.slice(0, 10).reverse())
const topProfitData = computed(() => getTopData(chartProductData.value, 'profit'))
const topGiftData = computed(() => getTopData(chartProductData.value, 'gift_amount'))

const categoryChartData = computed(() => {
  if (!chartProductData.value.length) return []
  const buckets = chartProductData.value.reduce((acc, item) => {
    const key = item.category || '其他'
    acc[key] = (acc[key] || 0) + toSafeNumber(item.sales_amount)
    return acc
  }, {})
  
  const sortedEntries = Object.entries(buckets)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  if (sortedEntries.length <= 10) {
    return sortedEntries
  }

  // 取前 10 名，其余合并为“其他品类”
  const top10 = sortedEntries.slice(0, 10)
  const othersValue = sortedEntries.slice(10).reduce((sum, item) => sum + item.value, 0)
  
  return [...top10, { name: '其他品类', value: othersValue }]
})

const salesChartRef = ref(null)
const profitChartRef = ref(null)
const giftChartRef = ref(null)
const categoryChartRef = ref(null)

const chartInstances = reactive({
  sales: null,
  profit: null,
  gift: null,
  category: null
})

const chartColorMap = {
  sales: '#409EFF',
  profit: '#67C23A',
  gift: '#E6A23C'
}

const chartRefMap = {
  sales: salesChartRef,
  profit: profitChartRef,
  gift: giftChartRef,
  category: categoryChartRef
}

const buildBarOption = (data, valueKey, color) => {
  if (!data.length) {
    return null
  }

  const names = data.map(item => item.product_name || '未知商品')
  const values = data.map(item => toSafeNumber(item[valueKey]))

  // 简化的金额格式化，防止x轴标签重叠
  const formatAxisLabelCompact = (value) => {
    const num = toSafeNumber(value)
    if (!Number.isFinite(num)) return '¥0'
    if (num >= 10000) {
      return '¥' + (num / 10000).toFixed(1) + '万'
    } else if (num >= 1000) {
      return '¥' + (num / 1000).toFixed(0) + 'K'
    } else {
      return '¥' + num.toFixed(0)
    }
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const first = Array.isArray(params) ? params[0] : params
        if (!first) return ''
        return `${first.name}<br/>${first.marker}${formatCurrency(first.value)}`
      }
    },
    grid: {
      top: 10,
      bottom: 30,
      left: 10,
      right: 20,
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLabel: {
        formatter: formatAxisLabelCompact,
        fontSize: 11,
        rotate: 0
      },
      splitLine: {
        lineStyle: { type: 'dashed' }
      }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: {
        formatter: formatDimensionLabel
      }
    },
    series: [
      {
        type: 'bar',
        data: values,
        barMaxWidth: 24,
        itemStyle: {
          color
        },
        label: {
          show: true,
          position: 'right',
          formatter: ({ value }) => formatCurrency(value)
        }
      }
    ]
  }
}

const buildCategoryPieOption = (data) => {
  if (!data.length) {
    return null
  }
  return {
    tooltip: {
      trigger: 'item',
      formatter: ({ name, value, percent }) => {
        const ratio = Number(percent)
        const percentText = Number.isFinite(ratio) ? `${ratio.toFixed(2)}%` : '--'
        return `${name}<br/>销售额：${formatCurrency(value)}<br/>占比：${percentText}`
      }
    },
    legend: {
      orient: 'vertical',
      right: 0,
      top: 'middle'
    },
    series: [
      {
        name: '品类销售占比',
        type: 'pie',
        roseType: 'radius',
        radius: ['35%', '65%'],
        center: ['40%', '50%'],
        data: data.map(item => ({
          name: item.name,
          value: toSafeNumber(item.value)
        })),
        emphasis: {
          scale: true,
          scaleSize: 8
        },
        label: {
          formatter: '{b}\n{d}%'
        }
      }
    ]
  }
}

const ensureChartInstance = (type) => {
  if (chartInstances[type]) {
    return chartInstances[type]
  }
  const el = chartRefMap[type]?.value
  if (!el) {
    return null
  }
  chartInstances[type] = echarts.init(el)
  
  // 添加点击联动
  chartInstances[type].on('click', (params) => {
    if (params.name) {
      searchKeyword.value = params.name
      pagination.page = 1
      handleSearch()
    }
  })
  
  return chartInstances[type]
}

const disposeChartInstance = (type) => {
  if (chartInstances[type]) {
    chartInstances[type].dispose()
    chartInstances[type] = null
  }
}

const disposeAllCharts = () => {
  disposeChartInstance('sales')
  disposeChartInstance('profit')
  disposeChartInstance('gift')
  disposeChartInstance('category')
}

const updateChart = (type, data, valueKey) => {
  const instance = ensureChartInstance(type)
  if (!instance) return
  if (!data.length) {
    instance.clear()
    return
  }
  const option = buildBarOption(data, valueKey, chartColorMap[type])
  if (option) {
    instance.setOption(option, true)
  }
}

const updateCategoryChart = (data) => {
  const instance = ensureChartInstance('category')
  if (!instance) return
  if (!data.length) {
    instance.clear()
    return
  }
  const option = buildCategoryPieOption(data)
  if (option) {
    instance.setOption(option, true)
  }
}

const updateAllCharts = () => {
  if (!chartProductData.value.length) {
    disposeAllCharts()
    return
  }
  updateChart('sales', topSalesData.value, 'sales_amount')
  updateChart('profit', topProfitData.value, 'profit')
  updateChart('gift', topGiftData.value, 'gift_amount')
  updateCategoryChart(categoryChartData.value)
}

const handleChartResize = () => {
  Object.values(chartInstances).forEach(instance => {
    instance?.resize()
  })
}

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
    const baseParams = buildBaseParams()
    if (!baseParams) {
      tableRows.value = []
      total.value = 0
      return
    }
    const response = await queryStats({
      ...baseParams,
      page: pagination.page,
      page_size: pagination.pageSize
    })

    if (response.success && response.data) {
      const rows = Array.isArray(response.data.rows) ? response.data.rows : []
      tableRows.value = rows
      const parsedTotal = Number(response.data.total)
      total.value = Number.isFinite(parsedTotal) ? parsedTotal : rows.length
    } else {
      tableRows.value = []
      total.value = 0
    }

    ensureFullDataset(baseParams)
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

watch(
  chartProductData,
  (rows) => {
    nextTick(() => {
      if (!rows.length) {
        disposeAllCharts()
        return
      }
      ensureChartInstance('sales')
      ensureChartInstance('profit')
      ensureChartInstance('gift')
      ensureChartInstance('category')
      updateAllCharts()
    })
  },
  { deep: true, immediate: true }
)

const scrollTableToTop = () => {
  nextTick(() => {
    if (tableRef.value?.setScrollTop) {
      tableRef.value.setScrollTop(0)
    }
  })
}

const parseStoreId = () => {
  if (currentStore.value && currentStore.value !== 'all') {
    const parsedStoreId = parseInt(currentStore.value, 10)
    if (Number.isFinite(parsedStoreId)) {
      return parsedStoreId
    }
  }
  return null
}

const buildBaseParams = () => {
  if (!dateRange.value || dateRange.value.length !== 2) {
    return null
  }
  const [startDate, endDate] = dateRange.value
  const baseParams = {
    table: 'sales',
    start_date: startDate,
    end_date: endDate,
    dimension: 'product',
    granularity: 'day'
  }
  const storeId = parseStoreId()
  if (storeId !== null) {
    baseParams.store_id = storeId
  }
  return baseParams
}

const buildFullQueryKey = (params) => {
  if (!params) return ''
  const storeKey = params.store_id ?? 'all'
  return `${params.start_date}|${params.end_date}|${storeKey}`
}

const ensureFullDataset = async (baseParams, force = false) => {
  if (!baseParams) return
  const queryKey = buildFullQueryKey(baseParams)
  const keyChanged = lastFullQueryKey.value !== queryKey
  if (!force && !keyChanged) {
    if (fullRows.value.length) {
      return
    }
    if (pendingFullFetch) {
      return pendingFullFetch
    }
  }
  lastFullQueryKey.value = queryKey
  if (force || keyChanged) {
    fullRows.value = []
  }
  fullDataLoading.value = true
  const fetchPromise = (async () => {
    const aggregated = []
    let page = 1
    try {
      while (true) {
        const resp = await queryStats({
          ...baseParams,
          page,
          page_size: FULL_DATA_PAGE_SIZE
        })
        if (!resp.success || !resp.data) {
          break
        }
        const rows = Array.isArray(resp.data.rows) ? resp.data.rows : []
        if (!rows.length) {
          break
        }
        aggregated.push(...rows)
        const totalCount = Number(resp.data.total)
        if (
          (Number.isFinite(totalCount) && aggregated.length >= totalCount) ||
          rows.length < FULL_DATA_PAGE_SIZE
        ) {
          break
        }
        page += 1
      }
      fullRows.value = aggregated
    } catch (error) {
      console.error('获取全量商品数据失败:', error)
      fullRows.value = aggregated
    } finally {
      fullDataLoading.value = false
      pendingFullFetch = null
    }
  })()
  pendingFullFetch = fetchPromise
  return fetchPromise
}

const handleExceptionToggle = async () => {
  pagination.page = 1
  if (showExceptionOnly.value) {
    const baseParams = buildBaseParams()
    await ensureFullDataset(baseParams)
  }
  scrollTableToTop()
}

const handleSearch = () => {
  pagination.page = 1
  scrollTableToTop()
}

const handlePageChange = async (page) => {
  if (showExceptionOnly.value) {
    pagination.page = page
    scrollTableToTop()
    return
  }
  pagination.page = page
  await fetchData()
  scrollTableToTop()
}

const handlePageSizeChange = async (size) => {
  if (showExceptionOnly.value) {
    pagination.pageSize = size
    pagination.page = 1
    scrollTableToTop()
    return
  }
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

const getRowClass = ({ row }) => {
  if (!row) return ''
  return row.gift_rate > 0.3 ? 'warning-row' : ''
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
  window.addEventListener('resize', handleChartResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleChartResize)
  disposeAllCharts()
})
</script>

<style lang="scss" scoped>
.product-analysis {
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

      :deep(.el-input) {
        width: 200px;
      }
    }

    .exception-switch {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .filter-label {
      font-size: 13px;
      color: #606266;
      white-space: nowrap;
    }
  }

  .search-input {
    width: 200px;
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

        :deep(.el-input) {
          flex: 1;
          min-width: 120px;
        }
      }

      .exception-switch {
        justify-content: flex-start;
      }
    }

    .filter-label {
      font-size: 12px;
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

    // 排行榜图表移动端优化
    .ranking-row,
    .category-structure {
      margin-bottom: 15px;

      .el-col {
        margin-bottom: 12px;
      }

      .chart-title {
        font-size: 14px;
      }

      .chart-wrapper {
        height: 250px;
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
      padding: 10px 12px;
    }

    :deep(.el-card__body) {
      padding: 10px;
    }

    .card-header {
      gap: 10px;

      .title-row {
        .title-text h2 {
          font-size: 15px;
        }
      }
    }

    .filters {
      gap: 10px;
    }

    // 排行榜图表小屏优化
    .ranking-row,
    .category-structure {
      margin-bottom: 12px;

      .el-col {
        margin-bottom: 10px;
      }

      :deep(.el-card__header) {
        padding: 10px 12px;
      }

      :deep(.el-card__body) {
        padding: 10px;
      }

      .chart-title {
        font-size: 13px;
      }

      .chart-wrapper {
        height: 220px;
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

  .exception-switch {
    min-width: 120px;
  }

  :deep(.warning-row) {
    background-color: rgba(245, 108, 108, 0.08);
  }

  :deep(.warning-row .cell) {
    color: #F56C6C;
    font-weight: 600;
  }

  .ranking-row,
  .category-structure {
    margin-bottom: 20px;

    .chart-card {
      height: 100%;
    }

    .chart-title {
      font-weight: 600;
      font-size: 15px;
    }

    .chart-wrapper {
      position: relative;
      height: 300px;
    }

    .chart-container {
      width: 100%;
      height: 100%;
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
  }
}
</style>

