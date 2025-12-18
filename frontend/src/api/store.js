/**
 * 门店管理 API
 * 
 * 参考: docs/web界面5.md (1.4 节)
 */

import request from './index'

/**
 * 获取门店列表
 * @param {boolean} isActive - 是否只返回启用的门店 (可选)
 * @returns {Promise} 门店列表
 */
export function listStores(isActive = null) {
  return request({
    url: '/stores',
    method: 'GET',
    params: isActive !== null ? { is_active: isActive } : {},
  })
}

/**
 * 获取门店详情
 * @param {number} storeId - 门店ID
 * @returns {Promise} 门店详情
 */
export function getStore(storeId) {
  return request({
    url: `/stores/${storeId}`,
    method: 'GET',
  })
}

/**
 * 创建门店
 * @param {Object} data - 门店信息
 * @param {string} data.store_name - 门店名称
 * @param {string} [data.region] - 所属区域/城市
 * @param {string} [data.address] - 门店地址
 * @returns {Promise} 创建结果
 */
export function createStore(data) {
  return request({
    url: '/stores',
    method: 'POST',
    data,
  })
}

/**
 * 删除门店
 * @param {number} storeId - 门店ID
 * @returns {Promise} 删除结果
 */
export function deleteStore(storeId) {
  return request({
    url: `/stores/${storeId}`,
    method: 'DELETE',
  })
}

