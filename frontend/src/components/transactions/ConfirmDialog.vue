<script setup lang="ts">
import { ref } from 'vue'
import type { Transaction } from '@/types/portfolio'

const props = defineProps<{ tx: Transaction | null; show: boolean }>()
const emit = defineEmits<{ close: []; confirm: [id: number, shares: string, nav: string, fee: string] }>()

const shares = ref('')
const nav = ref('')
const fee = ref('')

function open() {
  if (props.tx) {
    shares.value = props.tx.shares === '0.0000' ? '' : props.tx.shares
    nav.value = props.tx.nav === '0.0000' ? '' : props.tx.nav
    fee.value = props.tx.fee === '0.00' ? '' : props.tx.fee
  }
}

watch(() => props.tx, open, { immediate: true })

import { watch } from 'vue'
</script>

<template>
  <Teleport to="body">
    <div v-if="show && tx" class="cd-overlay" @click.self="emit('close')">
      <div class="cd-panel">
        <h3 class="cd-title">确认交易</h3>
        <p class="cd-subtitle">{{ tx.asset_name }} · {{ tx.channel_name }} · 定投买入  ¥{{ parseFloat(tx.amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</p>

        <div class="cd-field">
          <label class="cd-label">份额</label>
          <input v-model="shares" class="cd-input" type="number" step="0.01" placeholder="确认份额" />
        </div>
        <div class="cd-field">
          <label class="cd-label">净值</label>
          <input v-model="nav" class="cd-input" type="number" step="0.0001" placeholder="确认净值" />
        </div>
        <div class="cd-field">
          <label class="cd-label">手续费</label>
          <input v-model="fee" class="cd-input" type="number" step="0.01" placeholder="手续费" />
        </div>

        <div class="cd-hint">
          平台确认份额: {{ tx.shares }} · 平台确认净值: {{ tx.nav }}
        </div>

        <div class="cd-actions">
          <button class="cd-btn cd-btn--cancel" @click="emit('close')">取消</button>
          <button class="cd-btn cd-btn--primary" @click="emit('confirm', tx.id, shares, nav, fee)">确认</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.cd-overlay { position: fixed; inset: 0; z-index: 500; background: rgba(0,0,0,0.3); display: grid; place-items: center; }
.cd-panel { width: min(400px, 92vw); background: var(--surface); border-radius: 14px; padding: 28px; box-shadow: var(--shadow); }
.cd-title { margin: 0 0 4px; font-size: 18px; font-weight: 650; color: var(--text-strong); }
.cd-subtitle { margin: 0 0 18px; font-size: 13px; color: var(--text-muted); }
.cd-field { margin-bottom: 12px; }
.cd-label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.cd-input { width: 100%; padding: 9px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-muted); font-size: 14px; color: var(--text-strong); outline: none; }
.cd-input:focus { border-color: var(--accent); }
.cd-hint { font-size: 12px; color: var(--text-muted); margin-bottom: 16px; }
.cd-actions { display: flex; gap: 8px; justify-content: flex-end; }
.cd-btn { padding: 9px 20px; border-radius: 8px; border: 1px solid var(--border); font-size: 14px; font-weight: 500; cursor: pointer; }
.cd-btn--cancel { background: var(--surface); color: var(--text); }
.cd-btn--primary { background: var(--accent); border-color: transparent; color: #fff; }
</style>