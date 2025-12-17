/**
 * API 请求封装
 * 
 * 参考: docs/web界面5.md (4.1 节 - /frontend/src/api)
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import NProgress from '@/utils/nprogress'

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 开启进度条
    NProgress.start()
    
    // 添加 token 认证信息
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    NProgress.done()
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 关闭进度条
    NProgress.done()
    
    const data = response.data
    
    // 如果返回的是文件流，直接返回
    if (response.config.responseType === 'blob') {
      return response
    }
    
    // 业务逻辑错误处理
    if (data.success === false) {
      ElMessage.error(data.message || '操作失败')
      return Promise.reject(new Error(data.message || '操作失败'))
    }
    
    return data
  },
  (error) => {
    // 关闭进度条
    NProgress.done()
    
    // HTTP 错误处理
    let message = '网络错误，请稍后重试'
    
    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      
      switch (status) {
        case 400:
          message = data.detail || '请求参数错误'
          break
        case 401:
          message = '未登录或登录已过期'
          // 清除本地存储的用户信息
          localStorage.removeItem('access_token')
          localStorage.removeItem('user')
          // 跳转到登录页
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
          break
        case 403:
          message = '没有权限访问'
          break
        case 404:
          message = data.detail || '请求的资源不存在'
          break
        case 409:
          // 409 冲突通常需要业务侧给出更明确的 UI（例如上传页阻止确认入库）
          // 这里不自动弹窗，避免“全局拦截器 + 页面 catch”重复提示
          return Promise.reject(error)
        case 500:
          message = '服务器内部错误'
          break
        default:
          message = data?.message || data?.detail || `请求失败 (${status})`
      }
    } else if (error.request) {
      message = '服务器无响应，请检查网络'
    }
    
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request

// 导出各模块 API
export * from './auth'
export * from './upload'
export * from './stats'
export * from './dashboard'
export * from './batch'
export * from './store'

