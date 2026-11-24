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
