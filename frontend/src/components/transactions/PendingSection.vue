<script setup lang="ts">
import type { Transaction } from '@/types/portfolio'

defineProps<{ pending: Transaction[] }>()
const emit = defineEmits<{ confirm: [id: number]; void: [id: number] }>()

const typeLabels: Record<string, string> = { buy: '买入', sell: '卖出', cash_dividend: '现金分红', reinvest_dividend: '红利再投', share_adjustment: '份额调整', opening_balance: '初始持仓' }
</script>

<template>
  <div v-if="pending.length > 0" class="pending">
    <div v-for="tx in pending" :key="tx.id" class="pending__row">
      <svg class="pending__dot" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M12 4l9 16H3zM12 10v4M12 17h.01" />
      </svg>
      <span class="pending__asset">{{ tx.asset_name }}</span>
      <span class="pending__type">{{ typeLabels[tx.type] ?? tx.type }}</span>
      <span class="pending__amount">¥{{ parseFloat(tx.amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</span>
      <span class="pending__status">待确认</span>
      <button class="pending__btn" @click="emit('confirm', tx.id)">确认</button>
    </div>
  </div>
</template>

<style scoped>
.pending {
  background: var(--surface);
  border: 1px solid var(--warning);
  border-radius: 10px;
  margin-bottom: 16px;
  overflow: hidden;
}

.pending__row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.pending__row:last-child { border-bottom: none; }

.pending__dot { width: 16px; height: 16px; flex-shrink: 0; color: var(--warning); }

.pending__asset { flex: 1; font-weight: 600; color: var(--text-strong); }

.pending__type { color: var(--text-muted); }

.pending__amount {
  font-family: var(--font-mono);
  color: var(--text-strong);
}

.pending__status {
  color: var(--warning);
  font-size: 12px;
}

.pending__btn {
  padding: 5px 14px;
  border-radius: 6px;
  border: 1px solid var(--accent);
  background: transparent;
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pending__btn:hover {
  background: var(--accent);
  color: #fff;
}
</style>