import { computed, ref } from 'vue'
import type { Transaction } from '@/types/portfolio'
import { confirmTransaction, fetchTransactions, voidTransaction } from '@/api/portfolio'
import { ApiError } from '@/api/client'

export type TransactionFilter = 'all' | 'buy' | 'sell' | 'dividend'

export function useTransactions() {
  const all = ref<Transaction[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const filter = ref<TransactionFilter>('all')

  const pending = computed(() => all.value.filter((t) => t.status === 'pending'))

  const displayed = computed(() => {
    let list = [...all.value]
    if (filter.value === 'buy') list = list.filter((t) => t.type === 'buy')
    else if (filter.value === 'sell') list = list.filter((t) => t.type === 'sell')
    else if (filter.value === 'dividend') {
      list = list.filter((t) => t.type === 'cash_dividend' || t.type === 'reinvest_dividend')
    }
    return list.sort((a, b) => b.trade_date.localeCompare(a.trade_date))
  })

  async function fetch() {
    loading.value = true
    try {
      all.value = await fetchTransactions()
      error.value = null
    } catch (err) {
      all.value = []
      error.value = err instanceof ApiError ? err.message : '无法加载交易记录'
    } finally {
      loading.value = false
    }
  }

  async function confirm(id: number, shares: string, nav: string, fee?: string) {
    try {
      await confirmTransaction(id, { shares, nav, fee })
      await fetch()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '确认失败'
    }
  }

  async function voidTx(id: number) {
    try {
      await voidTransaction(id)
      await fetch()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '撤销失败'
    }
  }

  return { all, pending, displayed, filter, loading, error, fetch, confirm, voidTx }
}
