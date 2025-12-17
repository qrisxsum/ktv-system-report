<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon size="28"><Microphone /></el-icon>
        <span v-show="!isCollapse" class="logo-text">KTV 经营分析</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>综合驾驶舱</template>
        </el-menu-item>
        
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <template #title>数据上传</template>
        </el-menu-item>
        
        <el-menu-item index="/batch">
          <el-icon><List /></el-icon>
          <template #title>批次管理</template>
        </el-menu-item>
        
        <el-sub-menu index="/analysis">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>专项分析</span>
          </template>
          <el-menu-item index="/analysis/staff">人员风云榜</el-menu-item>
          <el-menu-item index="/analysis/products">商品销售</el-menu-item>
          <el-menu-item index="/analysis/rooms">包厢效能</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon 
            class="collapse-btn" 
            @click="isCollapse = !isCollapse"
          >
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <!-- 显示当前门店名称 -->
          <div class="current-store-display" style="width: 180px; text-align: right; padding-right: 20px;">
            <span class="store-label">{{ currentStoreDisplay }}</span>
          </div>

          <!-- 用户信息和登出 -->
          <el-dropdown @command="handleUserCommand" class="user-dropdown">
            <span class="user-info">
              <el-icon><Avatar /></el-icon>
              <span class="username">{{ currentUser?.username || '未登录' }}</span>
              <span class="user-role" v-if="currentUser">({{ currentUser.role === 'admin' ? '管理员' : '店长' }})</span>
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, provide, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listStores } from '@/api/store'
import { logout } from '@/api/auth'
import { Avatar, ArrowDown, SwitchButton } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const currentStore = ref('')
const stores = ref([])
const currentUser = ref(null)

// 提供门店状态给子组件
provide('currentStore', currentStore)

// 监听门店变化，用于调试
watch(currentStore, (newValue) => {
  console.log('门店切换到:', newValue)
})

// 获取用户门店名称
const userStoreName = computed(() => {
  if (!currentUser.value?.store_id || !stores.value.length) {
    return ''
  }
  const userStore = stores.value.find(store => store.id === currentUser.value.store_id)
  return userStore ? userStore.name : ''
})

// 获取当前显示的门店名称
const currentStoreDisplay = computed(() => {
  if (currentUser.value?.role === 'admin') {
    return '全部门店'
  } else if (currentUser.value?.role === 'manager') {
    return userStoreName.value || '我的门店'
  }
  return ''
})

// 加载当前用户信息
const loadCurrentUser = () => {
  try {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      currentUser.value = JSON.parse(userStr)

      // 根据用户角色设置默认门店
      if (currentUser.value.role === 'admin') {
        currentStore.value = 'all' // 管理员默认查看全部门店
      } else if (currentUser.value.role === 'manager' && currentUser.value.store_id) {
        currentStore.value = currentUser.value.store_id.toString() // 店长默认查看自己的门店
      }
    }
  } catch (error) {
    console.error('加载用户信息失败:', error)
  }
}

// 处理用户菜单命令
const handleUserCommand = async (command) => {
  switch (command) {
    case 'logout':
      await handleLogout()
      break
  }
}

// 处理登出
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    // 先清除本地存储
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    currentUser.value = null

    // 调用登出API
    try {
      await logout()
    } catch (error) {
      console.warn('登出API调用失败，但本地数据已清除:', error)
    }

    ElMessage.success('已退出登录')

    // 跳转到登录页
    router.push('/login')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('登出失败:', error)
    }
  }
}

// 加载门店列表
const loadStores = async () => {
  try {
    console.log('开始加载门店列表...')
    const response = await listStores(true) // 只加载启用的门店
    const apiStores = response.data || []
    console.log('API返回的门店列表:', apiStores)

    // 在门店列表开头添加"全部门店"选项
    stores.value = [
      { id: 'all', name: '全部门店' },
      ...apiStores
    ]
    console.log('最终门店列表:', stores.value)
  } catch (error) {
    console.error('加载门店列表失败:', error)
    console.error('错误详情:', error.response?.data)
    // 如果API调用失败，使用默认门店选项作为后备
    stores.value = [
      { id: 'all', name: '全部门店' },
      { id: 1, name: '万象城店' },
      { id: 2, name: '青年路店' }
    ]
    console.log('使用fallback门店列表:', stores.value)
  }
}

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title || '首页')

// 组件挂载时加载数据
onMounted(() => {
  loadStores()
  loadCurrentUser()
})
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
}

.aside {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  transition: width 0.3s;
  overflow: hidden;
  
  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: #fff;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    
    .logo-text {
      white-space: nowrap;
    }
  }
  
  .menu {
    border-right: none;
    background: transparent;
    
    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      color: rgba(255, 255, 255, 0.7);
      
      &:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #fff;
      }
    }
    
    :deep(.el-menu-item.is-active) {
      background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      color: #fff;
    }

    // 修复子菜单展开时文字看不清的问题
    :deep(.el-menu--inline) {
      background: transparent;

      .el-menu-item {
        color: rgba(255, 255, 255, 0.7);
        padding-left: 50px !important; // 增加缩进
        
        &:hover {
          color: #fff;
          background-color: rgba(255, 255, 255, 0.1);
        }
        
        &.is-active {
          background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
          color: #fff;
        }
      }
    }
  }
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  padding: 0 20px;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 15px;

    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
      color: #606266;

      &:hover {
        color: #409eff;
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 15px;

    .user-dropdown {
      cursor: pointer;

      .user-info {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 6px;
        transition: background-color 0.3s;

        &:hover {
          background-color: #f5f7fa;
        }

        .username {
          font-size: 14px;
          font-weight: 500;
          color: #303133;
        }

        .user-role {
          font-size: 12px;
          color: #909399;
        }

        .el-icon {
          color: #606266;
        }
      }
    }
  }
}

.main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>

