<template>
  <div class="upload-page">
    <el-row :gutter="20">
      <!-- 上传区域 -->
      <el-col :xs="24" :sm="24" :md="14" :lg="14">
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>📁 数据上传</span>
            </div>
          </template>
          
          <el-upload
            class="upload-dragger"
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :show-file-list="false"
            :disabled="parsing"
            accept=".csv,.xls,.xlsx"
          >
            <el-icon class="el-icon--upload" size="60"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .csv .xls .xlsx 格式，单个文件不超过 100MB
              </div>
            </template>
          </el-upload>
          
          <!-- 解析中状态 -->
          <div v-if="parsing" class="parsing-status">
            <el-icon class="is-loading" size="24"><Loading /></el-icon>
            <span>正在解析文件，请稍候...</span>
          </div>
          
          <!-- 解析结果预览 -->
          <div v-if="parseResult && !parsing" class="parse-result">
            <el-divider content-position="left">解析结果</el-divider>
            
            <el-descriptions :column="2" border>
              <el-descriptions-item label="文件类型">
                <el-tag type="success">{{ parseResult.file_type_name }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="门店">
                {{ parseResult.store_name }}
              </el-descriptions-item>
              <el-descriptions-item label="数据月份">
                {{ parseResult.data_month || '未识别' }}
              </el-descriptions-item>
              <el-descriptions-item label="数据行数">
                {{ parseResult.row_count }} 条
              </el-descriptions-item>
            </el-descriptions>
            
            <el-alert
              v-if="parseResult.validation.is_valid"
              title="校验通过"
              type="success"
              :closable="false"
              show-icon
              style="margin-top: 15px"
            >
              <template #default>
                <span>共 {{ parseResult.validation.summary.total_rows }} 行数据</span>
                <span v-if="parseResult.validation.summary.warning_rows > 0" style="margin-left: 10px; color: #e6a23c;">
                  ({{ parseResult.validation.summary.warning_rows }} 行警告)
                </span>
              </template>
            </el-alert>
            <el-alert
              v-else
              :title="`校验失败: ${parseResult.validation.summary.error_rows} 行错误`"
              type="error"
              :closable="false"
              show-icon
              style="margin-top: 15px"
            >
              <template #default>
                <div v-for="(error, index) in parseResult.validation.errors.slice(0, 3)" :key="index">
                  行 {{ error.row_index }}: {{ error.message }}
                </div>
                <div v-if="parseResult.validation.errors.length > 3">
                  ... 还有 {{ parseResult.validation.errors.length - 3 }} 个错误
                </div>
              </template>
            </el-alert>
            <el-alert
              v-if="duplicateWarning"
              :title="duplicateWarning"
              type="warning"
              :closable="false"
              show-icon
              style="margin-top: 15px"
            />
            
            <!-- 数据预览表格 -->
            <div class="preview-table" v-if="parseResult.preview_rows?.length">
              <h4>数据预览（前{{ parseResult.preview_rows.length }}行）</h4>
              <el-table :data="parseResult.preview_rows" border stripe max-height="200">
                <el-table-column
                  v-for="(value, key) in parseResult.preview_rows[0]"
                  :key="key"
                  :prop="key"
                  :label="key"
                  min-width="120"
                />
              </el-table>
            </div>
            
            <div class="action-buttons">
              <el-button @click="resetUpload" :disabled="uploading">取消</el-button>
              <el-button 
                type="primary" 
                @click="confirmUpload"
                :disabled="!parseResult.validation.is_valid || !!duplicateWarning"
                :loading="uploading"
              >
                确认入库
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 上传历史 -->
      <el-col :xs="24" :sm="24" :md="10" :lg="10">
        <el-card class="history-card">
          <template #header>
            <div class="card-header">
              <span>📋 最近上传记录</span>
              <el-button link type="primary" @click="refreshHistory">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          
          <el-table :data="uploadHistory" stripe v-loading="loadingHistory">
            <el-table-column prop="created_at" label="时间" width="150">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="store_name" label="门店" width="100" />
            <el-table-column prop="table_type_name" label="类型" />
            <el-table-column prop="row_count" label="行数" width="70" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ row }">
                <el-popconfirm
                  title="确定要删除这个批次吗？数据将被回滚。"
                  @confirm="handleDeleteBatch(row.id)"
                >
                  <template #reference>
                    <el-button link type="danger" size="small">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, inject, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { parseFile, confirmImport, cancelUpload } from '@/api/upload'
