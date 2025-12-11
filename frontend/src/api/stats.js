/**
 * 数据统计 API
 * 
 * 参考: docs/web界面5.md (1.3 节)
 */

import request from './index'

/**
 * 通用数据查询
 * @param {Object} params - 查询参数
 * @param {string} params.table - 表类型: booking | room | sales
 * @param {string} params.start_date - 开始日期 (YYYY-MM-DD)
 * @param {string} params.end_date - 结束日期 (YYYY-MM-DD)
 * @param {number} params.store_id - 门店ID (可选)
 * @param {string} params.dimension - 聚合维度: date | store | employee | product | room | room_type
 * @param {string} params.granularity - 时间粒度: day | week | month
 * @returns {Promise} 统计结果
 */
export function queryStats(params) {
  return request({
    url: '/stats/query',
    method: 'GET',
    params,
  })
}

/**
 * 获取首页看板数据
 * @param {number} storeId - 门店ID (可选，不传则汇总所有门店)
 * @returns {Promise} 看板数据
 */
export function getDashboardSummary(storeId = null) {
  return request({
    url: '/stats/dashboard/summary',
    method: 'GET',
    params: storeId ? { store_id: storeId } : {},
  })
}

