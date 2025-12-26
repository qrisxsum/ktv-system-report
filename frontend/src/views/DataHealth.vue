<template>
  <div class="data-health-page">
    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="月份">
          <el-date-picker
            v-model="filters.data_month"
            type="month"
            placeholder="选择月份"
            format="YYYY-MM"
            value-format="YYYY-MM"
            :editable="false"
            style="width: 150px"
            @change="loadData"
          />
        </el-form-item>

        <el-form-item>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 汇总统计 -->
    <el-card class="summary-card" v-if="summary">
      <template #header>
        <div class="card-header">
          <span>📊 数据完整度概览</span>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="6">
          <el-statistic title="完整数据" :value="summary.complete_count">
            <template #suffix>
              <el-tag type="success" size="small">项</el-tag>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="部分缺失" :value="summary.partial_count">
            <template #suffix>
              <el-tag type="warning" size="small">项</el-tag>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="完全缺失" :value="summary.missing_count">
            <template #suffix>
              <el-tag type="danger" size="small">项</el-tag>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="总门店数" :value="summary.total_stores">
            <template #suffix>
              <el-tag type="info" size="small">家</el-tag>
            </template>
          </el-statistic>
        </el-col>
      </el-row>
      
      <div v-if="dateRange" style="margin-top: 15px; color: #909399; font-size: 14px;">
        数据日期范围: {{ dateRange.start }} 至 {{ dateRange.end }}
      </div>
    </el-card>

    <!-- 数据完整度矩阵 -->
    <el-card class="matrix-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>📋 数据完整度矩阵</span>
          <el-button link type="primary" @click="loadData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>

      <el-table
        :data="matrixData"
        stripe
        border
        style="width: 100%"
        :default-sort="{ prop: 'store_name', order: 'ascending' }"
      >
        <el-table-column prop="store_name" label="门店" width="150" fixed="left" />
        <el-table-column 
          v-for="reportType in reportTypes" 
          :key="reportType.value"
          :label="reportType.label"
          :prop="reportType.value"
          width="180"
          align="center"
        >
          <template #default="{ row }">
            <template v-if="row[reportType.value]">
              <el-tooltip
                :content="getStatusTooltip(row[reportType.value])"
                placement="top"
              >
                <div
                  class="status-badge"
                  :class="`status-badge--${row[reportType.value]?.status || 'unknown'}`"
                  @click="showDetail(row.store_id, reportType.value, row[reportType.value])"
                >
                  <span class="status-label">
                    {{ getStatusText(row[reportType.value]?.status) }}
                  </span>
                  <span
                    v-if="getCoveragePercent(row[reportType.value])"
                    class="status-percent"
                  >
                    {{ getCoveragePercent(row[reportType.value]) }}
                  </span>
                </div>
              </el-tooltip>
            </template>
            <template v-else>
              <span style="color: #c0c4cc;">-</span>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="数据详情"
      :size="600"
    >
      <div v-if="selectedDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="门店">
            {{ selectedDetail.store_name }}
          </el-descriptions-item>
          <el-descriptions-item label="报表类型">
            {{ selectedDetail.report_type_name }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(selectedDetail.status)" size="small">
              {{ getStatusText(selectedDetail.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据行数">
            {{ selectedDetail.row_count || 0 }} 行
          </el-descriptions-item>
          <el-descriptions-item label="覆盖天数">
            {{ selectedDetail.coverage_days || 0 }} / {{ selectedDetail.expected_days || 0 }} 天
          </el-descriptions-item>
          <el-descriptions-item label="最近上传">
            {{ formatTime(selectedDetail.latest_upload) }}
          </el-descriptions-item>
          <el-descriptions-item label="数据日期范围" :span="2">
            <span v-if="selectedDetail.date_range?.start">
              {{ selectedDetail.date_range.start }} 至 {{ selectedDetail.date_range.end }}
            </span>
            <span v-else style="color: #909399;">暂无数据</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="selectedDetail.status === 'missing'"
          title="数据缺失"
          type="warning"
          :closable="false"
          style="margin-top: 20px"
        >
          <template #default>
            <p>该门店该报表类型在当前月份暂无数据，请及时上传。</p>
          </template>
        </el-alert>

        <el-alert
          v-if="selectedDetail.status === 'partial'"
          title="数据部分缺失"
          type="warning"
          :closable="false"
          style="margin-top: 20px"
        >
          <template #default>
            <p>
              该门店该报表类型在当前月份只覆盖了 {{ selectedDetail.coverage_days }} 天，
              期望覆盖 {{ selectedDetail.expected_days }} 天。
            </p>
            <p style="margin-top: 8px;">
              缺失日期: 
              <span v-if="selectedDetail.date_range?.start">
                {{ getMissingDays(selectedDetail) }}
              </span>
            </p>
          </template>
        </el-alert>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, inject, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getDataCoverage } from '@/api/health'

// 状态
const loading = ref(false)
const summary = ref(null)
const dateRange = ref(null)
const details = ref([])
const drawerVisible = ref(false)
const selectedDetail = ref(null)

// 筛选条件
const filters = ref({
  data_month: null
})

// 注入门店选择状态和事件发射器
const currentStore = inject('currentStore', ref('all'))
const eventEmitter = inject('eventEmitter', null)

// 报表类型定义
const reportTypes = [
  { value: 'booking', label: '预订汇总' },
  { value: 'room', label: '包厢开台分析' },
  { value: 'sales', label: '酒水销售分析' },
  { value: 'member_change', label: '连锁会员变动明细' }
]

// 计算矩阵数据
const matrixData = computed(() => {
  if (!details.value.length) return []
  
  // 按门店分组
  const storeMap = new Map()
  
  details.value.forEach(detail => {
    if (!storeMap.has(detail.store_id)) {
      storeMap.set(detail.store_id, {
        store_id: detail.store_id,
        store_name: detail.store_name
      })
    }
    
    const storeData = storeMap.get(detail.store_id)
    storeData[detail.report_type] = detail
  })
  
  return Array.from(storeMap.values())
})

// 监听门店变化，自动重新加载数据
watch(currentStore, (newStore) => {
  loadData()
})

// 加载数据
const loadData = async () => {
  loading.value = true
  
  try {
    const params = {}
    
    // 根据当前门店选择设置store_id参数
    if (currentStore.value && currentStore.value !== 'all') {
      const parsedStoreId = parseInt(currentStore.value, 10)
      if (Number.isFinite(parsedStoreId)) {
        params.store_id = parsedStoreId
      }
    }
    
    // 处理月份筛选
    if (filters.value.data_month) {
      params.data_month = filters.value.data_month
    }
    
    const response = await getDataCoverage(params)
    
    if (response.success && response.data) {
      summary.value = response.data.summary
      dateRange.value = response.data.date_range
      details.value = response.data.details || []
    } else {
      ElMessage.error(response.message || '加载数据失败')
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  filters.value = {
    data_month: null
  }
  loadData()
}

// 显示详情
const showDetail = (storeId, reportType, detail) => {
  if (!detail) {
    ElMessage.info('暂无数据')
    return
  }
  
  selectedDetail.value = detail
  drawerVisible.value = true
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const map = {
    complete: 'success',
    partial: 'warning',
    missing: 'danger'
  }
  return map[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const map = {
    complete: '完整',
    partial: '部分缺失',
    missing: '缺失'
  }
  return map[status] || '未知'
}

// 覆盖率（用于矩阵里的百分比显示）
const getCoveragePercent = (detail) => {
  if (!detail || !detail.expected_days) return ''
  const coverage = detail.coverage_days || 0
  const expected = detail.expected_days || 0
  if (!expected) return ''
  const percent = Math.round((coverage / expected) * 100)
  return `${percent}%`
}

// 矩阵单元格 tooltip 文案
const getStatusTooltip = (detail) => {
  if (!detail) return '暂无数据'
  const percent = getCoveragePercent(detail)
  const coverageText = detail.expected_days
    ? `覆盖 ${detail.coverage_days || 0} / ${detail.expected_days} 天${percent ? `（${percent}）` : ''}`
    : ''

  switch (detail.status) {
    case 'complete':
      return coverageText ? `数据完整，${coverageText}` : '数据完整'
    case 'partial':
      return coverageText
        ? `数据部分缺失，${coverageText}。请检查缺失日期的数据是否已上传。`
        : '数据部分缺失，请检查上传情况。'
    case 'missing':
      return '当前月份无任何数据，请上传对应类型报表。'
    default:
      return coverageText || '暂无数据'
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
      minute: '2-digit'
    })
  } catch {
    return time
  }
}

// 计算缺失日期 - 现在直接使用后端返回的准确缺失日期
const getMissingDays = (detail) => {
  // 优先使用后端返回的准确缺失日期列表
  if (detail.missing_dates && Array.isArray(detail.missing_dates)) {
    const missing = detail.missing_dates
    
    if (missing.length === 0) {
      return '无缺失'
    }
    
    if (missing.length <= 5) {
      return missing.join(', ')
    }
    
    return `${missing.slice(0, 5).join(', ')} 等 ${missing.length} 天`
  }
  
  // 向后兼容：如果后端没有返回 missing_dates，则使用旧的计算方式
  if (!detail.date_range?.start || !dateRange.value) {
    return '无法计算'
  }
  
  const start = new Date(dateRange.value.start)
  const end = new Date(dateRange.value.end)
  const dataStart = new Date(detail.date_range.start)
  const dataEnd = new Date(detail.date_range.end)
  
  const missing = []
  const current = new Date(start)
  
  while (current <= end) {
    const dateStr = current.toISOString().split('T')[0]
    if (current < dataStart || current > dataEnd) {
      missing.push(dateStr)
    }
    current.setDate(current.getDate() + 1)
  }
  
  if (missing.length === 0) {
    return '无缺失'
  }
  
  if (missing.length <= 5) {
    return missing.join(', ')
  }
  
  return `${missing.slice(0, 5).join(', ')} 等 ${missing.length} 天`
}

// 初始化
onMounted(() => {
  loadData()
})
</script>

<style lang="scss" scoped>
.data-health-page {
  .filter-card {
    margin-bottom: 20px;

    :deep(.el-card__body) {
      padding-bottom: 0;
    }
  }

  .summary-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }

  .matrix-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      min-width: 90px;
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 500;
      color: #fff;
      cursor: pointer;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
      transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;

      &:hover {
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.15);
        opacity: 0.95;
      }

      &--complete {
        background: linear-gradient(135deg, #3ecf8e, #28a745);
      }

      &--partial {
        background: linear-gradient(135deg, #f6a623, #e67e22);
      }

      &--missing {
        background: linear-gradient(135deg, #ff6b6b, #e53935);
      }

      &--unknown {
        background: linear-gradient(135deg, #c0c4cc, #909399);
      }

      .status-label {
        white-space: nowrap;
      }

      .status-percent {
        font-size: 12px;
        opacity: 0.9;
      }
    }
  }

  // 移动端优化
  @media (max-width: 768px) {
    .filter-card {
      :deep(.el-card__body) {
        padding: 12px;
      }

      :deep(.el-form) {
        display: flex;
        align-items: flex-end;
        gap: 12px;

        .el-form-item {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          margin-right: 0;
          margin-bottom: 0;
          flex: 1;

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

            :deep(.el-date-editor) {
              width: 100% !important;
              height: 32px;
            }
            
            .el-button {
              width: 100%;
              height: 32px;
              margin-left: 0;
            }
          }

          // 重置按钮隐藏label
          &:last-child {
            flex: 0 0 auto;
            
            .el-form-item__label {
              visibility: hidden;
              height: 0;
              padding: 0;
              margin: 0;
            }
          }
        }
      }
    }

    .summary-card {
      :deep(.el-row) {
        .el-col {
          margin-bottom: 12px;

          &:last-child {
            margin-bottom: 0;
          }
        }
      }

      :deep(.el-statistic) {
        .el-statistic__head {
          font-size: 13px;
        }

        .el-statistic__content {
          .el-statistic__number {
            font-size: 20px;
          }
        }
      }
    }

    .matrix-card {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 12px;
      }

      // 表格优化
      :deep(.el-table) {
        font-size: 12px;

        .el-table__header th,
        .el-table__body td {
          padding: 8px 5px;
        }

        // 固定列阴影
        .el-table__fixed-left {
          box-shadow: 2px 0 4px rgba(0, 0, 0, 0.1);
        }
      }

      .status-badge {
        min-width: 70px;
        padding: 3px 8px;
        font-size: 11px;
        gap: 4px;

        .status-percent {
          font-size: 10px;
        }
      }
    }

    // 详情抽屉优化
    :deep(.el-drawer) {
      width: 90% !important;
      max-width: 400px;

      .el-drawer__header {
        padding: 15px;
        margin-bottom: 0;
      }

      .el-drawer__body {
        padding: 15px;

        .el-descriptions {
          font-size: 13px;

          .el-descriptions__label,
          .el-descriptions__content {
            font-size: 13px;
            padding: 8px 10px;
          }
        }
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
          .el-form-item__label {
            font-size: 12px;
          }
        }
      }
    }

    .summary-card {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 12px;
      }

      :deep(.el-statistic) {
        .el-statistic__head {
          font-size: 12px;
        }

        .el-statistic__content {
          .el-statistic__number {
            font-size: 18px;
          }
        }
      }
    }

    .matrix-card {
      :deep(.el-table) {
        font-size: 11px;

        .el-table__header th,
        .el-table__body td {
          padding: 6px 3px;
        }
      }

      .status-badge {
        min-width: 60px;
        padding: 2px 6px;
        font-size: 10px;

        .status-percent {
          font-size: 9px;
        }
      }
    }

    :deep(.el-drawer) {
      width: 100% !important;
      max-width: none;

      .el-descriptions {
        .el-descriptions__label,
        .el-descriptions__content {
          font-size: 12px;
          padding: 6px 8px;
        }
      }
    }
  }
}
</style>

