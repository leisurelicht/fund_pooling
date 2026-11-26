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
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    // 其他路径统一回到首页，由首页守卫决定是否跳登录
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
      return { name: 'home' }
    }
    return true
  }

  if (!session.user) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
