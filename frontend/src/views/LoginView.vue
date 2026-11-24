<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import { login } from '@/auth/session'

const identifier = ref('')
const password = ref('')
const error = ref<string | null>(null)
const submitting = ref(false)

const route = useRoute()
const router = useRouter()

/** 只接受站内绝对路径，避免 open redirect */
function safeRedirect(): string {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  if (target.startsWith('/') && !target.startsWith('//')) return target
  return '/'
}

async function submit() {
  if (submitting.value) return

  error.value = null
  if (!identifier.value.trim() || !password.value) {
    error.value = '请输入用户名/邮箱和密码'
    return
  }

  submitting.value = true
  try {
    await login(identifier.value.trim(), password.value)
    await router.replace(safeRedirect())
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '登录失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="login">
    <section class="login__card">
      <div class="login__brand">
        <span class="brand__mark">FP</span>
        <div>
          <h1 class="login__title">Fund Pooling</h1>
          <p class="login__subtitle">资金池管理平台</p>
        </div>
      </div>

      <form class="login__form" @submit.prevent="submit">
        <label class="field">
          <span class="field__label">用户名 / 邮箱</span>
          <input
            v-model="identifier"
            class="field__input"
            type="text"
            name="username"
            autocomplete="username"
            placeholder="请输入用户名或邮箱"
            autofocus
          />
        </label>

        <label class="field">
          <span class="field__label">密码</span>
          <input
            v-model="password"
            class="field__input"
            type="password"
            name="password"
            autocomplete="current-password"
            placeholder="请输入密码"
          />
        </label>

        <p v-if="error" class="login__error" role="alert">{{ error }}</p>

        <button class="primary-button" type="submit" :disabled="submitting">
          {{ submitting ? '登录中…' : '登录' }}
        </button>
      </form>
    </section>
  </main>
</template>
