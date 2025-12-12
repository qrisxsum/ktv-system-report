/**
 * ECharts 通用 Hook
 * 
 * 封装 ECharts 实例的创建、更新、销毁和响应式调整
 */

import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

/**
 * 使用 ECharts 图表
 * @param {Object} options - 配置选项
 * @param {Ref} options.chartRef - 图表容器 DOM 引用
 * @param {Object|Function} options.getOption - 图表配置或返回配置的函数
 * @returns {Object} { chart, updateChart, resizeChart }
 */
export function useChart(chartRef, getOption) {
  let chartInstance = null
  
  // 初始化图表
  const initChart = () => {
    if (!chartRef.value) return
    
    // 如果已存在实例，先销毁
    if (chartInstance) {
      chartInstance.dispose()
    }
    
    chartInstance = echarts.init(chartRef.value)
    
    const option = typeof getOption === 'function' ? getOption() : getOption
    if (option) {
      chartInstance.setOption(option)
    }
  }
  
  // 更新图表配置
  const updateChart = (newOption, notMerge = false) => {
    if (!chartInstance) {
      initChart()
    }
    if (chartInstance && newOption) {
      chartInstance.setOption(newOption, notMerge)
    }
  }
  
  // 调整图表大小
  const resizeChart = () => {
    if (chartInstance) {
      chartInstance.resize()
    }
  }
  
  // 监听窗口大小变化
  const handleResize = () => {
    resizeChart()
  }
  
  onMounted(() => {
    initChart()
    window.addEventListener('resize', handleResize)
  })
  
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    if (chartInstance) {
      chartInstance.dispose()
      chartInstance = null
    }
  })
  
  return {
    chart: chartInstance,
    updateChart,
    resizeChart,
    initChart,
  }
}

/**
 * 通用图表颜色主题
 */
export const chartColors = {
  primary: '#667eea',
  success: '#43e97b',
  warning: '#f5576c',
  info: '#4facfe',
  purple: '#764ba2',
  cyan: '#38f9d7',
  pink: '#f093fb',
  orange: '#fa709a',
}

/**
 * 生成渐变色
 */
export function createGradient(echarts, startColor, endColor, direction = 'vertical') {
  const coords = direction === 'vertical' 
    ? [0, 0, 0, 1] 
    : [0, 0, 1, 0]
  
  return new echarts.graphic.LinearGradient(...coords, [
    { offset: 0, color: startColor },
    { offset: 1, color: endColor },
  ])
}
