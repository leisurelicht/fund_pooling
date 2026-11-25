import { ref } from 'vue'
import type { Summary } from '@/types/portfolio'
import { fetchSummary } from '@/api/portfolio'
import { ApiError } from '@/api/client'

export function useSummary() {
  const summary = ref<Summary | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch() {
    loading.value = true
    try {
      summary.value = await fetchSummary()
      error.value = null
    } catch (err) {
      summary.value = null
      error.value = err instanceof ApiError ? err.message : '无法加载总览数据'
    } finally {
      loading.value = false
    }
  }

  return { summary, loading, error, fetch }
}
