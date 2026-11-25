<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAssetDetail } from '@/composables/useAssetDetail'
import { usePositions } from '@/composables/usePositions'
import { useTransactions } from '@/composables/useTransactions'
import { computed } from 'vue'

const route = useRoute()
const code = route.params.code as string

const { asset, prices, loading: aLoading, error: assetError, fetch: fetchAsset } = useAssetDetail(code)
const { raw: positions } = usePositions()
const { displayed: txs } = useTransactions()

const myPositions = computed(() => positions.value.filter((p) => p.asset_code === code))
const myTxs = computed(() => txs.value.filter((t) => t.asset_code === code).slice(0, 10))

onMounted(async () => {
  await fetchAsset()
})

const typeLabels: Record<string, string> = { stock: '股票型', mix: '混合型', bond: '债券型', money: '货币型', index: '指数型', qdii: 'QDII', fof: 'FOF', other: '其他' }

function fmt(v: string, dec = 2): string {
  const n = parseFloat(v)
  if (isNaN(n)) return '—'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: dec, maximumFractionDigits: dec })
}
</script>

<template>
  <div class="page" v-if="asset">
    <div class="ad-header">
      <div>
        <h2>{{ asset.name }}</h2>
        <p style="color: var(--text-muted); font-size: 13px; margin: 0;">
          {{ typeLabels[asset.type] ?? asset.type }} · {{ asset.risk_level ?? '—' }}
          <span v-if="prices.length" style="margin-left: 12px;">最新净值 {{ prices[prices.length - 1].price }} ({{ prices[prices.length - 1].date }})</span>
        </p>
      </div>
    </div>

    <div v-if="myPositions.length" style="margin-top: 24px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 8px;">我的持仓</h3>
      <table class="ad-table">
        <thead><tr><th>渠道</th><th>份额</th><th>成本价</th><th>市值</th><th>收益</th></tr></thead>
        <tbody>
          <tr v-for="p in myPositions" :key="p.channel_id">
            <td>{{ p.channel_name }}</td>
            <td class="ad-num">{{ fmt(p.shares, 4) }}</td>
            <td class="ad-num">{{ fmt(p.cost_per_share, 4) }}</td>
            <td class="ad-num">¥{{ fmt(p.market_value) }}</td>
            <td class="ad-num" :class="parseFloat(p.holding_gain) >= 0 ? 'up' : 'down'">{{ parseFloat(p.holding_gain) >= 0 ? '+' : '' }}{{ fmt(p.holding_gain) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="prices.length" style="margin-top: 24px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 8px;">净值走势</h3>
      <div class="ad-chart">
        <svg viewBox="0 0 600 120" style="width: 100%; height: auto;">
          <polyline
            :points="prices.map((p, i) => `${(i / (prices.length - 1)) * 600},${120 - ((p.price - Math.min(...prices.map(x => x.price))) / (Math.max(...prices.map(x => x.price)) - Math.min(...prices.map(x => x.price)) || 1)) * 110}`).join(' ')"
            fill="none" stroke="var(--accent)" stroke-width="2"
          />
        </svg>
      </div>
    </div>

    <div v-if="myTxs.length" style="margin-top: 24px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 8px;">交易时间线</h3>
      <div class="ad-timeline">
        <div v-for="tx in myTxs" :key="tx.id" class="ad-tl-item">
          <span class="ad-tl-date">{{ tx.trade_date }}</span>
          <span>{{ { buy: '买入', sell: '卖出', cash_dividend: '现金分红', reinvest_dividend: '红利再投', share_adjustment: '份额调整', opening_balance: '初始持仓' }[tx.type] ?? tx.type }}</span>
          <span style="color: var(--text-muted);">{{ tx.channel_name }}</span>
          <span class="ad-num">¥{{ fmt(tx.amount) }}</span>
          <span class="ad-num">{{ fmt(tx.shares, 4) }} 份</span>
          <span>{{ { pending: '待确认', confirmed: '已确认', voided: '已撤销' }[tx.status] }}</span>
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="!aLoading" class="page">
    <p style="color: var(--text-muted);">{{ assetError ?? '未找到该资产' }}</p>
  </div>
</template>

<style scoped>
.ad-header { display: flex; justify-content: space-between; align-items: flex-start; }
.ad-table { width: 100%; border-collapse: collapse; font-size: 13px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.ad-table th { padding: 8px 10px; background: var(--surface-muted); border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text-muted); text-align: left; }
.ad-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); color: var(--text); }
.ad-num { font-family: var(--font-mono); text-align: right; }
.ad-num.up { color: var(--up); }
.ad-num.down { color: var(--down); }
.ad-chart { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
.ad-timeline { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.ad-tl-item { display: flex; align-items: center; gap: 16px; padding: 10px 14px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--text); }
.ad-tl-item:last-child { border-bottom: none; }
.ad-tl-date { font-weight: 600; color: var(--text-strong); min-width: 80px; }
</style>