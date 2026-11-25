<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: [] }>()

const types = [
  { value: 'opening_balance', label: '初始持仓' },
  { value: 'buy', label: '买入' },
  { value: 'sell', label: '卖出' },
  { value: 'cash_dividend', label: '现金分红' },
  { value: 'reinvest_dividend', label: '红利再投' },
  { value: 'share_adjustment', label: '份额调整' },
]

const txType = ref('buy')
const assetCode = ref('')
const amount = ref('')
const shares = ref('')
const price = ref('')
const fee = ref('')

function submit() {
  console.log('record entry submit:', { type: txType.value, assetCode: assetCode.value, amount: amount.value, shares: shares.value, price: price.value, fee: fee.value })
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="re-overlay" @click.self="emit('close')">
      <div class="re-panel">
        <h3 class="re-title">记一笔</h3>

        <div class="re-field">
          <label class="re-label">类型</label>
          <select v-model="txType" class="re-input">
            <option v-for="t in types" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>

        <div class="re-field">
          <label class="re-label">资产代码</label>
          <input v-model="assetCode" class="re-input" placeholder="如 005827" />
        </div>

        <div v-if="txType !== 'opening_balance'" class="re-field">
          <label class="re-label">金额 / 份额（填一个即可）</label>
          <div class="re-row">
            <input v-model="amount" class="re-input re-input--half" placeholder="金额" />
            <input v-model="shares" class="re-input re-input--half" placeholder="份额" />
          </div>
        </div>

        <div v-if="txType === 'opening_balance'" class="re-field">
          <label class="re-label">份额</label>
          <input v-model="shares" class="re-input" placeholder="当前持有总份额" />
        </div>

        <div v-if="txType === 'opening_balance'" class="re-field">
          <label class="re-label">累计成本</label>
          <input v-model="amount" class="re-input" placeholder="累计投入总额" />
        </div>

        <div v-if="txType !== 'opening_balance' && txType !== 'cash_dividend' && txType !== 'share_adjustment'" class="re-field">
          <label class="re-label">价格</label>
          <input v-model="price" class="re-input" placeholder="成交净值" />
        </div>

        <div v-if="txType !== 'share_adjustment'" class="re-field">
          <label class="re-label">手续费</label>
          <input v-model="fee" class="re-input" placeholder="留空按费率估算" />
        </div>

        <div class="re-actions">
          <button class="re-btn re-btn--cancel" @click="emit('close')">取消</button>
          <button class="re-btn re-btn--primary" @click="submit">记一笔</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.re-overlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  background: rgba(0, 0, 0, 0.3);
  display: grid;
  place-items: center;
}

.re-panel {
  width: min(420px, 92vw);
  background: var(--surface);
  border-radius: 14px;
  padding: 28px;
  box-shadow: var(--shadow);
}

.re-title {
  margin: 0 0 20px;
  font-size: 18px;
  font-weight: 650;
  color: var(--text-strong);
}

.re-field {
  margin-bottom: 14px;
}

.re-label {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.re-input {
  width: 100%;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
  font-size: 14px;
  color: var(--text-strong);
  outline: none;
  transition: border-color 0.15s ease;
}

.re-input:focus {
  border-color: var(--accent);
}

.re-input::placeholder {
  color: var(--text-muted);
}

.re-row {
  display: flex;
  gap: 8px;
}

.re-input--half {
  flex: 1;
}

.re-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 20px;
}

.re-btn {
  padding: 9px 20px;
  border-radius: 8px;
  border: 1px solid var(--border);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.re-btn--cancel {
  background: var(--surface);
  color: var(--text);
}

.re-btn--cancel:hover {
  border-color: var(--border-strong);
}

.re-btn--primary {
  background: var(--accent);
  border-color: transparent;
  color: #fff;
}

.re-btn--primary:hover {
  opacity: 0.9;
}
</style>