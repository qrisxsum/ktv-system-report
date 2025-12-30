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
            <el-option label="连锁会员变动明细" value="member_change" />
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
          background
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="total"
          :page-sizes="pageSizeOptions"
          :layout="paginationLayout"
          :pager-count="pagerCount"
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
      :fullscreen="isMobile"
      destroy-on-close
      class="batch-detail-dialog"
    >
      <div class="batch-detail-content" v-if="currentBatch">
        <!-- 头部信息卡片 -->
        <div class="detail-header">
          <div class="header-main">
            <div class="batch-id">#{{ currentBatch.id }}</div>
            <el-tag :type="getStatusType(currentBatch.status)" size="large" effect="dark">
              {{ getStatusText(currentBatch.status) }}
            </el-tag>
          </div>
          <div class="batch-no-text">{{ currentBatch.batch_no }}</div>
        </div>

        <!-- 文件信息 -->
        <div class="detail-section">
          <div class="section-title">
            <el-icon><Document /></el-icon>
            <span>文件信息</span>
          </div>
          <div class="section-content">
            <div class="info-row">
              <span class="info-label">文件名</span>
              <span class="info-value file-name">{{ currentBatch.file_name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">表类型</span>
              <span class="info-value">
                <el-tag :type="getTableTypeTag(currentBatch.table_type)" size="small">
                  {{ currentBatch.table_type_name || getTableTypeName(currentBatch.table_type) }}
                </el-tag>
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">数据行数</span>
              <span class="info-value highlight">{{ currentBatch.row_count }} 行</span>
            </div>
          </div>
        </div>

        <!-- 门店信息 -->
        <div class="detail-section">
          <div class="section-title">
            <el-icon><Shop /></el-icon>
            <span>门店信息</span>
          </div>
          <div class="section-content">
            <div class="info-row">
              <span class="info-label">所属门店</span>
              <span class="info-value">{{ currentBatch.store_name }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">上传时间</span>
              <span class="info-value">{{ formatTime(currentBatch.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 金额信息（如果有） -->
        <div class="detail-section" v-if="currentBatch.sales_total || currentBatch.actual_total">
          <div class="section-title">
            <el-icon><Money /></el-icon>
            <span>金额统计</span>
          </div>
          <div class="section-content money-grid">
            <div class="money-card" v-if="currentBatch.sales_total">
              <span class="money-label">销售总额</span>
              <span class="money-value">¥{{ currentBatch.sales_total?.toLocaleString() }}</span>
            </div>
            <div class="money-card" v-if="currentBatch.actual_total">
              <span class="money-label">实收总额</span>
              <span class="money-value actual">¥{{ currentBatch.actual_total?.toLocaleString() }}</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 错误日志 -->
      <div v-if="currentBatch?.error_log" class="error-log">
        <el-divider content-position="left">错误日志</el-divider>
        <el-alert type="error" :closable="false">
          <pre>{{ currentBatch.error_log }}</pre>
        </el-alert>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailVisible = false">关闭</el-button>
          <el-popconfirm
            title="确定要删除这个批次吗？"
            @confirm="handleDelete(currentBatch); detailVisible = false"
          >
            <template #reference>
              <el-button type="danger">删除此批次</el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, inject, watch, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listBatches, getBatchDetail, deleteBatch } from '@/api/batch'
import { listStores } from '@/api/store'
import { usePagination } from '@/composables/usePagination'

// 状态
const loading = ref(false)
const batches = ref([])
const total = ref(0)
const stores = ref([])
const detailVisible = ref(false)
const currentBatch = ref(null)

// 移动端检测
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value <= 768)

const handleResize = () => {
  windowWidth.value = window.innerWidth
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  loadStores()
  loadBatches()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

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

// 使用分页优化 Composable
const { pageSizeOptions, paginationLayout, pagerCount } = usePagination({
  desktopPageSizes: [10, 20, 50, 100],
  mobilePageSizes: [10, 20, 50]
})

// 状态映射
const STATUS_MAP = {
  pending: { type: 'warning', text: '处理中' },
  success: { type: 'success', text: '成功' },
  failed: { type: 'danger', text: '失败' },
  warning: { type: 'warning', text: '有警告' },
}

const TABLE_TYPE_MAP = {
  booking: { name: '预订汇总', tag: 'info' },
  room: { name: '包厢开台', tag: 'success' },
  sales: { name: '酒水销售', tag: 'warning' },
  member_change: { name: '连锁会员变动明细', tag: 'primary' },
}

const getStatusType = (status) => STATUS_MAP[status]?.type || 'info'
const getStatusText = (status) => STATUS_MAP[status]?.text || status
const getTableTypeName = (type) => TABLE_TYPE_MAP[type]?.name || type
const getTableTypeTag = (type) => TABLE_TYPE_MAP[type]?.tag || 'info'

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
    if (currentStore.value && currentStore.value !== 'all') {
      const parsedStoreId = parseInt(currentStore.value, 10)
      if (Number.isFinite(parsedStoreId)) {
        params.store_id = parsedStoreId
      }
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
      width: 100%;
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

  // 批次详情样式
  .batch-detail-content {
    // 头部信息
    .detail-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
      color: #fff;

      .header-main {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .batch-id {
          font-size: 24px;
          font-weight: 700;
        }
      }

      .batch-no-text {
        font-size: 12px;
        opacity: 0.85;
        font-family: monospace;
        word-break: break-all;
      }
    }

    // 信息区块
    .detail-section {
      background: #fff;
      border-radius: 10px;
      border: 1px solid #ebeef5;
      margin-bottom: 12px;
      overflow: hidden;

      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 16px;
        background: #f8f9fa;
        border-bottom: 1px solid #ebeef5;
        font-weight: 600;
        font-size: 14px;
        color: #303133;

        .el-icon {
          color: #409eff;
          font-size: 16px;
        }
      }

      .section-content {
        padding: 4px 0;

        .info-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding: 12px 16px;
          border-bottom: 1px solid #f0f0f0;

          &:last-child {
            border-bottom: none;
          }

          .info-label {
            color: #909399;
            font-size: 13px;
            flex-shrink: 0;
            min-width: 70px;
          }

          .info-value {
            color: #303133;
            font-size: 14px;
            text-align: right;
            word-break: break-word;
            flex: 1;
            margin-left: 12px;

            &.file-name {
              font-size: 13px;
              line-height: 1.5;
            }

            &.highlight {
              color: #409eff;
              font-weight: 500;
            }
          }
        }

        // 金额卡片样式
        &.money-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          padding: 12px 16px;

          .money-card {
            background: linear-gradient(135deg, #fff8e6 0%, #fff4d6 100%);
            border-radius: 8px;
            padding: 14px;
            text-align: center;
            border: 1px solid #ffeeba;

            .money-label {
              display: block;
              font-size: 12px;
              color: #909399;
              margin-bottom: 6px;
            }

            .money-value {
              display: block;
              font-size: 18px;
              font-weight: 700;
              color: #e6a23c;

              &.actual {
                color: #67c23a;
              }
            }
          }
        }
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  // 移动端优化
  @media (max-width: 768px) {
    .filter-card {
      // 优化内边距
      :deep(.el-card__body) {
        padding: 15px 12px 15px 12px;
      }

      :deep(.el-form) {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        
        .el-form-item {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          margin-right: 0;
          margin-bottom: 0;

          // 当前门店筛选占满一行
          &:first-child {
            width: 100%;
          }

          // 表类型和状态各占一半
          &:nth-child(2),
          &:nth-child(3) {
            width: calc(50% - 6px);
          }

          // 按钮组占满一行
          &:last-child {
            width: 100%;
          }

          .el-form-item__label {
            width: auto;
            padding-right: 0;
            padding-bottom: 4px;
            font-size: 13px;
            line-height: 1.4;
          }

          .el-form-item__content {
            width: 100%;
            margin-left: 0 !important;

            .el-select,
            .el-button {
              width: 100% !important;
            }
          }
          
          // 按钮组横向排列
          &:last-child .el-form-item__content {
            display: flex;
            gap: 12px;
            
            .el-button {
              flex: 1;
              margin-left: 0;
            }
          }
        }
      }
    }

    .table-card {
      .card-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }

      // 表格横向滚动
      :deep(.el-table) {
        .el-table__header-wrapper,
        .el-table__body-wrapper {
          overflow-x: auto;
        }

        // 固定操作列
        .el-table__fixed-right {
          box-shadow: -2px 0 4px rgba(0, 0, 0, 0.1);
        }
      }

      .pagination-wrapper {
        justify-content: center !important;
        margin-top: 15px;
        overflow-x: auto; // 允许横向滚动作为后备方案
        -webkit-overflow-scrolling: touch;

        :deep(.el-pagination) {
          flex-wrap: wrap; // 允许换行
          justify-content: center;
          font-size: 12px;

          .el-pagination__total,
          .el-pagination__sizes,
          .el-pagination__jump {
            margin-right: 8px;
            font-size: 12px;
          }

          .btn-prev,
          .btn-next {
            min-width: 26px;
            height: 26px;
            line-height: 26px;
            padding: 0 6px;
          }

          .el-pager {
            li {
              min-width: 26px;
              height: 26px;
              line-height: 26px;
              font-size: 12px;
              margin: 0 2px;
            }
          }

          // 每页条数选择器优化
          .el-pagination__sizes {
            .el-select {
              .el-input {
                .el-input__inner {
                  height: 26px;
                  line-height: 26px;
                  font-size: 12px;
                  padding: 0 20px 0 8px;
                }
              }
            }
          }

          // 跳转输入框优化
          .el-pagination__jump {
            .el-input {
              .el-input__inner {
                height: 26px;
                line-height: 26px;
                font-size: 12px;
                width: 40px;
              }
            }
          }
        }
      }
    }

    // 详情弹窗优化
    :deep(.el-dialog) {
      width: 90% !important;
      margin: 0 auto;
      
      .el-dialog__header {
        padding: 15px;
      }

      .el-dialog__body {
        padding: 12px;
        background: #f5f7fa;
      }

      .el-dialog__footer {
        padding: 12px 15px;
      }
    }

    // 移动端详情内容优化
    .batch-detail-content {
      .detail-header {
        padding: 16px;
        margin-bottom: 12px;

        .header-main {
          .batch-id {
            font-size: 20px;
          }
        }

        .batch-no-text {
          font-size: 11px;
        }
      }

      .detail-section {
        margin-bottom: 10px;

        .section-title {
          padding: 10px 14px;
          font-size: 13px;
        }

        .section-content {
          .info-row {
            padding: 10px 14px;

            .info-label {
              font-size: 12px;
            }

            .info-value {
              font-size: 13px;
            }
          }

          &.money-grid {
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            padding: 10px 14px;

            .money-card {
              padding: 12px 10px;

              .money-label {
                font-size: 11px;
              }

              .money-value {
                font-size: 16px;
              }
            }
          }
        }
      }
    }

    .dialog-footer {
      justify-content: center;
      
      .el-button {
        flex: 1;
        max-width: 150px;
      }
    }
  }

  @media (max-width: 480px) {
    .filter-card {
      :deep(.el-card__body) {
        padding: 12px;
      }

      :deep(.el-form) {
        .el-form-item {
          margin-bottom: 10px;

          .el-form-item__label {
            font-size: 13px;
          }
        }
      }
    }

    .table-card {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 12px;
      }

      .card-header {
        font-size: 14px;

        .total-count {
          font-size: 12px;
        }
      }

      :deep(.el-table) {
        font-size: 11px;

        .el-table__header th,
        .el-table__body td {
          padding: 6px 5px;
        }

        .el-button {
          padding: 4px 8px;
          font-size: 11px;
        }

        .el-tag {
          font-size: 10px;
          padding: 0 4px;
        }
      }
    }

    .pagination-wrapper {
      margin-top: 12px;

      :deep(.el-pagination) {
        font-size: 11px;
        gap: 4px; // 元素间距更小

        .el-pagination__total {
          font-size: 11px;
          margin-right: 4px;
        }

        .el-pagination__sizes {
          margin-right: 4px;
          
          .el-select {
            .el-input {
              .el-input__inner {
                height: 24px;
                line-height: 24px;
                font-size: 11px;
                padding: 0 18px 0 6px;
              }
            }
          }
        }

        .btn-prev,
        .btn-next {
          min-width: 24px;
          height: 24px;
          line-height: 24px;
          padding: 0 4px;
        }

        .el-pager {
          li {
            min-width: 24px;
            height: 24px;
            line-height: 24px;
            font-size: 11px;
            margin: 0 1px;
          }
        }

        .el-pagination__jump {
          margin-left: 4px;
          font-size: 11px;
          
          .el-input {
            .el-input__inner {
              height: 24px;
              line-height: 24px;
              font-size: 11px;
              width: 35px;
            }
          }
        }
      }
    }

    .error-log {
      pre {
        font-size: 11px;
      }
    }
  }
}
</style>
