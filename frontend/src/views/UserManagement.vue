<template>
  <div class="user-management-page">
    <!-- 筛选和操作区域 -->
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="门店">
          <el-select v-model="filters.store_id" placeholder="全部门店" clearable style="width: 180px">
            <el-option
              v-for="store in stores"
              :key="store.id"
              :label="store.name"
              :value="store.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="filters.is_active" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="启用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
        </el-form-item>

        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="搜索用户名、姓名、手机号"
            clearable
            style="width: 200px"
            @keyup.enter="loadManagers"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="loadManagers">
            <el-icon><Search /></el-icon> 查询
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
          <el-button type="success" @click="showCreateDialog">
            <el-icon><Plus /></el-icon> 添加店长
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 店长列表 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>👥 店长账号管理</span>
          <span class="total-count">共 {{ total }} 条记录</span>
        </div>
      </template>

      <el-table
        :data="managers"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="full_name" label="姓名" width="120" />
        <el-table-column prop="store_name" label="关联门店" width="150" />
        <el-table-column prop="email" label="邮箱" width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="is_active" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" width="170">
          <template #default="{ row }">
            {{ row.last_login_at ? formatTime(row.last_login_at) : '从未登录' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" :fixed="isMobile ? false : 'right'">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button
              link
              :type="row.is_active ? 'warning' : 'success'"
              size="small"
              @click="handleToggleStatus(row)"
            >
              <el-icon><Switch /></el-icon>
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button link type="info" size="small" @click="showResetPasswordDialog(row)">
              <el-icon><Key /></el-icon> 重置密码
            </el-button>
            <el-button link type="danger" size="small" @click="showDeleteDialog(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="total"
          :page-sizes="pageSizeOptions"
          :layout="paginationLayout"
          :pager-count="pagerCount"
          background
          @size-change="loadManagers"
          @current-change="loadManagers"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      destroy-on-close
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username" v-if="!isEdit">
          <el-input
            v-model="formData.username"
            placeholder="请输入用户名（3-50字符）"
            :disabled="isEdit"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input
            v-model="formData.password"
            type="password"
            placeholder="请输入密码（至少8位）"
            show-password
          />
        </el-form-item>

        <el-form-item 
          v-if="!isEdit"
          label="门店选择方式"
        >
          <el-radio-group v-model="storeInputMode" style="width: 100%">
            <el-radio label="select">选择已有门店</el-radio>
            <el-radio label="create">创建新门店</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item 
          v-if="!isEdit && storeInputMode === 'select'"
          prop="store_id"
          label="选择门店"
        >
          <el-select
            v-model="formData.store_id"
            placeholder="请选择门店"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="store in stores"
              :key="store.id"
              :label="store.name"
              :value="store.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item 
          v-if="!isEdit && storeInputMode === 'create'"
          prop="store_name"
          label="门店名称"
        >
          <el-input
            v-model="formData.store_name"
            placeholder="请输入新门店名称（如果门店不存在将自动创建）"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item 
          v-if="isEdit"
          prop="store_id"
          :label="`关联门店${currentManager?.store_name ? '（当前：' + currentManager.store_name + '）' : ''}`"
        >
          <el-select
            v-model="formData.store_id"
            placeholder="选择要关联的门店（可修改店长所属门店）"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="store in stores"
              :key="store.id"
              :label="store.name"
              :value="store.id"
            />
          </el-select>
          <div style="font-size: 12px; color: #909399; margin-top: 5px;">
            提示：修改门店后，店长账号将关联到新选择的门店
          </div>
        </el-form-item>

        <el-form-item label="真实姓名" prop="full_name">
          <el-input
            v-model="formData.full_name"
            placeholder="请输入真实姓名"
          />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="formData.email"
            placeholder="请输入邮箱"
          />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="formData.phone"
            placeholder="请输入手机号"
            maxlength="20"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 删除账号对话框 -->
    <el-dialog
      v-model="deleteDialogVisible"
      title="删除店长账号"
      width="500px"
      destroy-on-close
    >
      <div v-if="currentManager">
        <el-alert
          type="warning"
          :closable="false"
          style="margin-bottom: 20px"
        >
          <template #title>
            <div>
              <p style="margin: 0 0 10px 0;">确定要删除店长账号 <strong>{{ currentManager.username }}</strong> 吗？</p>
              <p style="margin: 0; font-size: 12px;">删除后，该账号将从数据库中永久删除，此操作不可恢复。</p>
            </div>
          </template>
        </el-alert>
        
        <el-form label-width="120px">
          <el-form-item label="关联门店">
            <div>{{ currentManager.store_name || '未关联门店' }}</div>
          </el-form-item>
          
          <el-form-item 
            v-if="currentManager.store_id"
            label="是否删除门店"
          >
            <el-radio-group v-model="deleteStoreOption">
              <el-radio label="no">仅删除账号，保留门店</el-radio>
              <el-radio label="yes">同时删除门店</el-radio>
            </el-radio-group>
            <div style="font-size: 12px; color: #909399; margin-top: 5px;">
              <span v-if="deleteStoreOption === 'yes'" style="color: #f56c6c;">
                警告：删除门店将从数据库中永久删除该门店及其所有相关数据，此操作不可恢复！
              </span>
              <span v-else>
                提示：仅删除店长账号，门店数据将保留。
              </span>
            </div>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button 
          type="danger" 
          @click="handleDelete" 
          :loading="deleting"
        >
          确定删除
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog
      v-model="resetPasswordVisible"
      title="重置密码"
      width="400px"
      destroy-on-close
    >
      <el-form
        ref="resetPasswordFormRef"
        :model="resetPasswordForm"
        :rules="resetPasswordRules"
        label-width="100px"
      >
        <el-form-item label="用户名">
          <el-input :value="currentManager?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="resetPasswordForm.new_password"
            type="password"
            placeholder="请输入新密码（至少8位）"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="resetPasswordForm.confirm_password"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="resetPasswordVisible = false">取消</el-button>
        <el-button type="primary" @click="handleResetPassword" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Refresh,
  Plus,
  Edit,
  Delete,
  Switch,
  Key,
} from '@element-plus/icons-vue'
import {
  createManager,
  listManagers,
  updateManager,
  deleteManager,
  toggleManagerStatus,
  resetManagerPassword,
} from '@/api/user'
import { listStores, deleteStore } from '@/api/store'
import { useRouter } from 'vue-router'
import { usePagination } from '@/composables/usePagination'

const router = useRouter()

// 状态
const loading = ref(false)
const submitting = ref(false)
const managers = ref([])
const stores = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const resetPasswordVisible = ref(false)
const deleteDialogVisible = ref(false)
const isEdit = ref(false)
const currentManager = ref(null)
const formRef = ref(null)
const resetPasswordFormRef = ref(null)
const currentUser = ref(null)
const deleting = ref(false)
const deleteStoreOption = ref('no') // 'no': 不删除门店, 'yes': 删除门店
// 门店输入模式：'select' 选择已有门店，'create' 创建新门店
const storeInputMode = ref('select')

// 筛选条件
const filters = reactive({
  store_id: null,
  is_active: null,
  keyword: '',
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
})

// 使用分页优化 Composable
const { isMobile, pageSizeOptions, paginationLayout, pagerCount } = usePagination({
  desktopPageSizes: [10, 20, 50, 100],
  mobilePageSizes: [10, 20, 50]
})

// 表单数据
const formData = reactive({
  username: '',
  password: '',
  store_id: null,
  store_name: '',
  full_name: '',
  email: '',
  phone: '',
})

// 重置密码表单
const resetPasswordForm = reactive({
  new_password: '',
  confirm_password: '',
})

// 表单验证规则
const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少需要8位', trigger: 'blur' },
  ],
  store_id: [
    {
      validator: (rule, value, callback) => {
        // 编辑时：必须选择门店
        if (isEdit.value) {
          if (!value) {
            callback(new Error('请选择门店'))
          } else {
            callback()
          }
        }
        // 创建时：只有在选择已有门店模式时才验证
        else if (storeInputMode.value === 'select') {
          if (!value) {
            callback(new Error('请选择门店'))
          } else {
            callback()
          }
        } else {
          // 创建新门店模式时，不验证 store_id
          callback()
        }
      },
      trigger: 'change',
    },
  ],
  store_name: [
    {
      validator: (rule, value, callback) => {
        // 只有在创建新门店模式时才验证
        if (storeInputMode.value === 'create') {
          if (!value || !value.trim()) {
            callback(new Error('请输入门店名称'))
          } else {
            callback()
          }
        } else {
          // 选择已有门店模式时，不验证 store_name
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  phone: [
    { pattern: /^[0-9]*$/, message: '手机号只能包含数字', trigger: 'blur' },
  ],
}

// 重置密码验证规则
const resetPasswordRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少需要8位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== resetPasswordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

// 对话框标题
const dialogTitle = computed(() => {
  return isEdit.value ? '编辑店长账号' : '添加店长账号'
})

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 加载门店列表
const loadStores = async () => {
  try {
    const res = await listStores(true) // 只加载启用的门店
    stores.value = res.data || []
  } catch (error) {
    console.error('加载门店失败:', error)
  }
}

// 加载店长列表
const loadManagers = async () => {
  loading.value = true
  try {
    const skip = (pagination.page - 1) * pagination.pageSize
    const params = {
      skip,
      limit: pagination.pageSize,
      ...filters,
    }
    // 移除空值
    Object.keys(params).forEach((key) => {
      if (params[key] === null || params[key] === '') {
        delete params[key]
      }
    })

    const res = await listManagers(params)
    managers.value = res.data || []
    total.value = res.meta?.total || 0
  } catch (error) {
    console.error('加载店长列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilters = () => {
  filters.store_id = null
  filters.is_active = null
  filters.keyword = ''
  pagination.page = 1
  loadManagers()
}

// 显示创建对话框
const showCreateDialog = async () => {
  isEdit.value = false
  resetForm()
  // 刷新门店列表，确保数据最新
  await loadStores()
  dialogVisible.value = true
}

// 显示编辑对话框
const showEditDialog = async (row) => {
  isEdit.value = true
  currentManager.value = row
  // 刷新门店列表，确保数据最新
  await loadStores()
  storeInputMode.value = 'select' // 编辑时只能选择已有门店
  formData.username = row.username
  formData.store_id = row.store_id
  formData.store_name = '' // 编辑时不使用门店名称
  formData.full_name = row.full_name || ''
  formData.email = row.email || ''
  formData.phone = row.phone || ''
  formData.password = '' // 编辑时不显示密码
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  storeInputMode.value = 'select'
  Object.assign(formData, {
    username: '',
    password: '',
    store_id: null,
    store_name: '',
    full_name: '',
    email: '',
    phone: '',
  })
  currentManager.value = null
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const data = { ...formData }
      // 编辑时，如果没有输入密码，则不传密码字段
      if (isEdit.value && !data.password) {
        delete data.password
      }
      
      // 根据编辑/创建模式处理门店数据
      if (isEdit.value) {
        // 编辑模式：只传 store_id（编辑时只能选择已有门店）
        delete data.store_name
        if (!data.store_id) {
          ElMessage.error('请选择门店')
          submitting.value = false
          return
        }
      } else if (storeInputMode.value === 'select') {
        // 创建模式 - 选择已有门店：只传 store_id
        delete data.store_name
        if (!data.store_id) {
          ElMessage.error('请选择门店')
          submitting.value = false
          return
        }
      } else {
        // 创建模式 - 创建新门店：只传 store_name
        delete data.store_id
        if (!data.store_name || !data.store_name.trim()) {
          ElMessage.error('请输入门店名称')
          submitting.value = false
          return
        }
        data.store_name = data.store_name.trim()
      }
      
      // 移除空字符串
      Object.keys(data).forEach((key) => {
        if (data[key] === '') {
          data[key] = null
        }
      })

      if (isEdit.value) {
        await updateManager(currentManager.value.id, data)
        ElMessage.success('更新成功')
      } else {
        await createManager(data)
        ElMessage.success('创建成功')
        // 如果创建了新门店，需要刷新门店列表
        if (storeInputMode.value === 'create' && data.store_name) {
          await loadStores()
        }
      }

      dialogVisible.value = false
      loadManagers()
    } catch (error) {
      console.error('提交失败:', error)
    } finally {
      submitting.value = false
    }
  })
}

// 切换状态
const handleToggleStatus = async (row) => {
  try {
    await toggleManagerStatus(row.id)
    ElMessage.success(`已${row.is_active ? '停用' : '启用'}`)
    loadManagers()
  } catch (error) {
    console.error('切换状态失败:', error)
  }
}

// 显示重置密码对话框
const showResetPasswordDialog = (row) => {
  currentManager.value = row
  resetPasswordForm.new_password = ''
  resetPasswordForm.confirm_password = ''
  resetPasswordVisible.value = true
}

// 重置密码
const handleResetPassword = async () => {
  if (!resetPasswordFormRef.value) return

  await resetPasswordFormRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      await resetManagerPassword(currentManager.value.id, resetPasswordForm.new_password)
      ElMessage.success('密码重置成功，用户需要重新登录')
      resetPasswordVisible.value = false
    } catch (error) {
      console.error('重置密码失败:', error)
    } finally {
      submitting.value = false
    }
  })
}

