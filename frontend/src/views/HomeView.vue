<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import AssetCards from '@/components/overview/AssetCards.vue'
import PositionTable from '@/components/overview/PositionTable.vue'
import RecordEntry from '@/components/overview/RecordEntry.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import ErrorBanner from '@/components/shared/ErrorBanner.vue'
import { usePositions } from '@/composables/usePositions'
import { useSummary } from '@/composables/useSummary'

const {
  summary, loading: summaryLoading, error: summaryError, fetch: fetchSummary,
} = useSummary()
const {
  displayed, totals, viewMode, sortKey, sortDir,
  visibleColumns, loading: posLoading, error: posError,
  toggleColumn, resetColumns, setSort, fetch: fetchPositions,
} = usePositions()

const bannerDismissed = ref(false)
const banner = computed(() =>
  bannerDismissed.value ? null : (summaryError.value ?? posError.value),
)

const recordOpen = ref(false)
let timer: ReturnType<typeof setInterval> | undefined

async function loadAll() {
  await Promise.all([fetchSummary(), fetchPositions()])
}

onMounted(() => {
  loadAll()
  timer = setInterval(() => fetchSummary(), 60_000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const loading = computed(() => summaryLoading.value || posLoading.value)
</script>

<template>
  <div class="page">
    <ErrorBanner v-if="banner" :message="banner" @dismiss="bannerDismissed = true" />

    <AssetCards :summary="summary" :loading="loading" />

    <div style="height: 24px" />

    <div v-if="displayed.length > 0">
      <PositionTable
        :positions="displayed"
        :view-mode="viewMode"
        :sort-key="sortKey"
        :sort-dir="sortDir"
        :visible-columns="visibleColumns"
        :totals="totals"
        @sort="setSort"
        @update:view-mode="viewMode = $event"
        @toggle-col="toggleColumn"
        @reset-cols="resetColumns"
      />
    </div>

    <div v-else-if="!loading" style="padding-top: 40px;">
      <EmptyState
        title="还没有持仓"
        description="先创建渠道，再录入初始持仓或导入 CSV"
      />
    </div>

    <div class="fab" @click="recordOpen = true" title="记一笔">+</div>

    <RecordEntry :show="recordOpen" @close="recordOpen = false" />
  </div>
</template>


<style scoped>
.fab {
  position: fixed;
  bottom: 32px;
  right: 32px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 24px;
  display: grid;
  place-items: center;
  cursor: pointer;
  box-shadow: var(--shadow);
  z-index: 400;
  transition: transform 0.15s ease;
}

.fab:hover {
  transform: scale(1.08);
}
</style>