<template>
  <div class="room-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>🎤 包厢效能分析</span>
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
      
      <el-table :data="roomData" stripe border style="margin-top: 20px" v-loading="loading">
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
      
      <div v-if="!roomData.length && !loading" class="empty-hint">
        暂无数据，请先上传包厢消费数据
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

// 汇总统计
const summary = computed(() => {
  const totalOrders = rawData.value.reduce((sum, item) => sum + (item.order_count || 0), 0)
  const totalGmv = rawData.value.reduce((sum, item) => sum + (item.gmv || 0), 0)
  const totalActual = rawData.value.reduce((sum, item) => sum + (item.actual || 0), 0)
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
  return rawData.value.map(item => ({
    room_name: item.dimension_label || '未知包厢',
    order_count: item.order_count || 0,
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
    
    const response = await queryStats({
      table: 'room',
      start_date: startDate,
      end_date: endDate,
      dimension: 'room',
      granularity: 'day'
    })
    
    if (response.success && response.data) {
      rawData.value = response.data
    } else {
      rawData.value = []
    }
  } catch (error) {
    console.error('获取包厢分析数据失败:', error)
    ElMessage.error('获取包厢分析数据失败')
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
.room-analysis {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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
  
  .empty-hint {
    text-align: center;
    padding: 40px 0;
    color: #999;
  }
}
</style>

