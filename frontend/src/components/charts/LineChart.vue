<template>
  <div ref="chartRef" class="chart-container" :style="{ height: height }"></div>
</template>

<script setup>
/**
 * 通用折线图组件
 * 
 * 参考: docs/web界面5.md (2.2.1 节)
 * 
 * @example
 * <LineChart
 *   :data="[{ date: '2025-01', value: 1000 }, ...]"
 *   xField="date"
 *   yField="value"
 *   title="营收趋势"
 * />
 */

import { ref, watch, computed } from 'vue'
import * as echarts from 'echarts'
import { useChart, chartColors, createGradient } from './useChart'

const props = defineProps({
  // 数据源
  data: {
    type: Array,
    default: () => [],
  },
  // X 轴字段名
  xField: {
    type: String,
    default: 'date',
  },
  // Y 轴字段名 (支持多个，传数组则显示多条线)
  yField: {
    type: [String, Array],
    default: 'value',
  },
  // 图表标题
  title: {
    type: String,
    default: '',
  },
  // 图表高度
  height: {
    type: String,
    default: '300px',
  },
  // 是否显示面积
  showArea: {
    type: Boolean,
    default: true,
  },
  // 是否平滑曲线
  smooth: {
    type: Boolean,
    default: true,
  },
  // Y 轴单位
  yAxisUnit: {
    type: String,
    default: '',
  },
  // 数值格式化函数
  valueFormatter: {
    type: Function,
    default: null,
  },
  // 自定义颜色
  colors: {
    type: Array,
    default: () => [chartColors.primary, chartColors.success, chartColors.warning],
  },
})

const chartRef = ref(null)

// 生成图表配置
const getOption = () => {
  if (!props.data || props.data.length === 0) {
    return null
  }
  
  const xData = props.data.map(item => item[props.xField])
  const yFields = Array.isArray(props.yField) ? props.yField : [props.yField]
  
  const series = yFields.map((field, index) => {
    const color = props.colors[index % props.colors.length]
    
    return {
      name: field,
      type: 'line',
      smooth: props.smooth,
      data: props.data.map(item => item[field]),
      lineStyle: { 
        color, 
        width: 2,
      },
      itemStyle: { color },
      areaStyle: props.showArea ? {
        color: createGradient(
          echarts,
          `${color}80`,  // 50% 透明度
          `${color}10`,  // 6% 透明度
        ),
      } : null,
    }
  })
  
  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    } : null,
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        
        let result = `<strong>${params[0].axisValue}</strong><br/>`
        params.forEach(param => {
          const value = props.valueFormatter 
            ? props.valueFormatter(param.value) 
            : param.value.toLocaleString()
          result += `${param.marker} ${param.seriesName}: ${value}${props.yAxisUnit}<br/>`
        })
        return result
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: props.title ? '15%' : '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#E5E7EB' } },
      axisLabel: { color: '#6B7280' },
    },
    yAxis: {
      type: 'value',
      name: props.yAxisUnit,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#F3F4F6' } },
      axisLabel: { color: '#6B7280' },
    },
    series,
  }
}

const { updateChart } = useChart(chartRef, getOption)

// 监听数据变化，自动更新图表
watch(
  () => props.data,
  () => {
    updateChart(getOption())
  },
  { deep: true }
)
</script>

<style scoped>
.chart-container {
  width: 100%;
}
</style>
