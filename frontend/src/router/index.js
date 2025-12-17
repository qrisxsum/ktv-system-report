import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
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

