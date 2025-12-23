import { createRouter, createWebHistory } from 'vue-router'

// 路由守卫：检查是否已登录
const requireAuth = (to, from, next) => {
  const token = localStorage.getItem('access_token')
  const user = localStorage.getItem('user')

  console.log('路由守卫检查:', {
    to: to.path,
    from: from.path,
    token: !!token,
    user: !!user,
    tokenValue: token,
    userValue: user
  })

  if (token && user) {
    // 已登录，继续访问
    console.log('已登录，继续访问')
    next()
  } else {
    // 未登录，跳转到登录页
    console.log('未登录，跳转到登录页')
    next('/login')
  }
}

// 路由守卫：检查是否已登录（用于登录页）
const redirectIfAuth = (to, from, next) => {
  const token = localStorage.getItem('access_token')
  const user = localStorage.getItem('user')

  if (token && user) {
    // 已登录，跳转到首页
    next('/dashboard')
  } else {
    // 未登录，继续访问登录页
    next()
  }
}

const routes = [
  // 登录页
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录' },
    beforeEnter: redirectIfAuth
  },
  // 主应用页面（需要登录）
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    beforeEnter: requireAuth,
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '综合驾驶舱', icon: 'DataAnalysis' }
      },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('@/views/Upload.vue'),
        meta: { title: '数据上传', icon: 'Upload' }
      },
      {
        path: 'batch',
        name: 'Batch',
        component: () => import('@/views/Batch.vue'),
        meta: { title: '批次管理', icon: 'List' }
      },
      {
        path: 'data-health',
        name: 'DataHealth',
        component: () => import('@/views/DataHealth.vue'),
        meta: { title: '数据健康度', icon: 'DataBoard' }
      },
      {
        path: 'general-analysis',
        name: 'GeneralAnalysis',
        component: () => import('@/views/analysis/GeneralAnalysis.vue'),
        meta: { title: '通用分析', icon: 'DataLine', hideStoreSelector: true }
      },
      {
        path: 'analysis',
        name: 'Analysis',
        redirect: '/analysis/staff',
        meta: { title: '专项分析', icon: 'TrendCharts' },
        children: [
          {
            path: 'staff',
            name: 'StaffAnalysis',
            component: () => import('@/views/analysis/StaffAnalysis.vue'),
            meta: { title: '人员风云榜' }
          },
          {
            path: 'products',
            name: 'ProductAnalysis',
            component: () => import('@/views/analysis/ProductAnalysis.vue'),
            meta: { title: '商品销售' }
          },
          {
            path: 'rooms',
            name: 'RoomAnalysis',
            component: () => import('@/views/analysis/RoomAnalysis.vue'),
            meta: { title: '包厢效能' }
          }
        ]
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('@/views/UserManagement.vue'),
        meta: { title: '账号管理', icon: 'User', hideStoreSelector: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/404.vue'),
    meta: { title: '404' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

