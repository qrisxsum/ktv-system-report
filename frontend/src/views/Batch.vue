<template>
  <div class="batch-page">
    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="当前门店筛选">
          <el-tag type="info" size="large">
            {{ getCurrentStoreName() }}
          </el-tag>
        </el-form-item>

        <el-form-item label="表类型">
          <el-select v-model="filters.table_type" placeholder="全部类型" clearable style="width: 150px">
            <el-option label="预订汇总" value="booking" />
            <el-option label="包厢开台" value="room" />
            <el-option label="酒水销售" value="sales" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="处理中" value="pending" />
            <el-option label="有警告" value="warning" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="loadBatches">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 批次列表 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>📋 批次列表</span>
          <span class="total-count">共 {{ total }} 条记录</span>
        </div>
      </template>
      
      <el-table
        :data="batches"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="batch_no" label="批次编号" min-width="200" show-overflow-tooltip />
        <el-table-column prop="file_name" label="文件名" min-width="250" show-overflow-tooltip />
        <el-table-column prop="store_name" label="门店" width="120" />
        <el-table-column prop="table_type_name" label="表类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTableTypeTag(row.table_type)" size="small">
              {{ row.table_type_name || getTableTypeName(row.table_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="row_count" label="行数" width="80" align="center" />
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">
              <el-icon><View /></el-icon> 详情
            </el-button>
            <el-popconfirm
              title="确定要删除这个批次吗？相关数据将被回滚。"
              confirm-button-text="确定删除"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button link type="danger" size="small">
                  <el-icon><Delete /></el-icon> 删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadBatches"
          @current-change="loadBatches"
        />
      </div>
    </el-card>
    
    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="批次详情"
      width="600px"
      destroy-on-close
    >
      <el-descriptions :column="2" border v-if="currentBatch">
        <el-descriptions-item label="批次ID">{{ currentBatch.id }}</el-descriptions-item>
        <el-descriptions-item label="批次编号">{{ currentBatch.batch_no }}</el-descriptions-item>
        <el-descriptions-item label="文件名" :span="2">{{ currentBatch.file_name }}</el-descriptions-item>
        <el-descriptions-item label="门店">{{ currentBatch.store_name }}</el-descriptions-item>
        <el-descriptions-item label="表类型">
          <el-tag :type="getTableTypeTag(currentBatch.table_type)" size="small">
            {{ currentBatch.table_type_name || getTableTypeName(currentBatch.table_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="数据行数">{{ currentBatch.row_count }} 行</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentBatch.status)">
            {{ getStatusText(currentBatch.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="上传时间" :span="2">
          {{ formatTime(currentBatch.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="销售总额" v-if="currentBatch.sales_total">
          ¥{{ currentBatch.sales_total?.toLocaleString() }}
        </el-descriptions-item>
        <el-descriptions-item label="实收总额" v-if="currentBatch.actual_total">
          ¥{{ currentBatch.actual_total?.toLocaleString() }}
        </el-descriptions-item>
      </el-descriptions>
      
      <!-- 错误日志 -->
      <div v-if="currentBatch?.error_log" class="error-log">
        <el-divider content-position="left">错误日志</el-divider>
        <el-alert type="error" :closable="false">
          <pre>{{ currentBatch.error_log }}</pre>
        </el-alert>
      </div>
      
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-popconfirm
          title="确定要删除这个批次吗？"
          @confirm="handleDelete(currentBatch); detailVisible = false"
        >
          <template #reference>
            <el-button type="danger">删除此批次</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { listBatches, getBatchDetail, deleteBatch } from '@/api/batch'
import { listStores } from '@/api/store'

// 状态
const loading = ref(false)
const batches = ref([])
const total = ref(0)
const stores = ref([])
const detailVisible = ref(false)
const currentBatch = ref(null)

// 注入门店选择状态
const currentStore = inject('currentStore', ref('all'))

// 筛选条件
const filters = reactive({
  store_id: null,
  table_type: null,
  status: null,
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
})

// 状态映射
const STATUS_MAP = {
  pending: { type: 'warning', text: '处理中' },
  success: { type: 'success', text: '成功' },
  failed: { type: 'danger', text: '失败' },
  warning: { type: 'warning', text: '有警告' },
}

const TABLE_TYPE_MAP = {
  booking: { name: '预订汇总', tag: '' },
  room: { name: '包厢开台', tag: 'success' },
  sales: { name: '酒水销售', tag: 'warning' },
}

const getStatusType = (status) => STATUS_MAP[status]?.type || 'info'
const getStatusText = (status) => STATUS_MAP[status]?.text || status
const getTableTypeName = (type) => TABLE_TYPE_MAP[type]?.name || type
const getTableTypeTag = (type) => TABLE_TYPE_MAP[type]?.tag || ''

// 获取当前门店名称
const getCurrentStoreName = () => {
  if (currentStore.value === 'all') return '全部门店'
  if (!stores.value || stores.value.length === 0) return '加载中...'
  const store = stores.value.find(s => s.id.toString() === currentStore.value)
  return store ? store.name : `门店ID: ${currentStore.value}`
}

// 监听门店变化，自动重新加载数据
watch(currentStore, (newStore) => {
  pagination.page = 1 // 重置到第一页
  loadBatches()
})

// 加载门店列表
const loadStores = async () => {
  try {
    const res = await listStores(true)
    stores.value = res.data || []
  } catch (error) {
    console.error('加载门店失败:', error)
  }
}

// 加载批次列表
const loadBatches = async () => {
  loading.value = true

  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      table_type: filters.table_type,
      status: filters.status,
    }

    // 根据当前门店选择设置store_id参数
    if (currentStore.value !== 'all') {
      params.store_id = parseInt(currentStore.value)
    }

    // 移除空值
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === '') {
        delete params[key]
      }
    })

    const res = await listBatches(params)
    batches.value = res.data || []
    total.value = res.total || 0
  } catch (error) {
    console.error('加载批次失败:', error)
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  filters.table_type = null
  filters.status = null
  pagination.page = 1
  loadBatches()
}

// 查看详情
const showDetail = async (row) => {
  try {
    const detail = await getBatchDetail(row.id)
    currentBatch.value = detail
    detailVisible.value = true
  } catch (error) {
    console.error('获取详情失败:', error)
  }
}

// 删除批次
const handleDelete = async (row) => {
  try {
    const res = await deleteBatch(row.id)
    ElMessage.success(res.message || '删除成功')
    loadBatches()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  try {
    return new Date(time).toLocaleString('zh-CN')
  } catch {
    return time
  }
}

// 初始化
onMounted(() => {
  loadStores()
  // 手动触发一次数据加载
  loadBatches()
})
</script>

<style lang="scss" scoped>
.batch-page {
  .filter-card {
    margin-bottom: 20px;
    
    :deep(.el-card__body) {
      padding-bottom: 0;
    }
  }
  
  .table-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .total-count {
        font-size: 14px;
        color: #909399;
      }
    }
    
    .pagination-wrapper {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
    }
  }
  
  .error-log {
    margin-top: 20px;
    
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
      font-size: 12px;
    }
  }
}
</style>
