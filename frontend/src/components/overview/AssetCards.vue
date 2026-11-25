<script setup lang="ts">
import type { Summary } from '@/types/portfolio'

defineProps<{ summary: Summary | null; loading: boolean }>()

function num(v: string | undefined): number | null {
  if (v == null) return null
  const n = parseFloat(v)
  return Number.isNaN(n) ? null : n
}

function money(v: string | undefined): string {
  const n = num(v)
  if (n == null) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function signedMoney(v: string | undefined): string {
  const n = num(v)
  if (n == null) return '—'
  return `${n >= 0 ? '+' : ''}${money(v)}`
}

function signedPct(v: string | undefined): string {
  const n = num(v)
  if (n == null) return '—'
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

function tone(v: string | undefined): string {
  const n = num(v)
  if (n == null) return ''
  return n >= 0 ? 'is-up' : 'is-down'
}
</script>

<template>
  <section class="summary" :class="{ 'summary--loading': loading }">
    <div class="summary__metric summary__metric--hero">
      <span class="summary__label">总资产</span>
      <span class="summary__value">
        <span class="summary__unit">¥</span>{{ summary ? money(summary.total_market_value) : '—' }}
      </span>
    </div>

    <div class="summary__metric">
      <span class="summary__label">今日涨跌</span>
      <span class="summary__value" :class="tone(summary?.daily_gain)">
        {{ summary ? signedMoney(summary.daily_gain) : '—' }}
        <em v-if="summary" class="summary__pct">{{ signedPct(summary.daily_gain_pct) }}</em>
      </span>
    </div>

    <div class="summary__metric">
      <span class="summary__label">累计收益</span>
      <span class="summary__value" :class="tone(summary?.total_gain)">
        {{ summary ? signedMoney(summary.total_gain) : '—' }}
        <em v-if="summary" class="summary__pct">{{ signedPct(summary.total_gain_pct) }}</em>
      </span>
    </div>

    <div class="summary__metric">
      <span class="summary__label">持仓成本</span>
      <span class="summary__value summary__value--sm">
        <span class="summary__unit">¥</span>{{ summary ? money(summary.cost_basis) : '—' }}
      </span>
    </div>

    <div class="summary__metric">
      <span class="summary__label">在途金额</span>
      <span class="summary__value summary__value--sm">
        <span class="summary__unit">¥</span>{{ summary ? money(summary.in_transit) : '—' }}
      </span>
    </div>

    <div class="summary__metric">
      <span class="summary__label">持仓天数</span>
      <span class="summary__value summary__value--sm">
        {{ summary ? summary.holding_days : '—' }}<span v-if="summary" class="summary__unit summary__unit--suffix">天</span>
      </span>
    </div>
  </section>

  <p v-if="summary" class="summary__updated">
    更新于 {{ new Date(summary.price_updated_at).toLocaleTimeString('zh-CN', { hour12: false }) }}
  </p>
</template>

<style scoped>
.summary {
  display: grid;
  grid-template-columns: 1.3fr 1.2fr 1.2fr 1fr 1fr 0.9fr;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 28px 0;
}

.summary--loading {
  opacity: 0.65;
}

.summary__metric {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 28px;
  border-left: 1px solid var(--border);
  min-width: 0;
}

.summary__metric:first-child {
  border-left: none;
}

.summary__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.01em;
}

.summary__value {
  font-size: 21px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-strong);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  line-height: 1.25;
}

.summary__metric--hero .summary__value {
  font-size: 34px;
  font-weight: 650;
}

.summary__value--sm {
  font-size: 19px;
  font-weight: 550;
}

.summary__unit {
  font-size: 0.72em;
  font-weight: 500;
  color: var(--text-muted);
  margin-right: 1px;
}

.summary__unit--suffix {
  margin-right: 0;
  margin-left: 3px;
}

.summary__pct {
  font-style: normal;
  font-size: 14px;
  font-weight: 500;
  margin-left: 5px;
  opacity: 0.85;
}

.summary__value.is-up {
  color: var(--up);
}

.summary__value.is-down {
  color: var(--down);
}

.summary__updated {
  margin: 10px 4px 0;
  text-align: right;
  font-size: 12.5px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1180px) {
  .summary {
    grid-template-columns: repeat(3, 1fr);
    row-gap: 22px;
  }

  .summary__metric:nth-child(4) {
    border-left: none;
  }

  .summary__metric--hero .summary__value {
    font-size: 28px;
  }
}

@media (max-width: 720px) {
  .summary {
    grid-template-columns: repeat(2, 1fr);
  }

  .summary__metric:nth-child(odd) {
    border-left: none;
  }

  .summary__metric--hero .summary__value {
    font-size: 24px;
  }
}
</style>