<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { ApiError } from '@/api/client'
import { fetchHealth, type HealthResponse } from '@/api/system'
import StatusCard from '@/components/StatusCard.vue'

const health = ref<HealthResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const lastUpdated = ref<Date | null>(null)
let refreshTimer: number | undefined

const apiStatus = computed<'ok' | 'error' | 'unknown'>(() =>
  health.value ? 'ok' : error.value ? 'error' : 'unknown',
)
const databaseStatus = computed<'ok' | 'error' | 'unknown'>(
  () => health.value?.database.status ?? 'unknown',
)
const databaseLatency = computed(() =>
  health.value ? `${health.value.database.latency_ms.toFixed(1)} ms` : '—',
)
const backendVersion = computed(() => health.value?.version ?? '—')
const environment = computed(() => {
  if (!health.value) return '—'
  return health.value.debug ? '开发模式' : '生产模式'
})
const updatedAt = computed(() =>
  lastUpdated.value
    ? lastUpdated.value.toLocaleTimeString('zh-CN', { hour12: false })
    : '—',
)

async function loadHealth() {
  loading.value = true
  try {
    health.value = await fetchHealth()
    error.value = null
    lastUpdated.value = new Date()
  } catch (err) {
    health.value = null
    error.value = err instanceof ApiError ? err.message : '无法连接后端服务'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadHealth()
  refreshTimer = window.setInterval(() => void loadHealth(), 15_000)
})

onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
})
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="brand__mark">FP</span>
        <div>
          <h1 class="brand__title">Fund Pooling</h1>
          <p class="brand__subtitle">资金池管理平台</p>
        </div>
      </div>
      <div class="topbar__meta">
        <span class="pill">Django · Vue 3 · PostgreSQL</span>
        <button class="ghost-button" type="button" :disabled="loading" @click="loadHealth">
          {{ loading ? '检测中…' : '重新检测' }}
        </button>
      </div>
    </header>

    <main class="content">
      <section class="hero">
        <h2>服务运行状态</h2>
        <p>每 15 秒自动刷新后端与数据库健康状态。</p>
      </section>

      <p v-if="error" class="alert" role="alert">{{ error }}</p>

      <section class="grid">
        <StatusCard
          title="API 服务"
          :value="health ? '运行中' : '不可用'"
          :status="apiStatus"
          :hint="`后端版本 ${backendVersion}`"
        />
        <StatusCard
          title="PostgreSQL"
          :value="databaseStatus === 'ok' ? '已连接' : '异常'"
          :status="databaseStatus"
          :hint="`查询耗时 ${databaseLatency}`"
        />
        <StatusCard
          title="运行环境"
          :value="environment"
          :status="health ? 'ok' : 'unknown'"
          :hint="`最后检测 ${updatedAt}`"
        />
        <StatusCard
          title="前端"
          value="Vue 3 + Vite"
          status="ok"
          hint="构建产物由 Django 在 /static/ 下提供"
        />
      </section>

      <section class="panel">
        <h3>快速开始</h3>
        <ul class="list">
          <li><code>make up</code> 构建并启动数据库 + 应用容器</li>
          <li><code>make dev</code> 本地开发模式（Vite 热更新 + Django 自动重载）</li>
          <li><code>make migrate</code> 执行数据库迁移</li>
          <li><code>make superuser</code> 创建后台管理员，访问 <a href="/admin/">/admin/</a></li>
        </ul>
      </section>
    </main>

    <footer class="footer">
      <span>Fund Pooling · Django + Vue 3 + PostgreSQL + Docker Compose</span>
      <a href="/api/health/" target="_blank" rel="noreferrer">健康检查接口</a>
    </footer>
  </div>
</template>