// 显示删除对话框
const showDeleteDialog = (row) => {
  currentManager.value = row
  deleteStoreOption.value = 'no' // 默认不删除门店
  deleteDialogVisible.value = true
}

// 删除店长
const handleDelete = async () => {
  if (!currentManager.value) return
  
  deleting.value = true
  try {
    // 先删除账号
    await deleteManager(currentManager.value.id)
    
    // 如果选择删除门店，则删除门店
    if (deleteStoreOption.value === 'yes' && currentManager.value.store_id) {
      try {
        await deleteStore(currentManager.value.store_id)
        ElMessage.success('店长账号和门店已删除')
      } catch (error) {
        // 如果删除门店失败，但账号已删除，仍然提示成功
        console.error('删除门店失败:', error)
        ElMessage.warning('店长账号已删除，但删除门店失败：' + (error.response?.data?.detail || error.message || '未知错误'))
      }
    } else {
      ElMessage.success('店长账号已删除')
    }
    
    deleteDialogVisible.value = false
    // 刷新门店列表（如果删除了门店，需要更新下拉框）
    if (deleteStoreOption.value === 'yes') {
      await loadStores()
    }
    loadManagers()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error('删除失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  } finally {
    deleting.value = false
  }
}

// 加载当前用户信息
const loadCurrentUser = () => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      currentUser.value = JSON.parse(userStr)
      // 检查权限：只有管理员可以访问
      if (currentUser.value?.role !== 'admin') {
        ElMessage.warning('只有管理员可以访问账号管理功能')
        router.push('/dashboard')
        return false
      }
    }
    return true
  } catch (error) {
    console.error('加载用户信息失败:', error)
    return false
  }
}

