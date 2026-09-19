/** The collection tree shown in the sidebar. */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, ApiError } from '@/services/api'
import type { CollectionDetail, SavedRequest } from '@/types'
import { useUiStore } from '@/stores/ui'

export const useCollectionsStore = defineStore('collections', () => {
  const ui = useUiStore()

  const collections = ref<CollectionDetail[]>([])
  const loading = ref(false)
  const expanded = ref<Set<string>>(new Set())
  const search = ref('')

  const allRequests = computed<SavedRequest[]>(() =>
    collections.value.flatMap((collection) => collection.requests),
  )

  /** Collections filtered by the sidebar search box. */
  const filtered = computed(() => {
    const term = search.value.trim().toLowerCase()
    if (!term) return collections.value

    return collections.value
      .map((collection) => ({
        ...collection,
        requests: collection.requests.filter(
          (request) =>
            request.name.toLowerCase().includes(term) ||
            request.url.toLowerCase().includes(term) ||
            request.method.toLowerCase().includes(term),
        ),
      }))
      .filter(
        (collection) =>
          collection.requests.length > 0 ||
          collection.name.toLowerCase().includes(term),
      )
  })

  async function load() {
    loading.value = true
    try {
      // One call returns collections, folders and requests together. This
      // used to be an index call followed by one call per collection, which
      // was roughly four times slower.
      const details = await api.listCollections()
      collections.value = details
      // Open everything the first time so the app never looks empty.
      if (expanded.value.size === 0) {
        details.forEach((item) => expanded.value.add(item.id))
      }
    } catch (error) {
      ui.toast(
        error instanceof ApiError ? error.message : 'Could not load collections',
        'error',
      )
    } finally {
      loading.value = false
    }
  }

  async function refreshOne(collectionId: string) {
    try {
      const detail = await api.getCollection(collectionId)
      const index = collections.value.findIndex((c) => c.id === collectionId)
      if (index >= 0) collections.value[index] = detail
      else collections.value.push(detail)
    } catch {
      await load()
    }
  }

  function toggleExpanded(id: string) {
    if (expanded.value.has(id)) expanded.value.delete(id)
    else expanded.value.add(id)
    // Reassign so Vue tracks the change to the Set.
    expanded.value = new Set(expanded.value)
  }

  async function createCollection(name: string) {
    const created = await api.createCollection({ name })
    expanded.value = new Set(expanded.value).add(created.id)
    await refreshOne(created.id)
    ui.toast(`Created "${created.name}"`, 'success')
    return created
  }

  async function renameCollection(id: string, name: string) {
    await api.updateCollection(id, { name })
    await refreshOne(id)
  }

  async function deleteCollection(id: string) {
    await api.deleteCollection(id)
    collections.value = collections.value.filter((item) => item.id !== id)
    ui.toast('Collection deleted', 'success')
  }

  async function saveRequest(
    collectionId: string,
    payload: Partial<SavedRequest>,
    requestId: string | null,
  ): Promise<SavedRequest> {
    const saved = requestId
      ? await api.updateRequest(requestId, payload)
      : await api.createRequest(collectionId, payload)
    await refreshOne(collectionId)
    return saved
  }

  async function deleteRequest(request: SavedRequest) {
    await api.deleteRequest(request.id)
    await refreshOne(request.collection_id)
    ui.toast('Request deleted', 'success')
  }

  async function duplicateRequest(request: SavedRequest) {
    const clone = await api.duplicateRequest(request.id)
    await refreshOne(request.collection_id)
    return clone
  }

  return {
    collections,
    filtered,
    allRequests,
    loading,
    expanded,
    search,
    load,
    refreshOne,
    toggleExpanded,
    createCollection,
    renameCollection,
    deleteCollection,
    saveRequest,
    deleteRequest,
    duplicateRequest,
  }
})
