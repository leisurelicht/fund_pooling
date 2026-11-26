<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { logout, session } from '@/auth/session'

const route = useRoute()
const router = useRouter()
const showChrome = computed(() => !route.meta.public)
const loggingOut = ref(false)

async function handleLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await logout()
    await router.push({ name: 'login' })
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div class="app" :class="{ 'app--plain': !showChrome }">
    <header v-if="showChrome" class="topbar">
      <div class="brand">
        <span class="brand__mark">FP</span>
        <div>
          <h1 class="brand__title">Fund Pooling</h1>
          <p class="brand__subtitle">基金管理平台</p>
        </div>
      </div>
      <div class="topbar__meta">
        <span v-if="session.user" class="user-badge">
          <span class="user-badge__dot" aria-hidden="true"></span>
          {{ session.user.username }}
        </span>
        <button class="ghost-button" type="button" :disabled="loggingOut" @click="handleLogout">
          {{ loggingOut ? '退出中…' : '退出登录' }}
        </button>
      </div>
    </header>

    <RouterView />

    <footer v-if="showChrome" class="footer">
      <span>Fund Pooling · Django + Vue 3 + PostgreSQL + Docker Compose</span>
      <a href="/api/health/" target="_blank" rel="noreferrer">健康检查接口</a>
    </footer>
  </div>
</template>
