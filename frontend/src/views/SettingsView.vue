<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ChannelManager from '@/components/settings/ChannelManager.vue'
import ErrorBanner from '@/components/shared/ErrorBanner.vue'
import { useChannels } from '@/composables/useChannels'
import { useTransactions } from '@/composables/useTransactions'

const {
  channels, error, fetch, setDefault, toggleArchive, addChannel, removeChannel,
} = useChannels()
const { all: transactions, error: txError, fetch: fetchTransactions } = useTransactions()
const bannerDismissed = ref(false)
const usageReady = ref(false)

/** 有未撤销交易引用的渠道不允许删除 */
const usedChannelIds = computed(() => [
  ...new Set(
    transactions.value.filter((t) => t.status !== 'voided').map((t) => t.channel_id),
  ),
])
const priceSyncEnabled = ref(true)
const theme = ref('system')
const greenUp = ref(false)

onMounted(async () => {
  fetch()
  await fetchTransactions()
  // 交易没加载成功就判断不出引用关系，保守起见禁止删除任何渠道
  usageReady.value = !txError.value
})

function toggleGreenUp() {
  greenUp.value = !greenUp.value
  document.documentElement.classList.toggle('green-up', greenUp.value)
  localStorage.setItem('green-up', String(greenUp.value))
}
</script>

<template>
  <div class="page">
    <h2>设置</h2>

    <ErrorBanner
      v-if="error && !bannerDismissed"
      :message="error"
      @dismiss="bannerDismissed = true"
    />

    <section style="margin-top: 24px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 12px;">渠道管理</h3>
      <ChannelManager
        :channels="channels"
        :used-channel-ids="usedChannelIds"
        :usage-ready="usageReady"
        @set-default="setDefault"
        @toggle-archive="toggleArchive"
        @create="addChannel"
        @delete="removeChannel"
      />
    </section>

    <section style="margin-top: 28px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 12px;">价格源</h3>
      <div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
        <label style="display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--text); cursor: pointer;">
          <input type="checkbox" v-model="priceSyncEnabled" /> 启用自动同步
        </label>
        <span style="font-size: 12px; color: var(--text-muted);">最后同步：刚刚</span>
        <button class="ghost-button">手动同步</button>
      </div>
    </section>

    <section style="margin-top: 28px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 12px;">外观</h3>
      <div style="display: flex; gap: 16px; flex-wrap: wrap; font-size: 14px;">
        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--text);">
          <input type="radio" v-model="theme" value="system" /> 跟随系统
        </label>
        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--text);">
          <input type="radio" v-model="theme" value="light" /> 浅色
        </label>
        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--text);">
          <input type="radio" v-model="theme" value="dark" /> 深色
        </label>
        <span style="border-left: 1px solid var(--border); margin: 0 4px;"></span>
        <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 14px; color: var(--text);">
          <input type="checkbox" :checked="greenUp" @change="toggleGreenUp" /> 绿涨红跌
        </label>
      </div>
    </section>

    <section style="margin-top: 28px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 12px;">数据</h3>
      <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        <button class="ghost-button">导出数据</button>
        <button class="ghost-button" style="color: var(--error); border-color: var(--error-soft);">清空所有数据</button>
      </div>
      <p style="font-size: 12px; color: var(--text-muted); margin: 10px 0 0;">
        导出为全部交易流水 CSV。导入交易记录请到交易页操作。
      </p>
    </section>

    <section style="margin-top: 28px;">
      <h3 style="font-size: 15px; font-weight: 650; color: var(--text-strong); margin: 0 0 12px;">提醒</h3>
      <p style="font-size: 13px; color: var(--text-muted); margin: 0;">定投扣款提醒等功能将在后续版本上线</p>
    </section>
  </div>
</template>