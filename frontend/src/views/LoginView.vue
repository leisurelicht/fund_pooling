<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchAuthConfig } from '@/api/auth'
import { ApiError } from '@/api/client'
import { login, loginWithApple, loginWithGoogle } from '@/auth/session'

const APPLE_SDK_URL =
  'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js'
const GOOGLE_SDK_URL = 'https://accounts.google.com/gsi/client'

/**
 * client id 由后端 /api/auth/config/ 在运行时下发。
 * 为空时不渲染对应按钮，密码登录始终可用。
 */
const appleClientId = ref('')
const googleClientId = ref('')
/** 至少有一个按钮真的渲染成功后才显示分隔线与按钮区 */
const oauthReady = ref(false)

const identifier = ref('')
const password = ref('')
const error = ref<string | null>(null)
const submitting = ref(false)

const appleSubmitting = ref(false)
const googleSubmitting = ref(false)
const googleButton = ref<HTMLElement | null>(null)

const route = useRoute()
const router = useRouter()

/** 只接受站内绝对路径，避免 open redirect */
function safeRedirect(): string {
  const target = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  if (target.startsWith('/') && !target.startsWith('//')) return target
  return '/'
}

/** 用户在授权弹窗里主动取消时不必提示错误 */
function isCancelled(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const code = (err as { error?: unknown }).error
  return code === 'popup_closed_by_user' || code === 'user_cancel' || code === 'access_denied'
}

/** 把第三方 SDK / 接口异常统一转成给用户看的提示 */
function describeError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) return err.message
  if (err && typeof err === 'object' && 'error' in err) {
    const message = (err as { error?: unknown }).error
    if (typeof message === 'string' && message) return message
  }
  return fallback
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

// ── 第三方登录 SDK 加载 ─────────────────────────────────────

/** 注入外部脚本；已存在则直接认为加载完成 */
function loadScript(src: string, marker: string): Promise<void> {
  if (document.querySelector(`script[src*="${marker}"]`)) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = src
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`SDK 加载失败：${src}`))
    document.head.appendChild(script)
  })
}

/** 第三方入口被隐藏时在控制台留痕，避免「按钮莫名消失」无从排查 */
function warnHidden(reason: string, err?: unknown): void {
  console.warn(`[oauth] ${reason}，已隐藏该第三方登录入口`, err ?? '')
}

onMounted(() => {
  void setupThirdPartyLogin()
})

/** 先向后端要配置，再按需加载对应 SDK 并渲染按钮 */
async function setupThirdPartyLogin() {
  try {
    const config = await fetchAuthConfig()
    appleClientId.value = (config.apple_client_id ?? '').trim()
    googleClientId.value = (config.google_client_id ?? '').trim()
  } catch {
    // 配置拉不到就只保留密码登录，不影响登录页可用性
    return
  }

  if (!appleClientId.value && !googleClientId.value) return

  // 等 v-if 把按钮容器渲染出来，否则 renderButton 拿不到 DOM
  await nextTick()

  if (appleClientId.value) {
    try {
      await loadScript(APPLE_SDK_URL, 'appleid.auth')
      if (!initAppleSDK()) {
        warnHidden('Apple 按钮渲染失败')
        appleClientId.value = ''
      }
    } catch (err) {
      // CDN 不可用时清空 clientId，模板会连同分隔线一起去掉这个入口
      warnHidden('Apple SDK 加载失败', err)
      appleClientId.value = ''
    }
  }

  if (googleClientId.value) {
    try {
      await loadScript(GOOGLE_SDK_URL, 'gsi/client')
      if (!initGoogleSDK()) {
        warnHidden('Google 按钮渲染失败')
        googleClientId.value = ''
      }
    } catch (err) {
      warnHidden('Google SDK 加载失败', err)
      googleClientId.value = ''
    }
  }

  // 全部渲染尝试结束后再决定是否展示第三方登录区：
  // 失败的一方已经把 clientId 清空，两个都失败时这里恒为 false
  oauthReady.value = Boolean(appleClientId.value || googleClientId.value)
}

