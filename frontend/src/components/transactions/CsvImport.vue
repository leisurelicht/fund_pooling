<script setup lang="ts">
defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: [] }>()

function handleDrop(e: DragEvent) {
  e.preventDefault()
  // S4: actual CSV parsing
  alert('CSV 导入将在后端就绪后实现')
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="ci-overlay" @click.self="emit('close')" @drop.prevent="handleDrop" @dragover.prevent>
      <div class="ci-panel">
        <h3 class="ci-title">导入交易记录</h3>
        <div class="ci-dropzone">
          <svg class="ci-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 16V4M8 8l4-4 4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
          </svg>
          <p style="margin: 0; font-size: 14px;">拖拽 CSV 文件到此处</p>
          <p style="color: var(--text-muted); font-size: 12px; margin: 4px 0 0;">支持：支付宝基金、天天基金交易记录</p>
        </div>
        <div class="ci-actions">
          <button class="ci-btn ci-btn--cancel" @click="emit('close')">取消</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ci-overlay { position: fixed; inset: 0; z-index: 500; background: rgba(0,0,0,0.3); display: grid; place-items: center; }
.ci-panel { width: min(460px, 92vw); background: var(--surface); border-radius: 14px; padding: 28px; box-shadow: var(--shadow); }
.ci-title { margin: 0 0 18px; font-size: 18px; font-weight: 650; color: var(--text-strong); }
.ci-icon { width: 28px; height: 28px; color: var(--text-muted); margin-bottom: 8px; }
.ci-dropzone { padding: 40px 20px; border: 2px dashed var(--border); border-radius: 10px; text-align: center; color: var(--text); transition: border-color 0.15s ease; }
.ci-dropzone:hover { border-color: var(--accent); }
.ci-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 18px; }
.ci-btn { padding: 9px 20px; border-radius: 8px; border: 1px solid var(--border); font-size: 14px; font-weight: 500; cursor: pointer; }
.ci-btn--cancel { background: var(--surface); color: var(--text); }
</style>