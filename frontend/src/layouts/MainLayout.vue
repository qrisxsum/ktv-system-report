<template>
  <el-container class="main-layout">
    <!-- 桌面端侧边栏 -->
    <el-aside 
      v-if="!isMobile"
      :width="isCollapse ? '64px' : '220px'" 
      class="aside"
    >
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
        <template v-for="item in menuItems" :key="item.index">
          <!-- 仅当没有角色限制或用户符合角色限制时显示 -->
          <template v-if="!item.role || currentUser?.role === item.role">
            <!-- 子菜单 -->
            <el-sub-menu v-if="item.children" :index="item.index">
              <template #title>
                <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
                <span>{{ item.title }}</span>
              </template>
              <el-menu-item 
                v-for="child in item.children" 
                :key="child.index" 
                :index="child.index"
              >
                {{ child.title }}
              </el-menu-item>
            </el-sub-menu>

            <!-- 普通菜单项 -->
            <el-menu-item v-else :index="item.index">
              <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
              <template #title>{{ item.title }}</template>
            </el-menu-item>
          </template>
        </template>
      </el-menu>
    </el-aside>

    <!-- 移动端侧边栏抽屉 -->
    <el-drawer
      v-model="mobileMenuVisible"
      :with-header="false"
      direction="ltr"
      size="200px"
      class="mobile-drawer"
    >
      <div class="aside mobile-aside">
        <div class="logo">
          <el-icon size="28"><Microphone /></el-icon>
          <span class="logo-text">KTV 经营分析</span>
        </div>
        
        <el-menu
          :default-active="activeMenu"
          router
          class="menu"
          @select="handleMobileMenuSelect"
        >
          <template v-for="item in menuItems" :key="item.index">
            <!-- 仅当没有角色限制或用户符合角色限制时显示 -->
            <template v-if="!item.role || currentUser?.role === item.role">
              <!-- 子菜单 -->
              <el-sub-menu v-if="item.children" :index="item.index">
                <template #title>
                  <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
                  <span>{{ item.title }}</span>
                </template>
                <el-menu-item 
                  v-for="child in item.children" 
                  :key="child.index" 
                  :index="child.index"
                >
                  {{ child.title }}
                </el-menu-item>
              </el-sub-menu>

              <!-- 普通菜单项 -->
              <el-menu-item v-else :index="item.index">
                <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
                <template #title>{{ item.title }}</template>
              </el-menu-item>
            </template>
          </template>
        </el-menu>
      </div>
    </el-drawer>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <!-- 移动端显示菜单按钮,桌面端显示折叠按钮 -->
          <el-icon 
            v-if="isMobile"
            class="collapse-btn menu-btn" 
            @click="mobileMenuVisible = true"
          >
            <Menu />
          </el-icon>
          <el-icon 
            v-else
            class="collapse-btn" 
            @click="isCollapse = !isCollapse"
          >
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          
          <!-- 移动端隐藏面包屑,显示标题 -->
          <span v-if="isMobile" class="mobile-title">{{ currentTitle }}</span>
          <el-breadcrumb v-else separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <!-- 门店选择器（管理员） -->
          <el-select 
            v-if="showStoreSelector && currentUser?.role === 'admin'"
            v-model="currentStore" 
            placeholder="选择门店" 
            :class="isMobile ? 'mobile-store-select' : ''"
            :style="isMobile ? 'width: 100px' : 'width: 180px'"
          >
            <el-option
              v-for="store in stores"
              :key="store.id"
              :label="store.name"
              :value="store.id.toString()"
            />
          </el-select>

          <!-- 门店名称显示（店长） - 移动端简化显示 -->
          <div 
            v-if="showStoreSelector && currentUser?.role === 'manager'"
            class="current-store-display"
            :style="isMobile ? 'width: auto; padding-right: 10px;' : 'width: 180px; text-align: right; padding-right: 20px;'"
          >
            <span class="store-label">{{ isMobile ? '' : (userStoreName || '我的门店') }}</span>
          </div>

          <!-- 用户信息和登出 -->
          <el-dropdown @command="handleUserCommand" class="user-dropdown">
            <span class="user-info">
              <el-icon><Avatar /></el-icon>
              <span v-if="!isMobile" class="username">{{ currentUser?.username || '未登录' }}</span>
              <span v-if="!isMobile && currentUser" class="user-role">({{ currentUser.role === 'admin' ? '管理员' : '店长' }})</span>
              <el-icon v-if="!isMobile" class="el-icon--right"><ArrowDown /></el-icon>
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
import { ref, computed, provide, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listStores } from '@/api/store'
import { logout } from '@/api/auth'
import { Avatar, ArrowDown, SwitchButton, Menu } from '@element-plus/icons-vue'

