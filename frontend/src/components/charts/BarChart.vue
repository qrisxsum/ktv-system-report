<template>
  <div ref="chartRef" class="chart-container" :style="{ height: height }"></div>
</template>

<script setup>
/**
 * 通用柱状图组件
 * 
 * 参考: docs/web界面5.md (2.2.1 节)
 * 
 * @example
 * <BarChart
 *   :data="[{ name: '张三', value: 45000 }, ...]"
 *   nameField="name"
 *   valueField="value"
 *   title="员工业绩 TOP5"
 *   horizontal
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
  // 名称字段
  nameField: {
    type: String,
    default: 'name',
  },
  // 数值字段
  valueField: {
    type: String,
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
  // 是否水平显示（横向柱状图）
  horizontal: {
    type: Boolean,
    default: false,
  },
  // 是否显示数据标签
  showLabel: {
    type: Boolean,
    default: true,
  },
  // 数值格式化函数
  valueFormatter: {
    type: Function,
    default: null,
  },
  // 渐变起始颜色
  startColor: {
    type: String,
    default: chartColors.primary,
  },
  // 渐变结束颜色
  endColor: {
    type: String,
    default: chartColors.purple,
  },
  // 柱子圆角
  barRadius: {
    type: Number,
    default: 4,
  },
})

const chartRef = ref(null)

// 生成图表配置
const getOption = () => {
  if (!props.data || props.data.length === 0) {
    return null
  }
  
  const names = props.data.map(item => item[props.nameField])
  const values = props.data.map(item => item[props.valueField])
  
  // 根据方向确定坐标轴配置
  const categoryAxis = {
    type: 'category',
    data: props.horizontal ? names.slice().reverse() : names,
    axisLine: { lineStyle: { color: '#E5E7EB' } },
    axisLabel: { color: '#6B7280' },
    axisTick: { show: false },
  }
  
  const valueAxis = {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#F3F4F6' } },
    axisLabel: { color: '#6B7280' },
  }
  
  const labelFormatter = (params) => {
    const val = props.valueFormatter 
      ? props.valueFormatter(params.value)
      : params.value.toLocaleString()
    return val
  }
  
  return {
    title: props.title ? {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    } : null,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        if (!params || params.length === 0) return ''
        const param = params[0]
        const value = props.valueFormatter 
          ? props.valueFormatter(param.value) 
          : param.value.toLocaleString()
        return `<strong>${param.name}</strong><br/>${param.marker} ${value}`
      },
    },
    grid: {
      left: '3%',
      right: props.showLabel && props.horizontal ? '15%' : '4%',
      bottom: '3%',
      top: props.title ? '15%' : '10%',
      containLabel: true,
    },
    xAxis: props.horizontal ? valueAxis : categoryAxis,
    yAxis: props.horizontal ? categoryAxis : valueAxis,
    series: [{
      type: 'bar',
      data: props.horizontal ? values.slice().reverse() : values,
      barWidth: '60%',
      itemStyle: {
        borderRadius: props.horizontal 
          ? [0, props.barRadius, props.barRadius, 0]
          : [props.barRadius, props.barRadius, 0, 0],
        color: createGradient(
          echarts,
          props.startColor,
          props.endColor,
          props.horizontal ? 'horizontal' : 'vertical',
        ),
      },
      label: props.showLabel ? {
        show: true,
        position: props.horizontal ? 'right' : 'top',
        formatter: labelFormatter,
        color: '#6B7280',
      } : null,
    }],
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
