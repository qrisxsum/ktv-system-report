<template>
  <div class="dashboard">
    <!-- KPI 卡片 -->
    <el-row :gutter="20" class="kpi-cards">
      <el-col :span="6" v-for="kpi in kpiList" :key="kpi.title">
        <el-card class="kpi-card" :body-style="{ padding: '20px' }">
          <div class="kpi-icon" :style="{ background: kpi.color }">
            <el-icon size="24"><component :is="kpi.icon" /></el-icon>
          </div>
          <div class="kpi-content">
            <div class="kpi-title">{{ kpi.title }}</div>
            <div class="kpi-value">{{ kpi.value }}</div>
            <div class="kpi-change" :class="kpi.trend">
              <el-icon v-if="kpi.trend === 'up'"><Top /></el-icon>
              <el-icon v-else><Bottom /></el-icon>
              {{ kpi.change }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>📈 业绩趋势（最近6个月）</span>
            </div>
          </template>
          <div class="chart-container" ref="trendChartRef"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>🥧 收入构成</span>
            </div>
          </template>
          <div class="chart-container" ref="pieChartRef"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 排行榜 -->
    <el-row :gutter="20" class="rankings">
      <el-col :span="12">
        <el-card class="ranking-card">
          <template #header>
            <div class="card-header">
              <span>👑 员工业绩 TOP5</span>
            </div>
          </template>
          <div class="chart-container" ref="staffChartRef"></div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card class="ranking-card">
          <template #header>
            <div class="card-header">
              <span>🍺 热销商品 TOP5</span>
            </div>
          </template>
          <div class="chart-container" ref="productChartRef"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

// KPI 数据
const kpiList = ref([
  { title: '本月营收', value: '¥221,989', change: '+12.5%', trend: 'up', icon: 'Money', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { title: '环比增长', value: '+12.5%', change: '较上月', trend: 'up', icon: 'TrendCharts', color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
  { title: '毛利率', value: '42.5%', change: '+2.1%', trend: 'up', icon: 'PieChart', color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
  { title: '开台数', value: '255', change: '-3.2%', trend: 'down', icon: 'Microphone', color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' }
])

// 图表 ref
const trendChartRef = ref(null)
const pieChartRef = ref(null)
const staffChartRef = ref(null)
const productChartRef = ref(null)

let charts = []

// 初始化趋势图
const initTrendChart = () => {
  const chart = echarts.init(trendChartRef.value)
  charts.push(chart)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: ['7月', '8月', '9月', '10月', '11月', '12月']
    },
    yAxis: { type: 'value', name: '金额（万元）' },
    series: [{
      name: '营收',
      type: 'line',
      smooth: true,
      data: [15.2, 18.5, 16.8, 19.2, 20.1, 22.2],
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(102, 126, 234, 0.5)' },
          { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
        ])
      },
      lineStyle: { color: '#667eea', width: 3 }
    }]
  })
}

// 初始化饼图
const initPieChart = () => {
  const chart = echarts.init(pieChartRef.value)
  charts.push(chart)
  
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 45, name: '酒水', itemStyle: { color: '#667eea' } },
        { value: 30, name: '房费', itemStyle: { color: '#f5576c' } },
        { value: 25, name: '超市', itemStyle: { color: '#43e97b' } }
      ],
      label: { formatter: '{b}: {d}%' }
    }]
  })
}

// 初始化员工排行
const initStaffChart = () => {
  const chart = echarts.init(staffChartRef.value)
  charts.push(chart)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: ['饶慧', '小宗', '姚杰', '张伟', '常含'].reverse()
    },
    series: [{
      type: 'bar',
      data: [15161, 18043, 17850, 35510, 90889].reverse(),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#667eea' },
          { offset: 1, color: '#764ba2' }
        ])
      },
      label: { show: true, position: 'right', formatter: '¥{c}' }
    }]
  })
}

// 初始化商品排行
const initProductChart = () => {
  const chart = echarts.init(productChartRef.value)
  charts.push(chart)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: ['卤水花生', '什锦果盘', '喜力铝罐', '百岁山', '青岛崂山'].reverse()
    },
    series: [{
      type: 'bar',
      data: [10, 9, 3, 27, 320].reverse(),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#43e97b' },
          { offset: 1, color: '#38f9d7' }
        ])
      },
      label: { show: true, position: 'right' }
    }]
  })
}

// 窗口大小变化时重新调整图表
const handleResize = () => {
  charts.forEach(chart => chart.resize())
}

onMounted(() => {
  initTrendChart()
  initPieChart()
  initStaffChart()
  initProductChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach(chart => chart.dispose())
})
</script>

<style lang="scss" scoped>
.dashboard {
  .kpi-cards {
    margin-bottom: 20px;
  }
  
  .kpi-card {
    display: flex;
    align-items: center;
    
    :deep(.el-card__body) {
      display: flex;
      align-items: center;
      width: 100%;
    }
    
    .kpi-icon {
      width: 60px;
      height: 60px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      margin-right: 15px;
      flex-shrink: 0;
    }
    
    .kpi-content {
      flex: 1;
      
      .kpi-title {
        font-size: 14px;
        color: #909399;
        margin-bottom: 8px;
      }
      
      .kpi-value {
        font-size: 24px;
        font-weight: bold;
        color: #303133;
        margin-bottom: 5px;
      }
      
      .kpi-change {
        font-size: 13px;
        display: flex;
        align-items: center;
        gap: 3px;
        
        &.up { color: #67c23a; }
        &.down { color: #f56c6c; }
      }
    }
  }
  
  .charts, .rankings {
    margin-bottom: 20px;
  }
  
  .chart-card, .ranking-card {
    .card-header {
      font-weight: bold;
    }
    
    .chart-container {
      height: 300px;
    }
  }
}
</style>

