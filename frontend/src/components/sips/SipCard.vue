<script setup lang="ts">
import type { SIPPlan } from '@/types/portfolio'

defineProps<{ plan: SIPPlan }>()
const emit = defineEmits<{ toggle: [id: number]; end: [id: number]; edit: [id: number] }>()

const freqLabels: Record<string, string> = { weekly: '每周', biweekly: '双周', monthly: '每月' }
const dayLabel = (plan: SIPPlan) => plan.frequency === 'monthly' ? `${plan.deduction_day} 日` : `周${'一二三四五六日'[plan.deduction_day - 1] ?? '?'}`
</script>

<template>
  <div class="sipcard">
    <div class="sipcard__header">
      <span class="sipcard__name">{{ plan.asset_name }}</span>
      <span class="sipcard__channel">· {{ plan.channel_name }}</span>
    </div>
    <div class="sipcard__body">
      <div class="sipcard__stat">
        <span class="sipcard__label">每期</span>
        <span class="sipcard__value">¥{{ parseFloat(plan.amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</span>
      </div>
      <div class="sipcard__stat">
        <span class="sipcard__label">周期</span>
        <span class="sipcard__value">{{ freqLabels[plan.frequency] ?? plan.frequency }} {{ dayLabel(plan) }}</span>
      </div>
      <div class="sipcard__stat" v-if="plan.next_deduction_date">
        <span class="sipcard__label">下次扣款</span>
        <span class="sipcard__value">{{ plan.next_deduction_date }}</span>
      </div>
      <div class="sipcard__stat">
        <span class="sipcard__label">累计已投</span>
        <span class="sipcard__value">¥{{ parseFloat(plan.total_invested).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</span>
      </div>
    </div>
    <div class="sipcard__footer">
      <span class="sipcard__status">
        <span class="sipcard__dot" :class="`sipcard__dot--${plan.status}`"></span>
        {{ { active: '进行中', paused: '已暂停', ended: '已结束' }[plan.status] }}
      </span>
      <div class="sipcard__actions">
        <button v-if="plan.status === 'active'" class="sipcard__btn" @click="emit('toggle', plan.id)">暂停</button>
        <button v-if="plan.status === 'paused'" class="sipcard__btn" @click="emit('toggle', plan.id)">恢复</button>
        <button v-if="plan.status !== 'ended'" class="sipcard__btn" @click="emit('end', plan.id)">结束</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sipcard { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; display: flex; flex-direction: column; gap: 12px; }
.sipcard__header { display: flex; align-items: center; gap: 4px; }
.sipcard__name { font-size: 15px; font-weight: 650; color: var(--text-strong); }
.sipcard__channel { font-size: 13px; color: var(--text-muted); }
.sipcard__body { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sipcard__stat { display: flex; flex-direction: column; gap: 2px; }
.sipcard__label { font-size: 11px; color: var(--text-muted); }
.sipcard__value { font-size: 14px; color: var(--text-strong); font-family: var(--font-mono); }
.sipcard__footer { display: flex; justify-content: space-between; align-items: center; padding-top: 8px; border-top: 1px solid var(--border); }
.sipcard__status { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text); }
.sipcard__dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; background: var(--text-muted); }
.sipcard__dot--active { background: var(--ok); }
.sipcard__dot--paused { background: var(--warning); }
.sipcard__dot--ended { background: var(--border-strong); }
.sipcard__actions { display: flex; gap: 6px; }
.sipcard__btn { padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-muted); font-size: 12px; color: var(--text); cursor: pointer; }
.sipcard__btn:hover { border-color: var(--accent); color: var(--accent); }
</style>