import { listBatches, deleteBatch } from '@/api/batch'

// 状态
const parseResult = ref(null)
const parsing = ref(false)
const uploading = ref(false)
const duplicateWarning = ref('')
const uploadHistory = ref([])
const loadingHistory = ref(false)

// 注入门店选择状态和事件发射器
const currentStore = inject('currentStore', ref('all'))
const eventEmitter = inject('eventEmitter', null)

// 状态映射
const STATUS_MAP = {
  pending: { type: 'warning', text: '处理中' },
  success: { type: 'success', text: '成功' },
  failed: { type: 'danger', text: '失败' },
  warning: { type: 'warning', text: '有警告' },
}

const getStatusType = (status) => STATUS_MAP[status]?.type || 'info'
const getStatusText = (status) => STATUS_MAP[status]?.text || status

// 监听门店变化，自动刷新上传历史
watch(currentStore, (newStore) => {
  console.log('Upload页面检测到门店变化:', newStore)
  refreshHistory()
})

// 文件变化处理
const handleFileChange = async (file) => {
  parsing.value = true
  parseResult.value = null
  duplicateWarning.value = ''
  
  try {
    const response = await parseFile(file.raw)
    
    if (response.success && response.data) {
      parseResult.value = response.data
      duplicateWarning.value = ''
      ElMessage.success(`文件 ${file.name} 解析成功`)
    } else {
      ElMessage.error(response.message || '文件解析失败')
    }
  } catch (error) {
    console.error('解析失败:', error)
    if (error?.response?.status === 409) {
      const message = error.response?.data?.message || '检测到重复文件，请勿重复上传'
      // 解析阶段无预览区域可展示告警，直接给出清晰提示即可
      ElMessage.warning(message)
    } else if (!error?.response) {
      // 只有在无 HTTP 响应（网络/跨域等）时，页面兜底提示；有响应的情况交给全局拦截器
      ElMessage.error('文件解析失败，请检查文件格式')
    }
  } finally {
    parsing.value = false
  }
}

// 确认上传
const confirmUpload = async () => {
  if (!parseResult.value?.session_id) {
    ElMessage.error('会话已过期，请重新上传文件')
    return
  }
  
  uploading.value = true
  
  try {
    duplicateWarning.value = ''
    const response = await confirmImport(parseResult.value.session_id)
    
    if (response.success) {
      // 先保存入库信息，再清空 parseResult
      const importedStoreId = parseResult.value?.store_id
      const importedStoreName = parseResult.value?.store_name
      const rowCount = parseResult.value?.row_count || response.data?.summary?.row_count || 0
      
      ElMessage.success(response.message || `成功导入 ${rowCount} 条数据`)
      
      parseResult.value = null
      duplicateWarning.value = ''
      
      // 刷新上传历史
      await refreshHistory()
      
      // 触发文件入库事件，通知 MainLayout 更新门店选择器
      if (eventEmitter) {
        eventEmitter.emit('file-imported', {
          store_id: importedStoreId,
          store_name: importedStoreName,
          row_count: rowCount
        })
      }
    } else {
      ElMessage.error(response.message || '入库失败')
    }
  } catch (error) {
    console.error('入库失败:', error)
    if (error?.response?.status === 409) {
      const message = error.response?.data?.message || '检测到重复文件，请勿重复入库'
      duplicateWarning.value = message
    } else {
      duplicateWarning.value = ''
      // 有 HTTP 响应的情况交给全局拦截器提示；仅在无响应时兜底
      if (!error?.response) {
        ElMessage.error('入库失败，请稍后重试')
      }
    }
  } finally {
    uploading.value = false
  }
}

