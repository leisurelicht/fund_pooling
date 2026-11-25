<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: [] }>()

const asset = ref('')
const amount = ref('')
const frequency = ref('monthly')
const deductionDay = ref(15)
const startDate = ref('')

function submit() {
  alert('新建定投将在后端就绪后实现')
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="sf-overlay" @click.self="emit('close')">
      <div class="sf-panel">
        <h3 class="sf-title">新建定投计划</h3>

        <div class="sf-field">
          <label class="sf-label">资产代码</label>
          <input v-model="asset" class="sf-input" placeholder="如 005827" />
        </div>
        <div class="sf-field">
          <label class="sf-label">每期金额</label>
          <input v-model="amount" class="sf-input" type="number" placeholder="2000" />
        </div>
        <div class="sf-field">
          <label class="sf-label">周期</label>
          <select v-model="frequency" class="sf-input">
            <option value="weekly">每周</option>
            <option value="biweekly">双周</option>
            <option value="monthly">每月</option>
          </select>
        </div>
        <div class="sf-field">
          <label class="sf-label">扣款日</label>
          <input v-model.number="deductionDay" class="sf-input" type="number" :min="1" :max="frequency === 'monthly' ? 28 : 7" :placeholder="frequency === 'monthly' ? '1–28' : '1=周一, 7=周日'" />
        </div>
        <div class="sf-field">
          <label class="sf-label">开始日期</label>
          <input v-model="startDate" class="sf-input" type="date" />
        </div>

        <div class="sf-actions">
          <button class="sf-btn sf-btn--cancel" @click="emit('close')">取消</button>
          <button class="sf-btn sf-btn--primary" @click="submit">创建计划</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.sf-overlay { position: fixed; inset: 0; z-index: 500; background: rgba(0,0,0,0.3); display: grid; place-items: center; }
.sf-panel { width: min(420px, 92vw); background: var(--surface); border-radius: 14px; padding: 28px; box-shadow: var(--shadow); }
.sf-title { margin: 0 0 18px; font-size: 18px; font-weight: 650; color: var(--text-strong); }
.sf-field { margin-bottom: 12px; }
.sf-label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.sf-input { width: 100%; padding: 9px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-muted); font-size: 14px; color: var(--text-strong); outline: none; }
.sf-input:focus { border-color: var(--accent); }
.sf-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 18px; }
.sf-btn { padding: 9px 20px; border-radius: 8px; border: 1px solid var(--border); font-size: 14px; font-weight: 500; cursor: pointer; }
.sf-btn--cancel { background: var(--surface); color: var(--text); }
.sf-btn--primary { background: var(--accent); border-color: transparent; color: #fff; }
</style>