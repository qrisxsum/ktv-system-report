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
          <el-select v-model="currentStore" placeholder="选择门店" style="width: 180px">
            <el-option
              v-for="store in stores"
              :key="store.id"
              :label="store.name"
              :value="store.id.toString()"
            />
          </el-select>
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
import { useRoute } from 'vue-router'
import { listStores } from '@/api/store'

const route = useRoute()
const isCollapse = ref(false)
const currentStore = ref('all')
const stores = ref([])

// 提供门店状态给子组件
provide('currentStore', currentStore)

// 监听门店变化，用于调试
watch(currentStore, (newValue) => {
  console.log('门店切换到:', newValue)
})

// 加载门店列表
const loadStores = async () => {
  try {
    const response = await listStores(true) // 只加载启用的门店
    const apiStores = response.data || []
    // 在门店列表开头添加"全部门店"选项
    stores.value = [
      { id: 'all', name: '全部门店' },
      ...apiStores
    ]
  } catch (error) {
    console.error('加载门店列表失败:', error)
    // 如果API调用失败，使用默认门店选项作为后备
    stores.value = [
      { id: 'all', name: '全部门店' },
      { id: 1, name: '万象城店' },
      { id: 2, name: '青年路店' }
    ]
  }
}

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta?.title || '首页')

// 组件挂载时加载门店列表
onMounted(() => {
  loadStores()
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
}

.main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>

