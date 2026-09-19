/** Environments and the variables interpolated into requests. */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, ApiError } from '@/services/api'
import { useUiStore } from '@/stores/ui'
import type { Environment, Variable } from '@/types'

export const useEnvironmentsStore = defineStore('environments', () => {
  const ui = useUiStore()

  const environments = ref<Environment[]>([])
  const loading = ref(false)

  const active = computed(
    () => environments.value.find((item) => item.is_active) ?? null,
  )
  const activeId = computed(() => active.value?.id ?? null)

  /** Variable names available for autocomplete and highlighting. */
  const activeKeys = computed(
    () =>
      active.value?.variables
        .filter((variable) => variable.enabled && variable.key)
        .map((variable) => variable.key) ?? [],
  )

  async function load() {
    loading.value = true
    try {
      environments.value = await api.listEnvironments()
    } catch (error) {
      ui.toast(
        error instanceof ApiError
          ? error.message
          : 'Could not load environments',
        'error',
      )
    } finally {
      loading.value = false
    }
  }

  async function create(name: string) {
    const created = await api.createEnvironment({ name, variables: [] })
    await load()
    ui.toast(`Created "${created.name}"`, 'success')
    return created
  }

  async function update(id: string, patch: Partial<Environment>) {
    await api.updateEnvironment(id, patch)
    await load()
  }

  async function saveVariables(id: string, variables: Variable[]) {
    await api.updateEnvironment(id, { variables })
    await load()
    ui.toast('Variables saved', 'success')
  }

  async function activate(id: string | null) {
    if (id === null) await api.deactivateAllEnvironments()
    else await api.activateEnvironment(id)
    await load()
  }

  async function remove(id: string) {
    await api.deleteEnvironment(id)
    await load()
    ui.toast('Environment deleted', 'success')
  }

  return {
    environments,
    loading,
    active,
    activeId,
    activeKeys,
    load,
    create,
    update,
    saveVariables,
    activate,
    remove,
  }
})
