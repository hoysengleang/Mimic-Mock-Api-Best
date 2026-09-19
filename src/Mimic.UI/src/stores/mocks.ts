/** Mock endpoint definitions served under /mock/*. */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, ApiError } from '@/services/api'
import { useUiStore } from '@/stores/ui'
import type { Mock } from '@/types'

export const useMocksStore = defineStore('mocks', () => {
  const ui = useUiStore()

  const mocks = ref<Mock[]>([])
  const loading = ref(false)
  const search = ref('')

  const filtered = computed(() => {
    const term = search.value.trim().toLowerCase()
    if (!term) return mocks.value
    return mocks.value.filter(
      (mock) =>
        mock.path.toLowerCase().includes(term) ||
        mock.name.toLowerCase().includes(term) ||
        mock.method.toLowerCase().includes(term),
    )
  })

  const enabledCount = computed(
    () => mocks.value.filter((mock) => mock.is_enabled).length,
  )
  const totalHits = computed(() =>
    mocks.value.reduce((sum, mock) => sum + (mock.hit_count ?? 0), 0),
  )

  async function load() {
    loading.value = true
    try {
      mocks.value = await api.listMocks()
    } catch (error) {
      ui.toast(
        error instanceof ApiError ? error.message : 'Could not load mocks',
        'error',
      )
    } finally {
      loading.value = false
    }
  }

  async function create(payload: Partial<Mock>) {
    const created = await api.createMock(payload)
    await load()
    ui.toast('Mock created', 'success')
    return created
  }

  async function update(id: string, payload: Partial<Mock>) {
    const updated = await api.updateMock(id, payload)
    await load()
    ui.toast('Mock saved', 'success')
    return updated
  }

  async function toggle(mock: Mock) {
    await api.toggleMock(mock.id)
    await load()
  }

  async function remove(id: string) {
    await api.deleteMock(id)
    await load()
    ui.toast('Mock deleted', 'success')
  }

  async function resetHits() {
    await api.resetMockHits()
    await load()
    ui.toast('Hit counters reset', 'success')
  }

  return {
    mocks,
    filtered,
    loading,
    search,
    enabledCount,
    totalHits,
    load,
    create,
    update,
    toggle,
    remove,
    resetHits,
  }
})