// 重置上传
const resetUpload = async () => {
  if (parseResult.value?.session_id) {
    try {
      await cancelUpload(parseResult.value.session_id)
    } catch (error) {
      console.error('取消上传失败:', error)
    }
  }
  parseResult.value = null
  duplicateWarning.value = ''
}

// 刷新上传历史
const refreshHistory = async () => {
  loadingHistory.value = true

  try {
    // 根据当前门店选择构建查询参数
    const params = { page: 1, page_size: 10 }

    // 转换门店ID：'all'表示全部门店，数字表示具体门店
    if (currentStore.value && currentStore.value !== 'all') {
      const parsedStoreId = parseInt(currentStore.value)
      if (!isNaN(parsedStoreId)) {
        params.store_id = parsedStoreId
      }
    }

    const response = await listBatches(params)

    if (response.success) {
      uploadHistory.value = response.data || []
    }
  } catch (error) {
    console.error('获取上传历史失败:', error)
  } finally {
    loadingHistory.value = false
  }
}

// 删除批次
const handleDeleteBatch = async (batchId) => {
  try {
    const response = await deleteBatch(batchId)
    
    if (response.success) {
      ElMessage.success(response.message || '删除成功')
      await refreshHistory()
    } else {
      ElMessage.error(response.message || '删除失败')
    }
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败，请稍后重试')
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  
  try {
    const date = new Date(time)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
  return time
}
}

// 组件挂载时加载数据
onMounted(() => {
  refreshHistory()
})
</script>

<style lang="scss" scoped>
.upload-page {
  .upload-card {
    .upload-dragger {
      width: 100%;
      
      :deep(.el-upload-dragger) {
        width: 100%;
        height: 200px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
      }
    }
    
    .parsing-status {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      color: #409eff;
      
      span {
        margin-left: 10px;
      }
    }
    
    .parse-result {
      margin-top: 20px;
      
      .preview-table {
        margin-top: 15px;
        
        h4 {
          margin-bottom: 10px;
          color: #606266;
        }
      }
      
      .action-buttons {
        margin-top: 20px;
        text-align: right;
      }
    }
  }
  
  .history-card {
    height: 100%;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  // 移动端优化
  @media (max-width: 768px) {
    :deep(.el-row) {
      .el-col {
        margin-bottom: 15px;
      }
    }

    .upload-card {
      .upload-dragger {
        :deep(.el-upload-dragger) {
          height: 180px;
        }

        :deep(.el-icon--upload) {
          font-size: 50px !important;
        }

        :deep(.el-upload__text) {
          font-size: 14px;
        }

        :deep(.el-upload__tip) {
          font-size: 12px;
        }
      }

      .parse-result {
        :deep(.el-descriptions) {
          .el-descriptions__label {
            font-size: 13px;
          }

          .el-descriptions__content {
            font-size: 13px;
          }
        }

        .preview-table {
          overflow-x: auto;

          h4 {
            font-size: 14px;
          }

          :deep(.el-table) {
            font-size: 12px;
          }
        }

        .action-buttons {
          text-align: center;

          .el-button {
            width: 48%;
          }
        }
      }
    }

    .history-card {
      :deep(.el-table) {
        font-size: 12px;

        .el-table__header th,
        .el-table__body td {
          padding: 8px 5px;
        }
      }
    }
  }

  @media (max-width: 480px) {
    .upload-card {
      .upload-dragger {
        :deep(.el-upload-dragger) {
          height: 160px;
        }

        :deep(.el-icon--upload) {
          font-size: 45px !important;
        }

        :deep(.el-upload__text) {
          font-size: 13px;
          padding: 0 10px;
        }
      }

      .parse-result {
        :deep(.el-descriptions) {
          font-size: 12px;
        }

        :deep(.el-alert) {
          font-size: 12px;
          padding: 8px 12px;
        }

        .action-buttons {
          .el-button {
            width: 100%;
            margin-top: 8px;
            margin-left: 0 !important;
          }
        }
      }
    }

    .history-card {
      .card-header {
        flex-wrap: wrap;
        gap: 10px;
      }

      :deep(.el-table) {
        .el-table__header th,
        .el-table__body td {
          padding: 6px 3px;
          font-size: 11px;
        }
      }
    }
  }
}
</style>
