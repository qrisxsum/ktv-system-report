<template>
  <div class="dashboard" v-loading="loading">
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
              <span>📈 营收趋势（近30天）</span>
            </div>
          </template>
          <div class="chart-container" ref="trendChartRef"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>🏪 门店排行 TOP5</span>
            </div>
          </template>
          <div class="chart-container" ref="storeChartRef"></div>
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
import { ref, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { getDashboardSummary } from '@/api/dashboard'

// 状态
const loading = ref(false)
const dashboardData = ref(null)

// KPI 数据 (从 API 响应计算)
const kpiList = computed(() => {
  const data = dashboardData.value
  if (!data) {
    return [
      { title: '昨日实收', value: '-', change: '-', trend: 'up', icon: 'Money', color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
      { title: '本月实收', value: '-', change: '-', trend: 'up', icon: 'TrendCharts', color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
      { title: '毛利率', value: '-', change: '-', trend: 'up', icon: 'PieChart', color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' },
      { title: '赠送率', value: '-', change: '-', trend: 'down', icon: 'Present', color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' }
    ]
  }
  
  return [
    { 
      title: '昨日实收', 
      value: formatCurrency(data.yesterday_actual), 
      change: formatPercent(data.yesterday_change), 
      trend: data.yesterday_change >= 0 ? 'up' : 'down',
      icon: 'Money', 
      color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
    },
    { 
      title: '本月实收', 
      value: formatCurrency(data.month_actual), 
      change: formatPercent(data.month_change), 
      trend: data.month_change >= 0 ? 'up' : 'down',
      icon: 'TrendCharts', 
      color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' 
    },
    { 
      title: '毛利率', 
      value: formatPercent(data.profit_rate), 
      change: `毛利 ${formatCurrency(data.month_profit)}`, 
      trend: 'up',
      icon: 'PieChart', 
      color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' 
    },
    { 
      title: '赠送率', 
      value: formatPercent(data.gift_rate), 
      change: '本月赠送', 
      trend: 'down',
      icon: 'Present', 
      color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' 
    }
  ]
})

// 格式化函数
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '-'
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

const formatPercent = (value) => {
  if (value === null || value === undefined) return '-'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(1)}%`
}

// 图表 ref
const trendChartRef = ref(null)
const storeChartRef = ref(null)
const staffChartRef = ref(null)
const productChartRef = ref(null)

let charts = []

// 初始化趋势图
const initTrendChart = (trendData) => {
  if (!trendChartRef.value) return
  
  const chart = echarts.init(trendChartRef.value)
  charts.push(chart)
  
  const dates = trendData.map(item => item.date.slice(5)) // MM-DD
  const values = trendData.map(item => (item.value / 10000).toFixed(2))
  
  chart.setOption({
    tooltip: { 
      trigger: 'axis',
      formatter: (params) => {
        const data = params[0]
        return `${data.name}<br/>营收: ¥${(data.value * 10000).toLocaleString()}`
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { interval: 4 }
    },
    yAxis: { type: 'value', name: '金额（万元）' },
    series: [{
      name: '营收',
      type: 'line',
      smooth: true,
      data: values,
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

// 初始化门店排行
const initStoreChart = (topStores) => {
  if (!storeChartRef.value) return
  
  const chart = echarts.init(storeChartRef.value)
  charts.push(chart)
  
  const names = topStores.map(item => item.name).reverse()
  const values = topStores.map(item => item.value).reverse()
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: names
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#f093fb' },
          { offset: 1, color: '#f5576c' }
        ])
      },
      label: { 
        show: true, 
        position: 'right', 
        formatter: (params) => `¥${(params.value / 10000).toFixed(1)}万`
      }
    }]
  })
}

// 初始化员工排行
const initStaffChart = (topEmployees) => {
  if (!staffChartRef.value) return
  
  const chart = echarts.init(staffChartRef.value)
  charts.push(chart)
  
  const names = topEmployees.map(item => item.name).reverse()
  const values = topEmployees.map(item => item.value).reverse()
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: names
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#667eea' },
          { offset: 1, color: '#764ba2' }
        ])
      },
      label: { 
        show: true, 
        position: 'right', 
        formatter: (params) => `¥${params.value.toLocaleString()}`
      }
    }]
  })
}

// 初始化商品排行
const initProductChart = (topProducts) => {
  if (!productChartRef.value) return
  
  const chart = echarts.init(productChartRef.value)
  charts.push(chart)
  
  const names = topProducts.map(item => item.name).reverse()
  const values = topProducts.map(item => item.value).reverse()
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '15%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: names
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#43e97b' },
          { offset: 1, color: '#38f9d7' }
        ])
      },
      label: { 
        show: true, 
        position: 'right', 
        formatter: (params) => `¥${params.value.toLocaleString()}`
      }
    }]
  })
}

// 加载数据
const loadDashboardData = async () => {
  loading.value = true
  
  try {
    const data = await getDashboardSummary()
    dashboardData.value = data
    
    // 初始化图表
    if (data.revenue_trend?.length) {
      initTrendChart(data.revenue_trend)
    }
    if (data.top_stores?.length) {
      initStoreChart(data.top_stores)
    }
    if (data.top_employees?.length) {
      initStaffChart(data.top_employees)
    }
    if (data.top_products?.length) {
      initProductChart(data.top_products)
    }
  } catch (error) {
    console.error('加载看板数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 窗口大小变化时重新调整图表
const handleResize = () => {
  charts.forEach(chart => chart.resize())
}

onMounted(() => {
  loadDashboardData()
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