// ── Apple ──────────────────────────────────────────────────

/** 渲染 Apple 按钮；任一环节失败返回 false，调用方据此隐藏整个第三方入口 */
function initAppleSDK(): boolean {
  const clientId = appleClientId.value
  const apple = window.AppleID
  if (!clientId || !apple) return false

  apple.auth.init({
    clientId,
    scope: 'name email',
    // usePopup 模式下 SDK 通过 postMessage 回传 token，不需要填 redirectURI
    usePopup: true,
  })

  // 用 SDK 渲染合规按钮（自动应对 dark mode、HIG 尺寸/颜色）
  try {
    apple.auth.renderButton('#appleid-signin', {
      type: 'sign-in',
      style: 'black',
      borderRadius: 8,
      mode: 'center-align',
    })
  } catch {
    // 旧版 SDK 无 renderButton，无法渲染合规按钮
    return false
  }
  return true
}

async function handleAppleLogin() {
  if (!window.AppleID || appleSubmitting.value) return

  error.value = null
  appleSubmitting.value = true
  try {
    const response = await window.AppleID.auth.signIn()
    const idToken = response.detail.authorization.id_token
    const name = response.detail.user?.name
    await loginWithApple(
      idToken,
      name ? { givenName: name.firstName, familyName: name.lastName } : null,
    )
    await router.replace(safeRedirect())
  } catch (err) {
    if (!isCancelled(err)) error.value = describeError(err, 'Apple 登录失败，请稍后重试')
  } finally {
    appleSubmitting.value = false
  }
}

// ── Google ─────────────────────────────────────────────────

/** 渲染 Google 按钮；失败返回 false，调用方据此隐藏整个第三方入口 */
function initGoogleSDK(): boolean {
  const clientId = googleClientId.value
  const google = window.google
  if (!clientId || !google || !googleButton.value) return false

  google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleCredential,
  })

  try {
    google.accounts.id.renderButton(googleButton.value, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      text: 'signin_with',
      shape: 'rectangular',
      logo_alignment: 'left',
      width: 336,
    })
  } catch {
    return false
  }
  return true
}

async function handleGoogleCredential(response: GoogleCredentialResponse) {
  if (googleSubmitting.value) return
  if (!response?.credential) {
    error.value = 'Google 未返回有效凭证，请重试'
    return
  }

  error.value = null
  googleSubmitting.value = true
  try {
    await loginWithGoogle(response.credential)
    await router.replace(safeRedirect())
  } catch (err) {
    error.value = describeError(err, 'Google 登录失败，请稍后重试')
  } finally {
    googleSubmitting.value = false
  }
}
</script>

<template>
  <main class="login">
    <section class="login__card">
      <div class="login__brand">
        <span class="brand__mark">账</span>
        <div>
          <h1 class="login__title">资产账本</h1>
          <p class="login__subtitle">基金与股票持仓管理</p>
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

      <!-- 只有真的渲染出按钮时才展示分隔线，避免出现孤零零的「或」 -->
      <template v-if="appleClientId || googleClientId">
        <div v-if="oauthReady" class="login__divider"><span>或</span></div>

        <!-- Apple 按钮按 HIG 要求排在首位 -->
        <div
          v-if="appleClientId"
          id="appleid-signin"
          class="login__oauth"
          :class="{
            'login__oauth--ready': oauthReady,
            'login__oauth--busy': appleSubmitting,
          }"
          data-type="sign-in"
          data-style="black"
          data-border-radius="8"
          data-mode="center-align"
          @click="handleAppleLogin"
        ></div>

        <div
          v-if="googleClientId"
          class="login__oauth"
          :class="{
            'login__oauth--ready': oauthReady,
            'login__oauth--busy': googleSubmitting,
          }"
        >
          <div ref="googleButton" class="login__oauth-google"></div>
        </div>
      </template>
    </section>
  </main>
</template>
