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

