/**
 * 设计系统变量映射
 * 将SCSS变量映射到JavaScript，供图表等组件使用
 */

// 品牌色
export const brandColors = {
  primary: '#409EFF',
  success: '#67C23A',
  warning: '#E6A23C',
  danger: '#F56C6C',
  info: '#909399',
}

// 文字颜色
export const textColors = {
  primary: '#303133',
  regular: '#606266',
  secondary: '#909399',
  placeholder: '#C0C4CC',
}

// 背景颜色
export const bgColors = {
  primary: '#FFFFFF',
  secondary: '#F5F7FA',
  tertiary: '#FAFAFA',
}

// 边框颜色
export const borderColors = {
  base: '#DCDFE6',
  light: '#EBEEF5',
  lighter: '#F2F6FC',
}

// 间距系统（基于8px网格）
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
}

// 透明度辅助函数
export const withOpacity = (color, opacity) => {
  // 将hex颜色转换为rgba
  const hex = color.replace('#', '')
  const r = parseInt(hex.substring(0, 2), 16)
  const g = parseInt(hex.substring(2, 4), 16)
  const b = parseInt(hex.substring(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${opacity})`
}

// 图表专用颜色配置
export const chartColors = {
  primary: brandColors.primary,
  primaryLight: '#66B1FF', // 可以后续添加到variables.scss
  textPrimary: textColors.primary,
  textRegular: textColors.regular,
  textSecondary: textColors.secondary,
  borderBase: borderColors.base,
  borderLight: borderColors.light,
  borderLighter: borderColors.lighter,
  bgPrimary: bgColors.primary,
  bgSecondary: bgColors.secondary,
  success: brandColors.success,
  danger: brandColors.danger,
  // 透明度颜色
  primaryLight10: withOpacity(brandColors.primary, 0.1),
  primaryLight40: withOpacity(brandColors.primary, 0.4),
  successLight10: withOpacity(brandColors.success, 0.1),
  warningLight10: withOpacity(brandColors.warning, 0.1),
  infoLight10: withOpacity(brandColors.info, 0.1),
  shadowColor: 'rgba(0, 0, 0, 0.15)',
}

export default {
  brandColors,
  textColors,
  bgColors,
  borderColors,
  spacing,
  chartColors,
  withOpacity,
}

