import { createRouter, createWebHistory } from 'vue-router'

import { loadSession, session } from '@/auth/session'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'overview',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: () => import('@/views/TransactionsView.vue'),
    },
    {
      path: '/sips',
      name: 'sips',
      component: () => import('@/views/SipsView.vue'),
    },
    {
      path: '/analysis',
      name: 'analysis',
      component: () => import('@/views/AnalysisView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
    {
      path: '/assets/:code',
      name: 'asset-detail',
      component: () => import('@/views/AssetDetailView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

/**
 * 全局守卫：
 * - 未登录访问受保护页面 → 跳 /login?redirect=<原地址>
 * - 已登录访问 /login       → 跳首页
 */
router.beforeEach(async (to) => {
  await loadSession()

  if (to.meta.public) {
    if (session.user && to.name === 'login') {
      return { name: 'overview' }
    }
    return true
  }

  if (!session.user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

const CHUNK_RELOAD_KEY = 'chunk-reload'

/**
 * 懒加载分块失效时自动刷新一次：
 * 重新部署后，仍开着的旧页面会引用已被替换掉的 chunk 文件名，点击导航会静默失败。
 * 这里识别「动态模块加载失败」，强制刷新以拿到新的入口文件。
 * 用 sessionStorage 记录，避免刷新后仍然失败时陷入死循环。
 */
router.onError((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error)
  if (!/dynamically imported module|Importing a module script failed/i.test(message)) return
  if (sessionStorage.getItem(CHUNK_RELOAD_KEY)) return
  sessionStorage.setItem(CHUNK_RELOAD_KEY, '1')
  window.location.reload()
})

router.afterEach(() => {
  sessionStorage.removeItem(CHUNK_RELOAD_KEY)
})

export default router