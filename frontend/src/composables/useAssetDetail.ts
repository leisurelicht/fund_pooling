import { ref } from 'vue'
import type { Asset, AssetPrice } from '@/types/portfolio'
import { fetchAsset, fetchAssetPrices } from '@/api/portfolio'
import { ApiError } from '@/api/client'

export function useAssetDetail(code: string) {
  const asset = ref<Asset | null>(null)
  const prices = ref<AssetPrice[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetch() {
    loading.value = true
    try {
      const [assetData, priceData] = await Promise.all([fetchAsset(code), fetchAssetPrices(code)])
      asset.value = assetData
      prices.value = priceData
      error.value = null
    } catch (err) {
      asset.value = null
      prices.value = []
      error.value = err instanceof ApiError ? err.message : '无法加载资产详情'
    } finally {
      loading.value = false
    }
  }

  return { asset, prices, loading, error, fetch }
}
