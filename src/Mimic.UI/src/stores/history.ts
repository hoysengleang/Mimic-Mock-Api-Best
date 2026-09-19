/** Past request executions. */

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, ApiError } from '@/services/api'
import { useUiStore } from '@/stores/ui'
import type { HistoryEntry } from '@/types'

export const useHistoryStore = defineStore('history', () => {
  const ui = useUiStore()

  const entries = ref<HistoryEntry[]>([])
  const total = ref(0)
  const loading = ref(false)
  const selected = ref<HistoryEntry | null>(null)

  async function load(limit = 100) {
    loading.value = true
    try {
      const page = await api.listHistory(limit)
      entries.value = page.items
      total.value = page.total
    } catch (error) {
      ui.toast(
        error instanceof ApiError ? error.message : 'Could not load history',
        'error',
      )
    } finally {
      loading.value = false
    }
  }

  async function remove(id: string) {
    await api.deleteHistoryEntry(id)
    entries.value = entries.value.filter((entry) => entry.id !== id)
    if (selected.value?.id === id) selected.value = null
  }

  async function clear() {
    await api.clearHistory()
    entries.value = []
    total.value = 0
    selected.value = null
    ui.toast('History cleared', 'success')
  }

  return { entries, total, loading, selected, load, remove, clear }
})
