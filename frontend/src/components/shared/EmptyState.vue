<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="empty">
    <p class="empty__title">{{ title }}</p>
    <p v-if="description" class="empty__desc">{{ description }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 64px 24px;
  text-align: center;
  border: 1px dashed var(--border);
  border-radius: 12px;
  color: var(--text-muted);
}

.empty__title {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.empty__desc {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}
</style>