// 初始化
onMounted(() => {
  if (!loadCurrentUser()) {
    return
  }
  loadStores()
  loadManagers()
})
</script>

<style lang="scss" scoped>
.user-management-page {
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
        color: #909399;
        font-size: 14px;
      }
    }

    .pagination-wrapper {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
      width: 100%;
    }
  }

  // 移动端优化
  @media (max-width: 768px) {
    .filter-card {
      :deep(.el-card__body) {
        padding: 15px 12px 15px 12px;
      }

      :deep(.el-form) {
        display: flex;
        flex-wrap: wrap;
        gap: 14px;

        .el-form-item {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          margin-right: 0;
          margin-bottom: 0;

          // 门店和状态各占一半
          &:nth-child(1),
          &:nth-child(2) {
            width: calc(50% - 7px);
          }

          // 关键词占满一行
          &:nth-child(3) {
            width: 100%;
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
            .el-input {
              width: 100% !important;
            }
          }

          // 按钮组横向排列
          &:last-child .el-form-item__content {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;

            .el-button {
              flex: 1;
              min-width: calc(33% - 6px);
              margin-left: 0;
            }
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
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
      }

      :deep(.el-table) {
        font-size: 12px;

        .el-table__header th,
        .el-table__body td {
          padding: 8px 5px;
        }

        // 固定操作列
        .el-table__fixed-right {
          box-shadow: -2px 0 4px rgba(0, 0, 0, 0.1);
        }
      }

      .pagination-wrapper {
        justify-content: center !important;
        margin-top: 15px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;

        :deep(.el-pagination) {
          flex-wrap: wrap;
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

    // 对话框优化
    :deep(.el-dialog) {
      width: 90% !important;
      margin: 0 auto;

      .el-dialog__header {
        padding: 15px;
      }

      .el-dialog__body {
        padding: 15px;

        .el-form {
          .el-form-item {
            margin-bottom: 16px;

            .el-form-item__label {
              font-size: 13px;
            }

            .el-input,
            .el-select {
              font-size: 14px;
            }

            .el-radio-group {
              display: flex;
              flex-direction: column;
              gap: 8px;
            }
          }
        }
      }

      .el-dialog__footer {
        padding: 12px 15px;

        .el-button {
          width: 48%;
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
        gap: 12px;

        .el-form-item {
          // 480px 以下门店和状态仍然各占一半
          &:nth-child(1),
          &:nth-child(2) {
            width: calc(50% - 6px);
          }

          .el-form-item__label {
            font-size: 12px;
          }

          // 按钮组
          &:last-child .el-form-item__content {
            .el-button {
              min-width: calc(50% - 4px);
              font-size: 13px;
              padding: 8px 12px;

              // 添加店长按钮单独一行
              &:last-child {
                width: 100%;
                margin-top: 4px;
              }
            }
          }
        }
      }
    }

    .table-card {
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
          padding: 6px 3px;
        }

        .el-button {
          padding: 4px 6px;
          font-size: 11px;
        }

        .el-tag {
          font-size: 10px;
          padding: 0 4px;
        }
      }

      .pagination-wrapper {
        margin-top: 12px;

        :deep(.el-pagination) {
          font-size: 11px;
          gap: 4px;

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
    }

    :deep(.el-dialog) {
      width: 95% !important;

      .el-dialog__body {
        padding: 12px;

        .el-form {
          .el-form-item {
            margin-bottom: 14px;

            .el-form-item__label {
              font-size: 12px;
            }
          }
        }
      }

      .el-dialog__footer {
        padding: 10px 12px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;

        .el-button {
          width: 100%;
          margin-left: 0 !important;
        }
      }
    }
  }
}
</style>

