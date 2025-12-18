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
              <span>📈 营收趋势（按月显示）</span>
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
import { ref, onMounted, onUnmounted, computed, inject, watch } from 'vue'
import * as echarts from 'echarts'
import { getDashboardSummary } from '@/api/dashboard'

// 状态
const loading = ref(false)
const dashboardData = ref(null)

// 注入门店选择状态
const currentStore = inject('currentStore', ref(''))

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

  // 清理之前的图表实例
  const existingChart = echarts.getInstanceByDom(trendChartRef.value)
  if (existingChart) {
    existingChart.dispose()
    const index = charts.indexOf(existingChart)
    if (index > -1) {
      charts.splice(index, 1)
    }
  }

  const chart = echarts.init(trendChartRef.value)
  charts.push(chart)

  if (!trendData || trendData.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    })
    return
  }

  // 按月聚合（兼容后端返回日粒度或月粒度：YYYY-MM-DD / YYYY-MM）
  const monthKeyOf = (dateStr) => {
    if (!dateStr) return ''
    const s = String(dateStr)
    // e.g. 2025-12-01 -> 2025-12
    if (/^\d{4}-\d{2}/.test(s)) return s.slice(0, 7)
    return s
  }

  const monthMap = new Map()
  for (const item of trendData) {
    const key = monthKeyOf(item.date)
    const v = Number(item.value || 0)
    monthMap.set(key, (monthMap.get(key) || 0) + v)
  }

  const months = Array.from(monthMap.keys()).filter(Boolean).sort()
  const seriesData = months.map((m) => {
    const raw = monthMap.get(m) || 0
    return { value: Number((raw / 10000).toFixed(2)), raw }
  })

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const data = params[0]
        const raw = data?.data?.raw ?? data?.value * 10000
        return `${data.name}<br/>营收: ¥${Number(raw).toLocaleString()}`
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: months,
      axisLabel: {
        interval: 0,
        rotate: months.length > 12 ? 45 : 0
      }
    },
    yAxis: { type: 'value', name: '金额（万元）' },
    series: [{
      name: '营收',
      type: 'line',
      smooth: true,
      data: seriesData,
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

  // 清理之前的图表实例
  const existingChart = echarts.getInstanceByDom(storeChartRef.value)
  if (existingChart) {
    existingChart.dispose()
    const index = charts.indexOf(existingChart)
    if (index > -1) {
      charts.splice(index, 1)
    }
  }

  const chart = echarts.init(storeChartRef.value)
  charts.push(chart)

  if (!topStores || topStores.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    })
    return
  }

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

  // 清理之前的图表实例
  const existingChart = echarts.getInstanceByDom(staffChartRef.value)
  if (existingChart) {
    existingChart.dispose()
    const index = charts.indexOf(existingChart)
    if (index > -1) {
      charts.splice(index, 1)
    }
  }

  const chart = echarts.init(staffChartRef.value)
  charts.push(chart)

  if (!topEmployees || topEmployees.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    })
    return
  }

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

  // 清理之前的图表实例
  const existingChart = echarts.getInstanceByDom(productChartRef.value)
  if (existingChart) {
    existingChart.dispose()
    const index = charts.indexOf(existingChart)
    if (index > -1) {
      charts.splice(index, 1)
    }
  }

  const chart = echarts.init(productChartRef.value)
  charts.push(chart)

  if (!topProducts || topProducts.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 14
        }
      },
      xAxis: { show: false },
      yAxis: { show: false },
      series: []
    })
    return
  }

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
const loadDashboardData = async (storeId = null) => {
  loading.value = true

  try {
    // 转换门店ID：'all'表示全部门店，'1'表示万象城店，'2'表示青年路店
    const storeIdParam = storeId === 'all' ? null : (storeId ? parseInt(storeId) : null)
    const data = await getDashboardSummary(storeIdParam)
    dashboardData.value = data
    
    // 初始化图表 (无论是否有数据都要初始化，确保清空之前的图表)
    initTrendChart(data.revenue_trend || [])
    initStoreChart(data.top_stores || [])
    initStaffChart(data.top_employees || [])
    initProductChart(data.top_products || [])
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

// 监听门店选择变化
watch(currentStore, (newStoreId) => {
  console.log('Dashboard检测到门店变化:', newStoreId)
  loadDashboardData(newStoreId)
})

onMounted(() => {
  loadDashboardData(currentStore.value)
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
