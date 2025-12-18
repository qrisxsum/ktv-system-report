/**
 * 认证相关 API
 */

import axios from 'axios'

// 创建认证专用的 axios 实例
const authRequest = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
authRequest.interceptors.request.use(
  (config) => {
    // 开启进度条
    if (window.NProgress) window.NProgress.start()
    return config
  },
  (error) => {
    if (window.NProgress) window.NProgress.done()
    return Promise.reject(error)
  }
)

// 响应拦截器
authRequest.interceptors.response.use(
  (response) => {
    // 关闭进度条
    if (window.NProgress) window.NProgress.done()
    return response.data
  },
  (error) => {
    // 关闭进度条
    if (window.NProgress) window.NProgress.done()
    // 保留原始错误信息，让调用方可以获取详细的错误信息
    // 特别是登录时的账号停用错误（403）
    return Promise.reject(error)
  }
)

/**
 * 用户登录
 * @param {string} username - 用户名
 * @param {string} password - 密码
 * @returns {Promise} 登录结果
 */
export function login(username, password) {
  console.log('authRequest配置:', {
    baseURL: authRequest.defaults.baseURL,
    url: '/auth/login',
    method: 'post'
  })

  return authRequest({
    url: '/auth/login',
    method: 'post',
    data: {
      username,
      password
    }
  })
}

/**
 * 获取当前用户信息
 * @returns {Promise} 用户信息
 */
export function getCurrentUser() {
  return authRequest({
    url: '/auth/me',
    method: 'get'
  })
}

/**
 * 用户登出
 * @returns {Promise} 登出结果
 */
export function logout() {
  return authRequest({
    url: '/auth/logout',
    method: 'post'
  })
}

/**
 * 管理员强制登出指定用户
 * @param {number} userId - 用户ID
 * @returns {Promise} 操作结果
 */
export function forceLogoutUser(userId) {
  return authRequest({
    url: `/auth/admin/force-logout/${userId}`,
    method: 'post'
  })
}

/**
 * 管理员清理过期tokens
 * @returns {Promise} 操作结果
 */
export function cleanupExpiredTokens() {
  return authRequest({
    url: '/auth/admin/cleanup-expired-tokens',
    method: 'post'
  })
}
