import { computed, ref, watch } from 'vue'
import type { Position } from '@/types/portfolio'
import { fetchPositions } from '@/api/portfolio'
import { ApiError } from '@/api/client'

const DEFAULT_COLUMNS = [
  'asset_name', 'asset_type', 'channel_name', 'shares',
  'cost_per_share', 'latest_price', 'market_value', 'holding_gain',
]

export type ViewMode = 'by_asset' | 'by_channel'

export function usePositions() {
  const raw = ref<Position[]>([])
  const viewMode = ref<ViewMode>('by_asset')
  const sortKey = ref('market_value')
  const sortDir = ref<'asc' | 'desc'>('desc')
  const visibleColumns = ref<Set<string>>(new Set(DEFAULT_COLUMNS))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const byAsset = computed(() => {
    const map = new Map<string, Position>()
    for (const p of raw.value) {
      const key = p.asset_code
      const existing = map.get(key)
      if (!existing) {
        map.set(key, { ...p })
      } else {
        map.set(key, mergePositions(existing, p))
      }
    }
    return [...map.values()]
  })

  const displayed = computed(() => {
    const list = viewMode.value === 'by_asset' ? byAsset.value : [...raw.value]
    const sgn = sortDir.value === 'asc' ? 1 : -1
    return [...list].sort((a, b) => {
      const va = parseFloat((a as unknown as Record<string, string>)[sortKey.value] ?? '0')
      const vb = parseFloat((b as unknown as Record<string, string>)[sortKey.value] ?? '0')
      return (va - vb) * sgn
    })
  })

  const totals = computed(() => {
    const list = displayed.value
    if (list.length === 0) return null
    const mv = list.reduce((s, p) => s + parseFloat(p.market_value), 0)
    const rc = list.reduce((s, p) => s + parseFloat(p.remaining_cost), 0)
    const hg = list.reduce((s, p) => s + parseFloat(p.holding_gain), 0)
    const pct = rc !== 0 ? `${((hg / rc) * 100).toFixed(2)}` : '0.00'
    return { market_value: mv.toFixed(2), remaining_cost: rc.toFixed(2), holding_gain: hg.toFixed(2), holding_gain_pct: pct, count: list.length }
  })

  function toggleColumn(key: string) {
    const next = new Set(visibleColumns.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    visibleColumns.value = next
  }

  function resetColumns() {
    visibleColumns.value = new Set(DEFAULT_COLUMNS)
  }

  function setSort(key: string) {
    if (sortKey.value === key) {
      sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortKey.value = key
      sortDir.value = 'desc'
    }
  }

  watch(viewMode, () => {
    void fetch()
  })

  async function fetch() {
    loading.value = true
    try {
      raw.value = await fetchPositions(viewMode.value === 'by_asset' ? 'asset' : 'channel')
      error.value = null
    } catch (err) {
      raw.value = []
      error.value = err instanceof ApiError ? err.message : '无法加载持仓'
    } finally {
      loading.value = false
    }
  }

  return { raw, viewMode, sortKey, sortDir, displayed, totals, visibleColumns, loading, error, toggleColumn, resetColumns, setSort, fetch }
}

function mergePositions(a: Position, b: Position): Position {
  const mv = parseFloat(a.market_value) + parseFloat(b.market_value)
  const rc = parseFloat(a.remaining_cost) + parseFloat(b.remaining_cost)
  const hg = parseFloat(a.holding_gain) + parseFloat(b.holding_gain)
  const shares = parseFloat(a.shares) + parseFloat(b.shares)
  return {
    ...a,
    channel_id: 0,
    channel_name: '多渠道',
    shares: shares.toFixed(4),
    cost_per_share: shares > 0 ? (rc / shares).toFixed(4) : '0.0000',
    remaining_cost: rc.toFixed(2),
    market_value: mv.toFixed(2),
    holding_gain: hg.toFixed(2),
    holding_gain_pct: rc > 0 ? `${((hg / rc) * 100).toFixed(2)}` : '0.00',
    holding_days: Math.max(a.holding_days, b.holding_days),
    realized_gain: (parseFloat(a.realized_gain) + parseFloat(b.realized_gain)).toFixed(2),
    weight: '',
    fee_total: (parseFloat(a.fee_total) + parseFloat(b.fee_total)).toFixed(2),
  }
}