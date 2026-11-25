<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SipCard from '@/components/sips/SipCard.vue'
import SipForm from '@/components/sips/SipForm.vue'
import EmptyState from '@/components/shared/EmptyState.vue'
import ErrorBanner from '@/components/shared/ErrorBanner.vue'
import { useSipPlans } from '@/composables/useSipPlans'

const { plans, loading, error, fetch, toggle, end } = useSipPlans()
const showForm = ref(false)
const bannerDismissed = ref(false)

onMounted(() => fetch())
</script>

<template>
  <div class="page">
    <ErrorBanner
      v-if="error && !bannerDismissed"
      :message="error"
      @dismiss="bannerDismissed = true"
    />

    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
      <h2>定投计划</h2>
      <button class="ghost-button" @click="showForm = true">+ 新建定投计划</button>
    </div>

    <div v-if="plans.length" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
      <SipCard v-for="p in plans" :key="p.id" :plan="p" @toggle="toggle" @end="end" />
    </div>

    <EmptyState v-else-if="!loading" title="暂无定投计划" description="新建定投计划，扣款日自动生成待确认交易" />

    <SipForm :show="showForm" @close="showForm = false" />
  </div>
</template>