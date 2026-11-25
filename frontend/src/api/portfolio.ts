import { request } from './client'
import type {
  Asset,
  AssetPrice,
  Channel,
  ChannelType,
  Position,
  SIPPlan,
  Summary,
  Transaction,
} from '@/types/portfolio'

/** 列表接口统一返回 { results: [...] }，便于日后加分页 */
interface ListResponse<T> {
  results: T[]
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

/* ---------- 总览 ---------- */

export function fetchSummary(): Promise<Summary> {
  return request<Summary>('/summary/')
}

/* ---------- 持仓 ---------- */

export function fetchPositions(group: 'asset' | 'channel' = 'asset'): Promise<Position[]> {
  return request<ListResponse<Position>>(`/positions/${query({ group })}`).then((data) => data.results)
}

/* ---------- 交易 ---------- */

export interface TransactionQuery {
  asset?: string
  channel?: number
  type?: string
  date_from?: string
  date_to?: string
}

export function fetchTransactions(params: TransactionQuery = {}): Promise<Transaction[]> {
  return request<ListResponse<Transaction>>(`/transactions/${query({ ...params })}`).then(
    (data) => data.results,
  )
}

export interface TransactionInput {
  asset_code: string
  channel_id: number
  type: string
  trade_date: string
  amount: string
  shares?: string
  nav?: string
  fee?: string
  notes?: string
}

export function createTransaction(payload: TransactionInput): Promise<Transaction> {
  return request<Transaction>('/transactions/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTransaction(id: number, payload: Partial<TransactionInput>): Promise<Transaction> {
  return request<Transaction>(`/transactions/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteTransaction(id: number): Promise<void> {
  return request<void>(`/transactions/${id}/`, { method: 'DELETE' })
}

export function confirmTransaction(
  id: number,
  payload: { shares: string; nav: string; fee?: string },
): Promise<Transaction> {
  return request<Transaction>(`/transactions/${id}/confirm/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function voidTransaction(id: number): Promise<Transaction> {
  return request<Transaction>(`/transactions/${id}/void/`, { method: 'POST' })
}

/* ---------- 渠道 ---------- */

export function fetchChannels(): Promise<Channel[]> {
  return request<ListResponse<Channel>>('/channels/').then((data) => data.results)
}

export function createChannel(payload: { name: string; type: ChannelType }): Promise<Channel> {
  return request<Channel>('/channels/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateChannel(
  id: number,
  payload: Partial<Pick<Channel, 'name' | 'is_default' | 'is_archived'>>,
): Promise<Channel> {
  return request<Channel>(`/channels/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteChannel(id: number): Promise<void> {
  return request<void>(`/channels/${id}/`, { method: 'DELETE' })
}

/* ---------- 定投 ---------- */

export function fetchSipPlans(): Promise<SIPPlan[]> {
  return request<ListResponse<SIPPlan>>('/sip-plans/').then((data) => data.results)
}

export interface SipPlanInput {
  asset_code: string
  channel_id: number
  amount: string
  frequency: string
  deduction_day: number
  start_date: string
  end_type: string
  end_count?: number
  end_date?: string
}

export function createSipPlan(payload: SipPlanInput): Promise<SIPPlan> {
  return request<SIPPlan>('/sip-plans/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSipPlan(id: number, payload: Partial<SipPlanInput & { status: string }>): Promise<SIPPlan> {
  return request<SIPPlan>(`/sip-plans/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/* ---------- 资产与价格 ---------- */

export function fetchAsset(code: string): Promise<Asset> {
  return request<Asset>(`/assets/${code}/`)
}

export function fetchAssetPrices(code: string, from?: string, to?: string): Promise<AssetPrice[]> {
  return request<ListResponse<AssetPrice>>(`/assets/${code}/prices/${query({ from, to })}`).then(
    (data) => data.results,
  )
}

export function syncPrices(): Promise<{ success: number; failed: number }> {
  return request<{ success: number; failed: number }>('/assets/sync/', { method: 'POST' })
}
