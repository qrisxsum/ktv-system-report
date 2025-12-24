import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

/**
 * 分页组件移动端优化 Composable
 * 
 * @param {Object} options - 配置选项
 * @param {Array<number>} options.desktopPageSizes - 桌面端每页条数选项，默认 [20, 50, 100]
 * @param {Array<number>} options.mobilePageSizes - 移动端每页条数选项，默认 [20, 50]
 * @returns {Object} 返回分页相关的响应式状态和配置
 */
export function usePagination(options = {}) {
  const {
    desktopPageSizes = [20, 50, 100],
    mobilePageSizes = [20, 50]
  } = options

  // 响应式状态
  const isMobile = ref(false)
  const isSmallScreen = ref(false)

  // 检测设备类型
  const checkDevice = () => {
    isMobile.value = window.innerWidth <= 768
    isSmallScreen.value = window.innerWidth <= 480
  }

  // 计算属性：每页条数选项
  const pageSizeOptions = computed(() => {
    return isMobile.value ? mobilePageSizes : desktopPageSizes
  })

  // 计算属性：分页布局
  const paginationLayout = computed(() => {
    if (isSmallScreen.value) {
      return 'sizes, prev, pager, next'
    } else if (isMobile.value) {
      return 'total, sizes, prev, pager, next'
    } else {
      return 'total, sizes, prev, pager, next, jumper'
    }
  })

  // 计算属性：页码按钮数量
  const pagerCount = computed(() => {
    if (isSmallScreen.value) {
      return 3
    } else if (isMobile.value) {
      return 5
    } else {
      return 7
    }
  })

  // 生命周期：组件挂载时初始化
  onMounted(() => {
    checkDevice()
    window.addEventListener('resize', checkDevice)
  })

  // 生命周期：组件卸载时清理
  onBeforeUnmount(() => {
    window.removeEventListener('resize', checkDevice)
  })

  return {
    // 响应式状态
    isMobile,
    isSmallScreen,
    
    // 计算属性
    pageSizeOptions,
    paginationLayout,
    pagerCount,
    
    // 方法（如果需要手动触发检测）
    checkDevice
  }
}
