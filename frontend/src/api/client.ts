const API_BASE = (import.meta.env.VITE_API_BASE ?? '/api').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** 从 Cookie 读取 Django 的 CSRF token。 */
export function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

/** 首次访问（例如直接打开 Vite 开发服务器）时补拿 CSRF Cookie。 */
async function ensureCsrfToken(): Promise<string | null> {
  let token = getCsrfToken()
  if (token) return token

  await fetch(`${API_BASE}/auth/csrf/`, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  })
  token = getCsrfToken()
  return token
}

/**
 * 统一的 JSON 请求封装：
 * - 自动带上 X-CSRFToken（POST / PUT / PATCH / DELETE）
 * - 统一解析后端 {detail: "..."} 错误信息
 * - 开发环境由 Vite 代理到 Django（见 vite.config.ts）
 */
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const token = await ensureCsrfToken()
    if (token) headers.set('X-CSRFToken', token)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    credentials: 'same-origin',
    ...init,
    method,
    headers,
  })

  if (!response.ok) {
    let message = `接口请求失败（HTTP ${response.status}）`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body?.detail) message = body.detail
    } catch {
      // 非 JSON 响应，保留默认提示
    }
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
