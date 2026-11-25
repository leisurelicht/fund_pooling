<script setup lang="ts">
import { onMounted, ref } from 'vue'
import PendingSection from '@/components/transactions/PendingSection.vue'
import TransactionTable from '@/components/transactions/TransactionTable.vue'
import ConfirmDialog from '@/components/transactions/ConfirmDialog.vue'
import CsvImport from '@/components/transactions/CsvImport.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import ErrorBanner from '@/components/shared/ErrorBanner.vue'
import { useTransactions } from '@/composables/useTransactions'

const { pending, displayed, filter, loading, error, fetch, confirm } = useTransactions()
const bannerDismissed = ref(false)
const confirmTarget = ref<any>(null)
const showConfirm = ref(false)
const showCsv = ref(false)

onMounted(() => fetch())

function openConfirm(tx: any) { confirmTarget.value = tx; showConfirm.value = true }
async function handleConfirm(id: number, shares: string, nav: string, fee: string) {
  showConfirm.value = false
  await confirm(id, shares, nav, fee)
}
</script>

<template>
  <div class="page">
    <ErrorBanner
      v-if="error && !bannerDismissed"
      :message="error"
      @dismiss="bannerDismissed = true"
    />

    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h2>交易记录</h2>
      <button class="ghost-button" @click="showCsv = true">导入 CSV</button>
    </div>

    <div v-if="displayed.length > 0">
      <PendingSection :pending="pending" @confirm="openConfirm" />
      <TransactionTable :transactions="displayed" :filter="filter" @update:filter="(v: string) => filter = v as 'all' | 'buy' | 'sell' | 'dividend'" />
    </div>

    <EmptyState v-else-if="!loading" title="暂无交易记录" description="通过定投自动记录、手动录入或导入 CSV 开始记账" />

    <ConfirmDialog :tx="confirmTarget" :show="showConfirm" @close="showConfirm = false" @confirm="handleConfirm" />
    <CsvImport :show="showCsv" @close="showCsv = false" />
  </div>
</template>