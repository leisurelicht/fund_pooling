export type AssetType = 'stock' | 'mix' | 'bond' | 'money' | 'index' | 'qdii' | 'fof' | 'other'

export interface Asset {
  code: string
  name: string
  type: AssetType
  manager?: string
  risk_level?: string
  status: 'normal' | 'liquidated' | 'suspended'
}

export interface AssetPrice {
  price: number
  acc_price?: number
  daily_change?: number
  date: string
  source: 'auto' | 'manual'
}

export type ChannelType = 'third_party' | 'bank' | 'broker' | 'direct'

export interface Channel {
  id: number
  name: string
  type: ChannelType
  is_default: boolean
  is_archived: boolean
}

/* ---------- 交易 ---------- */

export type TransactionType =
  | 'buy'
  | 'sell'
  | 'cash_dividend'
  | 'reinvest_dividend'
  | 'share_adjustment'
  | 'opening_balance'

export type TransactionStatus = 'pending' | 'confirmed' | 'voided'
export type TransactionSource = 'manual' | 'import_csv' | 'sip'

export interface Transaction {
  id: number
  asset_code: string
  asset_name: string
  asset_type: AssetType
  channel_id: number
  channel_name: string
  type: TransactionType
  trade_date: string
  confirm_date?: string
  amount: string
  shares: string
  nav: string
  fee: string
  status: TransactionStatus
  source: TransactionSource
  notes?: string
}

/* ---------- 持仓行 ---------- */

export interface Position {
  asset_code: string
  asset_name: string
  asset_type: AssetType
  channel_id: number
  channel_name: string
  shares: string
  cost_per_share: string
  remaining_cost: string
  latest_price: string
  price_date: string
  market_value: string
  holding_gain: string
  holding_gain_pct: string
  realized_gain: string
  holding_days: number
  weight: string
  fee_total: string
}

/* ---------- 总览 ---------- */

export interface Summary {
  total_market_value: string
  daily_gain: string
  daily_gain_pct: string
  total_gain: string
  total_gain_pct: string
  cost_basis: string
  in_transit: string
  holding_days: number
  price_updated_at: string
}

/* ---------- 定投 ---------- */

export type SIPFrequency = 'weekly' | 'biweekly' | 'monthly'
export type SIPStatus = 'active' | 'paused' | 'ended'

export interface SIPPlan {
  id: number
  asset_code: string
  asset_name: string
  channel_id: number
  channel_name: string
  amount: string
  frequency: SIPFrequency
  deduction_day: number
  start_date: string
  end_type: 'unlimited' | 'by_count' | 'by_date'
  end_count?: number
  end_date?: string
  status: SIPStatus
  next_deduction_date?: string
  total_invested: string
}