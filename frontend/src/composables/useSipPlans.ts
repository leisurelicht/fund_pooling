import { ref } from 'vue'
import type { SIPPlan } from '@/types/portfolio'
import { fetchSipPlans, updateSipPlan } from '@/api/portfolio'
import { ApiError } from '@/api/client'

export function useSipPlans() {
  const plans = ref<SIPPlan[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch() {
    loading.value = true
    try {
      plans.value = await fetchSipPlans()
      error.value = null
    } catch (err) {
      plans.value = []
      error.value = err instanceof ApiError ? err.message : '无法加载定投计划'
    } finally {
      loading.value = false
    }
  }

  async function setStatus(id: number, status: SIPPlan['status']) {
    try {
      await updateSipPlan(id, { status })
      await fetch()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '操作失败'
    }
  }

  function toggle(id: number) {
    const plan = plans.value.find((p) => p.id === id)
    if (!plan) return
    return setStatus(id, plan.status === 'active' ? 'paused' : 'active')
  }

  function end(id: number) {
    return setStatus(id, 'ended')
  }

  return { plans, loading, error, fetch, toggle, end }
}
