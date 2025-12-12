/**
 * 文件上传 API
 * 
 * 参考: docs/web界面5.md (1.2 节)
 */

import request from './index'

/**
 * 解析上传文件
 * @param {File} file - 要上传的文件
 * @param {number} storeId - 门店ID (可选)
 * @returns {Promise} 解析结果
 */
export function parseFile(file, storeId = null) {
  const formData = new FormData()
  formData.append('file', file)
  if (storeId) {
    formData.append('store_id', storeId)
  }
  
  return request({
    url: '/upload/parse',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

/**
 * 确认入库
 * @param {string} sessionId - 解析会话ID
 * @returns {Promise} 入库结果
 */
export function confirmImport(sessionId) {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  
  return request({
    url: '/upload/confirm',
    method: 'POST',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

/**
 * 取消上传
 * @param {string} sessionId - 解析会话ID
 * @returns {Promise}
 */
export function cancelUpload(sessionId) {
  return request({
    url: `/upload/cancel/${sessionId}`,
    method: 'DELETE',
  })
}

