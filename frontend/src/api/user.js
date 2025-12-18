/**
 * 用户管理 API
 * 
 * 管理员管理店长账号的 API
 */

import request from './index'

/**
 * 创建店长账号
 * @param {Object} data - 店长信息
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 * @param {number} data.store_id - 门店ID
 * @param {string} [data.full_name] - 真实姓名
 * @param {string} [data.email] - 邮箱
 * @param {string} [data.phone] - 手机号
 * @returns {Promise} 创建结果
 */
export function createManager(data) {
  return request({
    url: '/users/managers',
    method: 'POST',
    data,
  })
}

/**
 * 获取店长列表
 * @param {Object} params - 查询参数
 * @param {number} [params.store_id] - 门店ID筛选
 * @param {boolean} [params.is_active] - 激活状态筛选
 * @param {string} [params.keyword] - 关键词搜索
 * @param {number} [params.skip] - 分页偏移
 * @param {number} [params.limit] - 每页数量
 * @returns {Promise} 店长列表
 */
export function listManagers(params = {}) {
  return request({
    url: '/users/managers',
    method: 'GET',
    params,
  })
}

/**
 * 获取店长详情
 * @param {number} userId - 用户ID
 * @returns {Promise} 店长详情
 */
export function getManager(userId) {
  return request({
    url: `/users/managers/${userId}`,
    method: 'GET',
  })
}

/**
 * 更新店长信息
 * @param {number} userId - 用户ID
 * @param {Object} data - 更新数据
 * @param {string} [data.password] - 新密码
 * @param {number} [data.store_id] - 门店ID
 * @param {string} [data.full_name] - 真实姓名
 * @param {string} [data.email] - 邮箱
 * @param {string} [data.phone] - 手机号
 * @returns {Promise} 更新结果
 */
export function updateManager(userId, data) {
  return request({
    url: `/users/managers/${userId}`,
    method: 'PUT',
    data,
  })
}

/**
 * 删除店长账号
 * @param {number} userId - 用户ID
 * @returns {Promise} 删除结果
 */
export function deleteManager(userId) {
  return request({
    url: `/users/managers/${userId}`,
    method: 'DELETE',
  })
}

/**
 * 切换店长账号状态
 * @param {number} userId - 用户ID
 * @returns {Promise} 操作结果
 */
export function toggleManagerStatus(userId) {
  return request({
    url: `/users/managers/${userId}/toggle-status`,
    method: 'POST',
  })
}

/**
 * 重置店长密码
 * @param {number} userId - 用户ID
 * @param {string} newPassword - 新密码
 * @returns {Promise} 操作结果
 */
export function resetManagerPassword(userId, newPassword) {
  return request({
    url: `/users/managers/${userId}/reset-password`,
    method: 'POST',
    data: {
      new_password: newPassword,
    },
  })
}

