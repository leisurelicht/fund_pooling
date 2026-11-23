import { request } from './client'

export interface HealthResponse {
  status: 'ok' | 'error'
  service: string
  version: string
  debug: boolean
  time: string
  database: {
    status: 'ok' | 'error'
    latency_ms: number
    error: string | null
  }
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health/')
}
