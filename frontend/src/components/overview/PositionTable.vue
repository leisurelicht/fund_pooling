<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Position } from '@/types/portfolio'
import ColumnSettings from './ColumnSettings.vue'

const props = defineProps<{
  positions: Position[]
  viewMode: 'by_asset' | 'by_channel'
  sortKey: string
  sortDir: 'asc' | 'desc'
  visibleColumns: Set<string>
  totals: { market_value: string; remaining_cost: string; holding_gain: string; holding_gain_pct: string; count: number } | null
}>()

const emit = defineEmits<{
  sort: [key: string]
  'update:viewMode': [mode: 'by_asset' | 'by_channel']
  'toggle-col': [key: string]
  'reset-cols': []
}>()

const router = useRouter()
const showColSettings = ref(false)

const COLUMNS = [
  { key: 'asset_name', label: '资产', align: 'left' as const },
  { key: 'asset_type', label: '类型', align: 'left' as const },
  { key: 'channel_name', label: '渠道', align: 'left' as const },
  { key: 'shares', label: '份额', align: 'right' as const },
  { key: 'cost_per_share', label: '成本价', align: 'right' as const },
  { key: 'latest_price', label: '价格', align: 'right' as const },
  { key: 'market_value', label: '市值', align: 'right' as const },
  { key: 'holding_gain', label: '收益', align: 'right' as const },
  { key: 'holding_gain_pct', label: '收益率', align: 'right' as const },
  { key: 'realized_gain', label: '已实现收益', align: 'right' as const },
  { key: 'holding_days', label: '持有天数', align: 'right' as const },
  { key: 'weight', label: '占比', align: 'right' as const },
  { key: 'fee_total', label: '累计手续费', align: 'right' as const },
]

const visible = computed(() => COLUMNS.filter((c) => props.visibleColumns.has(c.key)))

function sortIndicator(key: string): string {
  if (props.sortKey !== key) return ''
  return props.sortDir === 'asc' ? ' ▲' : ' ▼'
}

