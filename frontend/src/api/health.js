/**
 * 数据健康度 API
 */

import request from './index'

/**
 * 获取数据完整度
 * @param {Object} params - 查询参数
 * @param {number} params.store_id - 门店ID（可选）
 * @param {string} params.data_month - 数据月份（YYYY-MM格式，可选）
 * @param {string} params.report_types - 报表类型（逗号分隔，如：booking,room,sales，可选）
 * @returns {Promise} 数据完整度信息
 */
export function getDataCoverage(params = {}) {
  return request({
    url: '/health/coverage',
    method: 'GET',
    params,
  })
}


