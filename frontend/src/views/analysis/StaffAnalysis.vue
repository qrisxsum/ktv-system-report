<template>
  <div class="staff-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>👑 人员风云榜</span>
          <div class="filter-group">
            <el-radio-group v-model="roleFilter" size="small">
              <el-radio-button label="">全部</el-radio-button>
              <el-radio-button label="销售经理">销售经理</el-radio-button>
              <el-radio-button label="服务员">服务员</el-radio-button>
              <el-radio-button label="收银员">收银员</el-radio-button>
            </el-radio-group>
          </div>
        </div>
      </template>
      
      <div class="chart-container" ref="chartRef"></div>
      
      <el-table :data="staffData" stripe border style="margin-top: 20px">
        <el-table-column type="index" label="排名" width="70" align="center" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department" label="部门" width="100" />
        <el-table-column prop="booking_count" label="订台数" width="100" align="right" />
        <el-table-column prop="sales_amount" label="销售金额" width="120" align="right">
          <template #default="{ row }">
            ¥{{ row.sales_amount.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="base_performance" label="基本业绩" width="120" align="right">
          <template #default="{ row }">
            ¥{{ row.base_performance.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="received_amount" label="实收金额" align="right">
          <template #default="{ row }">
            ¥{{ row.received_amount.toLocaleString() }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const roleFilter = ref('')
const chartRef = ref(null)
let chart = null

const staffData = ref([
  { name: '常含', department: '收银员', booking_count: 93, sales_amount: 90889, base_performance: 66934, received_amount: 90889 },
  { name: '张伟青年路', department: '服务员', booking_count: 36, sales_amount: 35509.93, base_performance: 20246.93, received_amount: 35509.93 },
  { name: '姚杰', department: '销售经理', booking_count: 25, sales_amount: 17850, base_performance: 12106, received_amount: 17850 },
  { name: '小宗', department: '服务员', booking_count: 7, sales_amount: 18043, base_performance: 16667, received_amount: 18043 },
  { name: '饶慧', department: '服务员', booking_count: 21, sales_amount: 15161, base_performance: 8037, received_amount: 15161 },
  { name: '黄怡芳', department: '销售经理', booking_count: 10, sales_amount: 9309, base_performance: 7063, received_amount: 9309 },
  { name: '李雪', department: '收银员', booking_count: 20, sales_amount: 5835, base_performance: 3748, received_amount: 5835 },
])

const initChart = () => {
  chart = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  const data = staffData.value
    .slice(0, 10)
    .map(item => ({ name: item.name, value: item.sales_amount }))
    .reverse()
  
  chart.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}: ¥{c}' },
    grid: { left: '15%', right: '15%' },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: data.map(d => d.name)
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
        formatter: '¥{c}'
      }
    }]
  })
}

const handleResize = () => chart?.resize()

onMounted(() => {
  initChart()
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
}
</style>

