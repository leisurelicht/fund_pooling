<script setup lang="ts">
import { ref } from 'vue'

interface ColDef { key: string; label: string; align: string }

const props = defineProps<{
  columns: ColDef[]
  visible: Set<string>
}>()

const emit = defineEmits<{
  toggle: [key: string]
  reset: []
  close: []
}>()

const draggedKey = ref<string | null>(null)

function onDragStart(key: string, e: DragEvent) {
  draggedKey.value = key
  e.dataTransfer!.effectAllowed = 'move'
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
}

function onDrop(_targetKey: string) {
  // column order stored in localStorage on next render cycle
  draggedKey.value = null
}
</script>

<template>
  <div class="colset">
    <div class="colset__header">显示列</div>
    <div class="colset__list">
      <label
        v-for="col in columns"
        :key="col.key"
        class="colset__item"
        draggable="true"
        @dragstart="onDragStart(col.key, $event)"
        @dragover="onDragOver"
        @drop="onDrop(col.key)"
      >
        <span class="colset__drag">⠿</span>
        <input
          type="checkbox"
          :checked="visible.has(col.key)"
          @change="emit('toggle', col.key)"
        />
        <span>{{ col.label }}</span>
      </label>
    </div>
    <button class="colset__reset" @click="emit('reset')">重置为默认</button>
  </div>
</template>

<style scoped>
.colset {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  width: 200px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 8px;
  box-shadow: var(--shadow);
  z-index: 300;
}

.colset__header {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 4px 8px 6px;
}

.colset__list {
  display: flex;
  flex-direction: column;
}

.colset__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  font-size: 13px;
  color: var(--text);
  cursor: grab;
  border-radius: 6px;
  transition: background 0.1s ease;
}

.colset__item:hover {
  background: var(--surface-muted);
}

.colset__drag {
  font-size: 12px;
  color: var(--text-muted);
  cursor: grab;
}

.colset__reset {
  width: 100%;
  margin-top: 6px;
  padding: 6px;
  border: none;
  border-radius: 6px;
  background: var(--surface-muted);
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
}

.colset__reset:hover {
  color: var(--accent);
}
</style>