function fmtCell(key: string, row: Position): string {
  const v = (row as unknown as Record<string, string>)[key]
  if (v == null) return '—'

  if (key === 'asset_type') {
    const labels: Record<string, string> = { stock: '股票型', mix: '混合型', bond: '债券型', money: '货币型', index: '指数型', qdii: 'QDII', fof: 'FOF', other: '其他' }
    return labels[v] ?? v
  }

  if (key === 'shares') {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '—'
    return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
  }

  if (key === 'cost_per_share' || key === 'latest_price') {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '—'
    return n.toFixed(4)
  }

  if (key === 'market_value' || key === 'fee_total' || key === 'realized_gain') {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '—'
    const sign = key === 'realized_gain' && n >= 0 ? '+' : ''
    return `${sign}${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  if (key === 'holding_gain') {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '—'
    return `${n >= 0 ? '+' : ''}${n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  if (key === 'holding_gain_pct') {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '—'
    return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
  }

  if (key === 'weight') {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '—'
    return `${n.toFixed(1)}%`
  }

  if (key === 'holding_days') {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '—'
    return `${n} 天`
  }

  return v
}

function money(v: string): string {
  const n = parseFloat(v)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function signedMoney(v: string): string {
  const n = parseFloat(v)
  return `${n >= 0 ? '+' : ''}${money(v)}`
}

function totalClass(key: string): string {
  if (key === 'holding_gain' || key === 'holding_gain_pct') {
    const raw = key === 'holding_gain' ? props.totals?.holding_gain : props.totals?.holding_gain_pct
    const n = parseFloat(raw ?? '0')
    return `ptable__td--total-gain ${n >= 0 ? 'up' : 'down'}`
  }
  return ''
}

function cellClass(key: string, row: Position): string {
  if (key === 'holding_gain' || key === 'holding_gain_pct') {
    const n = parseFloat((row as unknown as Record<string, string>)[key])
    return n >= 0 ? 'up' : 'down'
  }
  return ''
}

function goDetail(row: Position) {
  router.push(`/assets/${row.asset_code}`)
}
</script>

<template>
  <div class="ptable-wrap">
    <div class="ptable__toolbar">
      <div class="ptable__tabs">
        <button :class="['ptable__tab', { active: viewMode === 'by_asset' }]" @click="emit('update:viewMode', 'by_asset')">按资产</button>
        <button :class="['ptable__tab', { active: viewMode === 'by_channel' }]" @click="emit('update:viewMode', 'by_channel')">按渠道</button>
      </div>
      <div class="ptable__actions">
        <button class="ptable__action-btn" @click="showColSettings = !showColSettings">列设置</button>
        <ColumnSettings
          v-if="showColSettings"
          :columns="COLUMNS"
          :visible="visibleColumns"
          @toggle="emit('toggle-col', $event)"
          @reset="emit('reset-cols')"
          @close="showColSettings = false"
        />
      </div>
    </div>

    <div class="ptable__container">
      <table class="ptable">
        <thead>
          <tr>
            <th v-for="col in visible" :key="col.key" :class="['ptable__th', `ptable__th--${col.align}`]" @click="emit('sort', col.key)">
              {{ col.label }}<span class="ptable__sort">{{ sortIndicator(col.key) }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in positions" :key="`${row.asset_code}-${row.channel_id}`" class="ptable__row" @click="goDetail(row)">
            <td v-for="col in visible" :key="col.key" :class="['ptable__td', `ptable__td--${col.align}`, cellClass(col.key, row)]">
              {{ fmtCell(col.key, row) }}
            </td>
          </tr>
        </tbody>
        <tfoot v-if="totals">
          <tr class="ptable__totals">
            <td
              v-for="(col, index) in visible"
              :key="col.key"
              :class="['ptable__td', `ptable__td--${col.align}`, totalClass(col.key)]"
            >
              <template v-if="index === 0">合计 {{ totals.count }} 只</template>
              <template v-else-if="col.key === 'market_value'">¥{{ money(totals.market_value) }}</template>
              <template v-else-if="col.key === 'holding_gain'">{{ signedMoney(totals.holding_gain) }}</template>
              <template v-else-if="col.key === 'holding_gain_pct'">{{ signedMoney(totals.holding_gain_pct) }}%</template>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>

<style scoped>
.ptable-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ptable__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.ptable__tabs {
  display: flex;
  gap: 4px;
  background: var(--surface-muted);
  border-radius: 8px;
  padding: 3px;
}

.ptable__tab {
  padding: 6px 14px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.ptable__tab.active {
  background: var(--surface);
  color: var(--text-strong);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.ptable__actions {
  position: relative;
}

.ptable__action-btn {
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
}

.ptable__action-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.ptable__container {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}

.ptable {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ptable__th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 11px 14px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  font-weight: 500;
  font-size: 11.5px;
  letter-spacing: 0.02em;
  color: var(--text-muted);
  white-space: nowrap;
  cursor: pointer;
  user-select: none;
}

.ptable__th:hover {
  color: var(--text-strong);
}

.ptable__td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

.ptable__td:first-child {
  color: var(--text-strong);
  font-weight: 500;
}

.ptable__th--left, .ptable__td--left { text-align: left; }
.ptable__th--right, .ptable__td--right { text-align: right; }

.ptable__row {
  cursor: pointer;
  transition: background 0.1s ease;
}

.ptable__row:hover {
  background: var(--surface-muted);
}

.ptable__row:last-child .ptable__td {
  border-bottom: none;
}

.ptable__sort {
  font-size: 10px;
  color: var(--accent);
}

.ptable__td.up, .ptable__td.up .ptable__sort { color: var(--up); }
.ptable__td.down, .ptable__td.down .ptable__sort { color: var(--down); }

.ptable__totals .ptable__td {
  border-top: 1px solid var(--border-strong);
  border-bottom: none;
  background: var(--surface-muted);
  color: var(--text-strong);
  font-weight: 600;
}

.ptable__totals .ptable__td:first-child {
  font-weight: 500;
  color: var(--text-muted);
}

.ptable__td--total-gain.up { color: var(--up); }
.ptable__td--total-gain.down { color: var(--down); }

.ptable__td--bold {
  font-weight: 650;
}

.ptable__totals {
  position: sticky;
  bottom: 0;
}
</style>