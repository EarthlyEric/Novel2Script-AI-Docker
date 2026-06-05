/**
 * Vue Router 路由配置
 *
 * 定义三个核心页面路由：
 * - /          HomeView   首页/上传页面
 * - /preview   PreviewView 剧本预览页面
 * - /edit      EditView   剧本编辑页面
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '上传小说' },
  },
  {
    path: '/preview',
    name: 'preview',
    component: () => import('@/views/PreviewView.vue'),
    meta: { title: '剧本预览' },
  },
  {
    path: '/edit',
    name: 'edit',
    component: () => import('@/views/EditView.vue'),
    meta: { title: '剧本编辑' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由切换时更新页面标题
router.beforeEach((to) => {
  document.title = `${to.meta.title || ''} - 文剧智转`
})

export default router
