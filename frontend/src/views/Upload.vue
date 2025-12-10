<template>
  <div class="upload-page">
    <el-row :gutter="20">
      <!-- 上传区域 -->
      <el-col :span="14">
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
          
          <!-- 解析结果预览 -->
          <div v-if="parseResult" class="parse-result">
            <el-divider content-position="left">解析结果</el-divider>
            
            <el-descriptions :column="2" border>
              <el-descriptions-item label="文件类型">
                <el-tag type="success">{{ parseResult.file_type_name }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="门店">
                {{ parseResult.store_name }}
              </el-descriptions-item>
              <el-descriptions-item label="数据月份">
                {{ parseResult.data_month }}
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
            />
            <el-alert
              v-else
              :title="parseResult.validation.errors.join(', ')"
              type="error"
              :closable="false"
              show-icon
              style="margin-top: 15px"
            />
            
            <!-- 数据预览表格 -->
            <div class="preview-table" v-if="parseResult.preview_rows?.length">
              <h4>数据预览（前5行）</h4>
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
              <el-button @click="resetUpload">取消</el-button>
              <el-button 
                type="primary" 
                @click="confirmUpload"
                :disabled="!parseResult.validation.is_valid"
                :loading="uploading"
              >
                确认入库
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 上传历史 -->
      <el-col :span="10">
        <el-card class="history-card">
          <template #header>
            <div class="card-header">
              <span>📋 最近上传记录</span>
            </div>
          </template>
          
          <el-table :data="uploadHistory" stripe>
            <el-table-column prop="created_at" label="时间" width="150">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="store_name" label="门店" width="100" />
            <el-table-column prop="file_type_name" label="类型" />
            <el-table-column prop="row_count" label="行数" width="70" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const parseResult = ref(null)
const uploading = ref(false)
const uploadHistory = ref([
  { id: 1, created_at: '2025-12-08 14:30:00', store_name: '万象城店', file_type_name: '包厢开台分析', row_count: 78, status: 'success' },
  { id: 2, created_at: '2025-12-08 14:28:00', store_name: '万象城店', file_type_name: '酒水销售分析', row_count: 34, status: 'success' },
  { id: 3, created_at: '2025-12-08 14:25:00', store_name: '青年路店', file_type_name: '预订汇总', row_count: 16, status: 'success' },
])

// 文件变化处理
const handleFileChange = async (file) => {
  // 模拟解析结果（实际应调用后端 API）
  parseResult.value = {
    file_type: 'room_analysis',
    file_type_name: '包厢开台分析表',
    store_name: '万象城店',
    store_id: 1,
    data_month: '2025-12',
    row_count: 78,
    preview_rows: [
      { room_name: 'K07', room_type: '电音中包', order_no: 'Z-KT25120200041', total_amount: 225 },
      { room_name: 'K11', room_type: '电音小包', order_no: 'Z-KT25120200040', total_amount: 193 },
      { room_name: 'K18', room_type: '电音小包', order_no: 'Z-KT25120200039', total_amount: 133 },
    ],
    validation: {
      is_valid: true,
      warnings: [],
      errors: []
    },
    session_id: 'uuid-xxx'
  }
  
  ElMessage.success(`文件 ${file.name} 解析成功`)
}

// 确认上传
const confirmUpload = async () => {
  uploading.value = true
  
  // 模拟上传（实际应调用后端 API）
  setTimeout(() => {
    uploading.value = false
    ElMessage.success(`成功导入 ${parseResult.value.row_count} 条数据`)
    
    // 添加到历史记录
    uploadHistory.value.unshift({
      id: Date.now(),
      created_at: new Date().toLocaleString(),
      store_name: parseResult.value.store_name,
      file_type_name: parseResult.value.file_type_name,
      row_count: parseResult.value.row_count,
      status: 'success'
    })
    
    parseResult.value = null
  }, 1500)
}

// 重置上传
const resetUpload = () => {
  parseResult.value = null
}

// 格式化时间
const formatTime = (time) => {
  return time
}
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
  }
}
</style>

