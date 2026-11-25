<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Channel, ChannelType } from '@/types/portfolio'

const props = defineProps<{ channels: Channel[]; usedChannelIds: number[]; usageReady: boolean }>()
const emit = defineEmits<{
  setDefault: [id: number]
  toggleArchive: [id: number]
  create: [name: string, type: ChannelType]
  delete: [id: number]
}>()

/**
 * 有交易引用的渠道不能删除，只能归档。
 * 交易数据没加载成功时无法判断引用关系，保守处理为全部已使用。
 */
const used = computed(() => {
  if (!props.usageReady) return new Set(props.channels.map((c) => c.id))
  return new Set(props.usedChannelIds)
})
const pendingDelete = ref<number | null>(null)

function requestDelete(id: number) {
  if (pendingDelete.value === id) {
    emit('delete', id)
    pendingDelete.value = null
    return
  }
  pendingDelete.value = id
}

const typeLabels: Record<string, string> = {
  third_party: '第三方平台',
  bank: '银行',
  broker: '券商',
  direct: '直销',
}

const types: { value: ChannelType; label: string }[] = [
  { value: 'third_party', label: '第三方平台' },
  { value: 'bank', label: '银行' },
  { value: 'broker', label: '券商' },
  { value: 'direct', label: '直销' },
]

const adding = ref(false)
const name = ref('')
const type = ref<ChannelType>('third_party')

function startAdd() {
  adding.value = true
  name.value = ''
  type.value = 'third_party'
}

function submit() {
  const trimmed = name.value.trim()
  if (!trimmed) return
  emit('create', trimmed, type.value)
  adding.value = false
  name.value = ''
}
</script>

<template>
  <div class="ch">
    <div class="ch__toolbar">
      <span class="ch__count">{{ channels.length }} 个渠道</span>
      <button v-if="!adding" class="ch__new" type="button" @click="startAdd">+ 新建渠道</button>
    </div>

    <form v-if="adding" class="ch__form" @submit.prevent="submit">
      <input
        v-model="name"
        class="ch__input"
        placeholder="渠道名称，如「支付宝-主账户」"
        maxlength="64"
        autofocus
      />
      <select v-model="type" class="ch__input ch__input--select">
        <option v-for="item in types" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <button class="ch__btn ch__btn--primary" type="submit" :disabled="!name.trim()">添加</button>
      <button class="ch__btn" type="button" @click="adding = false">取消</button>
    </form>

    <table v-if="channels.length" class="ch__table">
      <thead>
        <tr>
          <th>名称</th>
          <th>类型</th>
          <th>默认</th>
          <th>状态</th>
          <th class="ch__actions-head">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="ch in channels" :key="ch.id" :class="{ 'ch__row--archived': ch.is_archived }">
          <td class="ch__name">{{ ch.name }}</td>
          <td class="ch__muted">{{ typeLabels[ch.type] ?? ch.type }}</td>
          <td>
            <span v-if="ch.is_default" class="ch__badge">默认</span>
            <span v-else class="ch__muted">—</span>
          </td>
          <td>
            <span class="ch__badge" :class="{ 'ch__badge--muted': ch.is_archived }">
              {{ ch.is_archived ? '已归档' : '使用中' }}
            </span>
          </td>
          <td class="ch__actions">
            <button
              v-if="!ch.is_default && !ch.is_archived"
              class="ch__btn"
              type="button"
              @click="emit('setDefault', ch.id)"
            >
              设为默认
            </button>
            <button class="ch__btn" type="button" @click="emit('toggleArchive', ch.id)">
              {{ ch.is_archived ? '取消归档' : '归档' }}
            </button>
            <button
              v-if="!used.has(ch.id)"
              class="ch__btn ch__btn--danger"
              :class="{ 'ch__btn--confirm': pendingDelete === ch.id }"
              type="button"
              @click="requestDelete(ch.id)"
            >
              {{ pendingDelete === ch.id ? '确认删除' : '删除' }}
            </button>
            <span v-else class="ch__locked" title="该渠道已有交易记录，只能归档">已使用</span>
          </td>
        </tr>
      </tbody>
    </table>

    <p v-else class="ch__empty">还没有渠道，先新建一个再记账</p>
  </div>
</template>

<style scoped>
.ch {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ch__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ch__count {
  font-size: 12.5px;
  color: var(--text-muted);
}

.ch__new {
  padding: 6px 12px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    color 0.15s ease;
}

.ch__new:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.ch__form {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-muted);
}

.ch__input {
  flex: 1;
  min-width: 180px;
  padding: 8px 10px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 13px;
  color: var(--text-strong);
  outline: none;
}

.ch__input:focus {
  border-color: var(--accent);
}

.ch__input--select {
  flex: 0 0 auto;
  min-width: 120px;
}

.ch__btn {
  padding: 7px 14px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    color 0.15s ease,
    opacity 0.15s ease;
}

.ch__btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.ch__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ch__btn--primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.ch__btn--primary:hover:not(:disabled) {
  color: #fff;
  opacity: 0.9;
}

.ch__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

.ch__table th {
  padding: 9px 14px;
  text-align: left;
  font-size: 11.5px;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
}

.ch__table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}

.ch__table tr:last-child td {
  border-bottom: none;
}

.ch__name {
  color: var(--text-strong);
  font-weight: 500;
}

.ch__muted {
  color: var(--text-muted);
}

.ch__badge {
  display: inline-flex;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11.5px;
  color: var(--accent);
  background: var(--accent-soft);
}

.ch__badge--muted {
  color: var(--text-muted);
  background: var(--surface-muted);
}

.ch__row--archived .ch__name {
  color: var(--text-muted);
}

.ch__actions-head {
  text-align: right;
}

.ch__actions {
  text-align: right;
  white-space: nowrap;
}

.ch__actions .ch__btn {
  margin-left: 6px;
  padding: 4px 10px;
  font-size: 12.5px;
}

.ch__btn--danger {
  color: var(--error);
  border-color: var(--error-soft);
}

.ch__btn--danger:hover:not(:disabled) {
  border-color: var(--error);
  color: var(--error);
  background: var(--error-soft);
}

.ch__btn--confirm {
  color: #fff;
  border-color: var(--error);
  background: var(--error);
}

.ch__btn--confirm:hover:not(:disabled) {
  color: #fff;
  background: var(--error);
  opacity: 0.9;
}

.ch__locked {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.ch__empty {
  margin: 0;
  padding: 24px;
  border: 1px dashed var(--border);
  border-radius: 10px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}
</style>