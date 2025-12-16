<template>
  <div class="product-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>🍺 商品销售分析</span>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            @change="fetchData"
          />
        </div>
      </template>
      
      <el-table :data="productData" stripe border v-loading="loading">
        <el-table-column prop="product_name" label="商品名称" width="200" />
        <el-table-column prop="sales_qty" label="销售数量" width="120" align="right">
          <template #default="{ row }">
            {{ row.sales_qty || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="sales_amount" label="销售金额" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.sales_amount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_qty" label="赠送数量" width="120" align="right">
          <template #default="{ row }">
            {{ row.gift_qty || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="gift_amount" label="赠送金额" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.gift_amount || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.cost || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit" label="利润" width="140" align="right">
          <template #default="{ row }">
            ¥{{ (row.profit || 0).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" label="利润率" align="right">
          <template #default="{ row }">
            {{ row.profit_rate ? row.profit_rate.toFixed(2) : '0.00' }}%
          </template>
        </el-table-column>
      </el-table>
      
      <div v-if="!productData.length && !loading" class="empty-hint">
        暂无数据，请先上传商品销售数据
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { queryStats, getDateRange } from '@/api/stats'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const dateRange = ref([])
const rawData = ref([])

// 处理后的商品数据
const productData = computed(() => {
  return rawData.value.map(item => {
    const salesAmount = item.sales_amount || 0
    const cost = item.cost || 0
    const profit = item.profit || 0
    const profitRate = salesAmount > 0 ? (profit / salesAmount * 100) : 0
    
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
    
    const response = await queryStats({
      table: 'sales',
      start_date: startDate,
      end_date: endDate,
      dimension: 'product',
      granularity: 'day'
    })
    
    if (response.success && response.data) {
      rawData.value = response.data
    } else {
      rawData.value = []
    }
  } catch (error) {
    console.error('获取商品分析数据失败:', error)
    ElMessage.error('获取商品分析数据失败')
    rawData.value = []
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await initDateRange()
  await fetchData()
})
</script>

<style lang="scss" scoped>
.product-analysis {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .empty-hint {
    text-align: center;
    padding: 40px 0;
    color: #999;
  }
}
</style>