// 菜单配置
const menuItems = [
  { index: '/dashboard', icon: 'DataAnalysis', title: '综合驾驶舱' },
  { index: '/upload', icon: 'Upload', title: '数据上传' },
  { index: '/batch', icon: 'List', title: '批次管理' },
  { index: '/data-health', icon: 'Monitor', title: '数据健康度' },
  { index: '/general-analysis', icon: 'DataLine', title: '通用分析' },
  {
    index: '/analysis',
    icon: 'TrendCharts',
    title: '专项分析',
    children: [
      { index: '/analysis/staff', title: '人员风云榜' },
      { index: '/analysis/products', title: '商品销售' },
      { index: '/analysis/rooms', title: '包厢效能' },
      { index: '/analysis/financial', title: '财务专项' },
      { index: '/analysis/members', title: '会员变动' }
    ]
  },
  { index: '/users', icon: 'User', title: '账号管理', role: 'admin' }
]

const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const currentStore = ref('all')
const stores = ref([])
const currentUser = ref(null)
const mobileMenuVisible = ref(false)
const isMobile = ref(false)

// 检测是否为移动设备
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
  // 移动端自动折叠侧边栏
  if (isMobile.value) {
    isCollapse.value = true
  }
}

// 监听窗口大小变化
const handleResize = () => {
  checkMobile()
}

// 移动端菜单选择后关闭抽屉
const handleMobileMenuSelect = () => {
  if (isMobile.value) {
    mobileMenuVisible.value = false
  }
}

// 创建简单的事件发射器
const eventEmitter = {
  listeners: {},
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event].push(callback)
  },
  off(event, callback) {
    if (!this.listeners[event]) return
    const index = this.listeners[event].indexOf(callback)
    if (index > -1) {
      this.listeners[event].splice(index, 1)
    }
  },
  emit(event, ...args) {
    if (!this.listeners[event]) return
    this.listeners[event].forEach(callback => {
      callback(...args)
    })
  }
}

// 监听文件入库事件，更新门店选择器
eventEmitter.on('file-imported', (importData) => {
  console.log('收到文件入库事件:', importData)
  // 文件入库成功后，刷新门店列表以确保数据最新
  // 这对于"全部门店"选择特别重要，因为可能有新门店数据
  loadStores()
})

// 提供门店状态和事件发射器给子组件
provide('currentStore', currentStore)
provide('eventEmitter', eventEmitter)

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

// setup 阶段就初始化用户与门店（避免子页面首次挂载时拿到空门店导致请求报错）
loadCurrentUser()

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
const showStoreSelector = computed(() => route.meta?.hideStoreSelector !== true)

// 组件挂载时加载数据
onMounted(() => {
  loadStores()
  checkMobile()
  window.addEventListener('resize', handleResize)
})

// 组件卸载时移除监听
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss">
// 移动端抽屉样式覆盖 - 放置在非 scoped 样式块中以确保样式生效
.mobile-drawer {
  --el-drawer-padding-primary: 0; // 使用变量去除内边距
  --el-drawer-bg-color: #1a1a2e; // 设置背景色避免边缘白边
  
  .el-drawer__body {
    padding: 0 !important;
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  }
}
</style>

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

  &.mobile-aside {
    height: 100%;
    width: 100%;
  }
}

// 移除旧的 scoped 样式，因为已移至全局样式块
// 移动端抽屉样式
// .mobile-drawer {
//   :deep(.el-drawer__body) {
//     padding: 0;
//   }
// }

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

      &.menu-btn {
        font-size: 24px;
      }
    }

    .mobile-title {
      font-size: 16px;
      font-weight: 500;
      color: #303133;
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

// 移动端样式优化
@media (max-width: 768px) {
  .header {
    padding: 0 12px;
    height: 50px;

    .header-left {
      gap: 10px;
      flex: 1;
    }

    .header-right {
      gap: 8px;

      .mobile-store-select {
        :deep(.el-input__inner) {
          font-size: 13px;
        }
      }

      .user-dropdown .user-info {
        padding: 6px 8px;
      }
    }
  }

  .main {
    padding: 12px;
  }
}

@media (max-width: 480px) {
  .header {
    padding: 0 10px;

    .header-left .mobile-title {
      font-size: 14px;
    }
  }

  .main {
    padding: 10px;
  }
}
</style>

