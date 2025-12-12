/**
 * 批次管理 API
 * 
 * 参考: docs/web界面5.md (1.2 节, 2.2.4 节)
 */

import request from './index'

/**
 * 获取批次列表
 * @param {Object} params - 查询参数
 * @param {number} params.store_id - 门店ID (可选)
 * @param {string} params.table_type - 表类型 (可选)
 * @param {string} params.status - 状态 (可选)
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页数量
 * @returns {Promise} 批次列表
 */
export function listBatches(params = {}) {
  return request({
    url: '/batches',
    method: 'GET',
    params,
  })
}

/**
 * 获取批次详情
 * @param {number} batchId - 批次ID
 * @returns {Promise} 批次详情
 */
export function getBatchDetail(batchId) {
  return request({
    url: `/batches/${batchId}`,
    method: 'GET',
  })
}

/**
 * 删除批次 (回滚数据)
 * @param {number} batchId - 批次ID
 * @returns {Promise} 删除结果
 */
export function deleteBatch(batchId) {
  return request({
    url: `/batches/${batchId}`,
    method: 'DELETE',
  })
}

