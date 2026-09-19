/**
 * Open request tabs and the send loop.
 *
 * A tab holds a working copy of a request so edits are never written straight
 * to the server. `dirty` tracks divergence from the saved version, which is
 * what drives the unsaved-changes dot and the save prompt on close.
 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, ApiError } from '@/services/api'
import { useCollectionsStore } from '@/stores/collections'
import { useEnvironmentsStore } from '@/stores/environments'
import { useUiStore } from '@/stores/ui'
import {
  emptyAuth,
  type HttpMethod,
  type RequestTab,
  type SavedRequest,
} from '@/types'

let tabCounter = 0

function newTabId() {
  return `tab-${++tabCounter}-${Date.now().toString(36)}`
}

/**
 * Deep-copy plain request data.
 *
 * `structuredClone` cannot be used here: values read out of the collections
 * store are Vue reactive Proxies, and cloning a Proxy raises DataCloneError.
 * Everything copied here is JSON-serialisable by construction.
 */
function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value ?? null)) as T
}

function blankTab(): RequestTab {
  return {
    tabId: newTabId(),
    requestId: null,
    collectionId: null,
    name: 'Untitled request',
    method: 'GET',
    url: '',
    headers: [],
    query_params: [],
    body_mode: 'none',
    body: '',
    form_data: [],
    auth: emptyAuth(),
    assertions: [],
    dirty: false,
    sending: false,
    response: null,
  }
}

function tabFromRequest(request: SavedRequest): RequestTab {
  return {
    tabId: newTabId(),
    requestId: request.id,
    collectionId: request.collection_id,
    name: request.name,
    method: request.method,
    url: request.url,
    headers: clone(request.headers ?? []),
    query_params: clone(request.query_params ?? []),
    body_mode: request.body_mode ?? 'none',
    body: request.body ?? '',
    form_data: clone(request.form_data ?? []),
    auth: { ...emptyAuth(), ...clone(request.auth ?? {}) },
    assertions: clone(request.assertions ?? []),
    dirty: false,
    sending: false,
    response: null,
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const ui = useUiStore()

  const tabs = ref<RequestTab[]>([])
  const activeTabId = ref<string | null>(null)

  const activeTab = computed(
    () => tabs.value.find((tab) => tab.tabId === activeTabId.value) ?? null,
  )

  function openBlank() {
    const tab = blankTab()
    tabs.value.push(tab)
    activeTabId.value = tab.tabId
    return tab
  }

  function openRequest(request: SavedRequest) {
    // Re-focus the tab if this request is already open.
    const existing = tabs.value.find((tab) => tab.requestId === request.id)
    if (existing) {
      activeTabId.value = existing.tabId
      return existing
    }
    const tab = tabFromRequest(request)
    tabs.value.push(tab)
    activeTabId.value = tab.tabId
    return tab
  }

  function closeTab(tabId: string) {
    const index = tabs.value.findIndex((tab) => tab.tabId === tabId)
    if (index < 0) return
    tabs.value.splice(index, 1)

    if (activeTabId.value === tabId) {
      const next = tabs.value[index] ?? tabs.value[index - 1] ?? null
      activeTabId.value = next?.tabId ?? null
    }
  }

  function selectTab(tabId: string) {
    activeTabId.value = tabId
  }

  function markDirty(tab: RequestTab) {
    tab.dirty = true
  }

  function setMethod(tab: RequestTab, method: HttpMethod) {
    tab.method = method
    markDirty(tab)
  }

  /** Send the active tab's request and store the response on the tab. */
  async function send(tab: RequestTab) {
    if (!tab.url.trim()) {
      ui.toast('Enter a URL first', 'error')
      return
    }

    const environments = useEnvironmentsStore()
    tab.sending = true

    try {
      tab.response = await api.send({
        name: tab.name,
        request_id: tab.requestId,
        method: tab.method,
        url: tab.url,
        headers: tab.headers,
        query_params: tab.query_params,
        body_mode: tab.body_mode,
        body: tab.body,
        form_data: tab.form_data,
        auth: tab.auth,
        assertions: tab.assertions,
        environment_id: environments.activeId,
        save_history: true,
      })

      if (!tab.response.ok) {
        ui.toast(tab.response.error ?? 'Request failed', 'error')
      }
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'Could not send the request'
      ui.toast(message, 'error')
      tab.response = null
    } finally {
      tab.sending = false
    }
  }

  /** Persist the tab into a collection. */
  async function save(tab: RequestTab, collectionId?: string) {
    const collections = useCollectionsStore()
    const target = collectionId ?? tab.collectionId

    if (!target) {
      ui.toast('Choose a collection to save into', 'error')
      return null
    }

    try {
      const saved = await collections.saveRequest(
        target,
        {
          name: tab.name,
          method: tab.method,
          url: tab.url,
          headers: tab.headers,
          query_params: tab.query_params,
          body_mode: tab.body_mode,
          body: tab.body,
          form_data: tab.form_data,
          auth: tab.auth,
          assertions: tab.assertions,
        },
        tab.requestId,
      )

      tab.requestId = saved.id
      tab.collectionId = saved.collection_id
      tab.dirty = false
      ui.toast(`Saved "${saved.name}"`, 'success')
      return saved
    } catch (error) {
      ui.toast(
        error instanceof ApiError ? error.message : 'Could not save',
        'error',
      )
      return null
    }
  }

  return {
    tabs,
    activeTabId,
    activeTab,
    openBlank,
    openRequest,
    closeTab,
    selectTab,
    markDirty,
    setMethod,
    send,
    save,
  }
})
