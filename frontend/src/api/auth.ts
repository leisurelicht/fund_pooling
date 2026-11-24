import { request } from './client'

export interface User {
  id: number
  username: string
  email: string
  is_staff: boolean
  is_superuser: boolean
}

interface UserPayload {
  user: User
}

/** 后端下发的第三方登录配置；未配置的 provider 为空字符串 */
export interface AuthConfig {
  google_client_id: string
  apple_client_id: string
}

/**
 * 运行时读取第三方登录配置。
 * client id 是公开信息，由后端下发即可避免把它固化进前端构建产物——
 * 换 id 只需重启后端，不用重新构建镜像。
 */
export function fetchAuthConfig(): Promise<AuthConfig> {
  return request<AuthConfig>('/auth/config/')
}

export function fetchMe(): Promise<UserPayload> {
  return request<UserPayload>('/auth/me/')
}

/** `identifier` 可以是用户名或邮箱（后端同一字段接收） */
export function login(identifier: string, password: string): Promise<UserPayload> {
  return request<UserPayload>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username: identifier, password }),
  })
}

export function logout(): Promise<void> {
  return request<void>('/auth/logout/', { method: 'POST' })
}

export interface AppleFullName {
  givenName?: string
  familyName?: string
}

/** `fullName` 仅在用户首次授权时返回，后续登录传 null。 */
export function loginWithApple(
  idToken: string,
  fullName?: AppleFullName | null,
): Promise<UserPayload> {
  return request<UserPayload>('/auth/apple/', {
    method: 'POST',
    body: JSON.stringify({
      id_token: idToken,
      full_name: fullName || null,
    }),
  })
}

/**
 * `credential` 是 Google Identity Services 回调里的 ID token。
 * 显示名由后端从 token 的 given_name / family_name 中取，无需前端传。
 */
export function loginWithGoogle(credential: string): Promise<UserPayload> {
  return request<UserPayload>('/auth/google/', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  })
}
