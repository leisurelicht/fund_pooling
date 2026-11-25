<script setup lang="ts">
defineProps<{ message: string | null }>()
const emit = defineEmits<{ dismiss: [] }>()
</script>

<template>
  <div v-if="message" class="banner" role="alert">
    <span class="banner__text">{{ message }}</span>
    <button class="banner__close" type="button" aria-label="关闭" @click="emit('dismiss')">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
        <path d="M6 6l12 12M18 6L6 18" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid var(--warning-soft);
  background: var(--warning-soft);
  font-size: 13px;
  color: var(--warning);
}

.banner__text {
  flex: 1;
  min-width: 0;
}

.banner__close {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  opacity: 0.75;
}

.banner__close:hover {
  opacity: 1;
}

.banner__close svg {
  width: 13px;
  height: 13px;
}
</style>