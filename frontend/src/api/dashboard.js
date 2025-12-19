/**
 * 仪表盘 API
 * 
 * 参考: docs/web界面5.md (1.3 节, 2.2.1 节)
 */

import request from './index'

/**
 * 获取首页看板汇总数据
 * @param {number} storeId - 门店ID (可选，不传则汇总所有门店)
 * @returns {Promise} 看板数据
 */
export function getDashboardSummary(storeId = null, targetDate = null) {
  const params = {}
  if (storeId) {
    params.store_id = storeId
  }
  if (targetDate) {
    params.target_date = targetDate
  }

  return request({
    url: '/dashboard/summary',
    method: 'GET',
    params,
  })
}

/**
 * 获取 KPI 指标卡片数据
 * @param {Object} params - 查询参数
 * @param {number} params.store_id - 门店ID (可选)
 * @param {string} params.start_date - 开始日期 (可选)
 * @param {string} params.end_date - 结束日期 (可选)
 * @returns {Promise} KPI 数据
 */
export function getKpiCards(params = {}) {
  return request({
    url: '/dashboard/kpi',
    method: 'GET',
    params,
  })
}

/**
 * 获取趋势数据
 * @param {Object} params - 查询参数
 * @param {string} params.metric - 指标: actual/sales/profit/orders
 * @param {number} params.days - 天数 (7-90)
 * @param {number} params.store_id - 门店ID (可选)
 * @returns {Promise} 趋势数据
 */
export function getTrendData(params = {}) {
  return request({
    url: '/dashboard/trend',
    method: 'GET',
    params: {
      metric: 'actual',
      days: 30,
      ...params,
    },
  })
}

/**
 * 获取排行榜数据
 * @param {Object} params - 查询参数
 * @param {string} params.dimension - 维度: store/employee/product/room
 * @param {string} params.metric - 指标: actual/sales/profit/qty
 * @param {number} params.limit - 返回数量 (5-50)
 * @param {number} params.store_id - 门店ID (可选)
 * @returns {Promise} 排行榜数据
 */
export function getRankingData(params = {}) {
  return request({
    url: '/dashboard/ranking',
    method: 'GET',
    params: {
      dimension: 'store',
      metric: 'actual',
      limit: 10,
      ...params,
    },
  })
}
