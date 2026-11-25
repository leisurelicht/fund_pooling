<script setup lang="ts">
import type { Transaction } from '@/types/portfolio'

defineProps<{ transactions: Transaction[]; filter: string }>()
const emit = defineEmits<{ 'update:filter': [v: string] }>()

const typeLabels: Record<string, string> = { buy: '买入', sell: '卖出', cash_dividend: '现金分红', reinvest_dividend: '红利再投', share_adjustment: '份额调整', opening_balance: '初始持仓' }
const sourceLabels: Record<string, string> = { sip: '定投', manual: '手动', import_csv: '导入' }
const statusLabels: Record<string, string> = { pending: '待确认', confirmed: '已确认', voided: '已撤销' }

function fmt(v: string, dec = 2): string {
  const n = parseFloat(v)
  if (isNaN(n)) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: dec, maximumFractionDigits: dec })
}
</script>

<template>
  <div class="ttable-wrap">
    <div class="ttable__filters">
      <button v-for="f in ['all', 'buy', 'sell', 'dividend']" :key="f"
        :class="['ttable__filter', { active: filter === f }]" @click="emit('update:filter', f)">
        {{ { all: '全部', buy: '买入', sell: '卖出', dividend: '分红' }[f] }}
      </button>
    </div>

    <table class="ttable">
      <thead>
        <tr>
          <th>日期</th><th>资产</th><th>类型</th><th>渠道</th><th>金额</th><th>份额</th><th>净值</th><th>手续费</th><th>来源</th><th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="tx in transactions" :key="tx.id">
          <td>{{ tx.trade_date }}</td>
          <td>{{ tx.asset_name }}</td>
          <td>{{ typeLabels[tx.type] ?? tx.type }}</td>
          <td>{{ tx.channel_name }}</td>
          <td class="ttable__num">¥{{ fmt(tx.amount) }}</td>
          <td class="ttable__num">{{ fmt(tx.shares, 4) }}</td>
          <td class="ttable__num">{{ fmt(tx.nav, 4) }}</td>
          <td class="ttable__num">¥{{ fmt(tx.fee) }}</td>
          <td><span class="ttable__tag">{{ sourceLabels[tx.source] ?? tx.source }}</span></td>
          <td><span class="ttable__badge" :class="`ttable__badge--${tx.status}`">{{ statusLabels[tx.status] ?? tx.status }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.ttable-wrap { }
.ttable__filters { display: flex; gap: 4px; margin-bottom: 12px; }
.ttable__filter { padding: 5px 12px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); font-size: 12px; color: var(--text-muted); cursor: pointer; }
.ttable__filter.active { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); font-weight: 600; }
.ttable { width: 100%; border-collapse: collapse; font-size: 13px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.ttable th { padding: 8px 10px; background: var(--surface-muted); border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text-muted); text-align: left; white-space: nowrap; }
.ttable td { padding: 8px 10px; border-bottom: 1px solid var(--border); color: var(--text); white-space: nowrap; }
.ttable__num { font-variant-numeric: tabular-nums; text-align: right; }
.ttable__tag {
  display: inline-flex;
  padding: 1px 6px;
  border-radius: 5px;
  border: 1px solid var(--border);
  font-size: 11.5px;
  color: var(--text-muted);
}
.ttable__badge {
  display: inline-flex;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
}
.ttable__badge--pending { color: var(--warning); background: var(--warning-soft); }
.ttable__badge--confirmed { color: var(--text-muted); background: var(--surface-muted); }
.ttable__badge--voided { color: var(--text-muted); background: transparent; opacity: 0.65; text-decoration: line-through; }
</style>