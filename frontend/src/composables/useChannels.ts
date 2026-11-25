import { ref } from 'vue'
import type { Channel, ChannelType } from '@/types/portfolio'
import {
  createChannel as apiCreateChannel,
  deleteChannel as apiDeleteChannel,
  fetchChannels,
  updateChannel,
} from '@/api/portfolio'
import { ApiError } from '@/api/client'

export function useChannels() {
  const channels = ref<Channel[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch() {
    loading.value = true
    try {
      channels.value = await fetchChannels()
      error.value = null
    } catch (err) {
      channels.value = []
      error.value = err instanceof ApiError ? err.message : '无法加载渠道'
    } finally {
      loading.value = false
    }
  }

  async function setDefault(id: number) {
    try {
      await updateChannel(id, { is_default: true })
      await fetch()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '操作失败'
    }
  }

  async function toggleArchive(id: number) {
    const channel = channels.value.find((c) => c.id === id)
    if (!channel) return
    try {
      await updateChannel(id, { is_archived: !channel.is_archived })
      await fetch()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '操作失败'
    }
  }

  async function addChannel(name: string, type: ChannelType) {
    try {
      await apiCreateChannel({ name: name.trim(), type })
      await fetch()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '新建渠道失败'
    }
  }

  async function removeChannel(id: number) {
    try {
      await apiDeleteChannel(id)
      await fetch()
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : '删除渠道失败'
    }
  }

  return { channels, loading, error, fetch, setDefault, toggleArchive, addChannel, removeChannel }
}
