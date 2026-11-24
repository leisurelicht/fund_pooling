import { reactive } from 'vue'

import {
  fetchMe,
  login as loginApi,
  loginWithApple as loginAppleApi,
  loginWithGoogle as loginGoogleApi,
  logout as logoutApi,
  type AppleFullName,
  type User,
} from '@/api/auth'

/**
 * 极简的登录状态管理（无需引入 Pinia）：
 * - `user` 为空表示未登录
 * - `loaded` 避免重复请求 /auth/me/
 */
export const session = reactive<{
  user: User | null
  loaded: boolean
}>({
  user: null,
  loaded: false,
})

export async function loadSession(force = false): Promise<void> {
  if (session.loaded && !force) return
  try {
    session.user = (await fetchMe()).user
  } catch {
    session.user = null
  } finally {
    session.loaded = true
  }
}

export async function login(identifier: string, password: string): Promise<void> {
  session.user = (await loginApi(identifier, password)).user
  session.loaded = true
}

export async function logout(): Promise<void> {
  try {
    await logoutApi()
  } finally {
    session.user = null
    session.loaded = true
  }
}

export async function loginWithApple(
  idToken: string,
  fullName?: AppleFullName | null,
): Promise<void> {
  session.user = (await loginAppleApi(idToken, fullName)).user
  session.loaded = true
}

export async function loginWithGoogle(credential: string): Promise<void> {
  session.user = (await loginGoogleApi(credential)).user
  session.loaded = true
}
