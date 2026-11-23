<script setup lang="ts">
defineProps<{
  title: string
  value: string
  hint?: string
  status?: 'ok' | 'error' | 'unknown'
}>()
</script>

<template>
  <article class="card" :data-status="status ?? 'unknown'">
    <header class="card__header">
      <span class="card__title">{{ title }}</span>
      <span class="card__dot" aria-hidden="true"></span>
    </header>
    <p class="card__value">{{ value }}</p>
    <p v-if="hint" class="card__hint">{{ hint }}</p>
  </article>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
  transition:
    border-color 0.2s ease,
    transform 0.2s ease;
}

.card:hover {
  border-color: var(--border-strong);
  transform: translateY(-2px);
}

.card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card__title {
  font-size: 13px;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.card__dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--text-muted);
}

.card[data-status='ok'] .card__dot {
  background: var(--ok);
  box-shadow: 0 0 0 4px var(--ok-soft);
}

.card[data-status='error'] .card__dot {
  background: var(--error);
  box-shadow: 0 0 0 4px var(--error-soft);
}

.card__value {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-strong);
  font-variant-numeric: tabular-nums;
}

.card__hint {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  word-break: break-all;
}
</style>
