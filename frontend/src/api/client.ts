const API_BASE = (import.meta.env.VITE_API_BASE ?? '/api').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * 统一的 JSON 请求封装。
 * 开发环境由 Vite 代理到 Django（见 vite.config.ts）。
 */
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...init.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, `接口请求失败（HTTP ${response.status}）`)
  }

  return (await response.json()) as T
}
