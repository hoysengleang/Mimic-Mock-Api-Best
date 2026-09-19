/** Collection runs, including looped iterations. */

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, ApiError } from '@/services/api'
import { useEnvironmentsStore } from '@/stores/environments'
import { useUiStore } from '@/stores/ui'
import type { RunResult, RunSummary } from '@/types'

export const useRunnerStore = defineStore('runner', () => {
  const ui = useUiStore()

  const running = ref(false)
  const current = ref<RunResult | null>(null)
  const recent = ref<RunSummary[]>([])

  // Run options, bound to the runner form.
  const iterations = ref(1)
  const delayMs = ref(0)
  const stopOnFailure = ref(false)

  async function loadRecent() {
    try {
      const page = await api.listRuns(25)
      recent.value = page.items
    } catch {
      // A failed history load should not block starting a run.
    }
  }

  async function run(collectionId: string) {
    const environments = useEnvironmentsStore()
    running.value = true

    try {
      current.value = await api.run({
        collection_id: collectionId,
        environment_id: environments.activeId,
        iterations: iterations.value,
        delay_ms: delayMs.value,
        stop_on_failure: stopOnFailure.value,
      })

      const result = current.value
      if (result.status === 'passed') {
        ui.toast(
          `All ${result.total_assertions} assertions passed`,
          'success',
        )
      } else {
        ui.toast(`${result.failed} assertion(s) failed`, 'error')
      }

      await loadRecent()
      return result
    } catch (error) {
      ui.toast(
        error instanceof ApiError ? error.message : 'Could not run collection',
        'error',
      )
      return null
    } finally {
      running.value = false
    }
  }

  async function open(runId: string) {
    try {
      current.value = await api.getRun(runId)
    } catch (error) {
      ui.toast(
        error instanceof ApiError ? error.message : 'Could not load that run',
        'error',
      )
    }
  }

  async function clear() {
    await api.clearRuns()
    recent.value = []
    current.value = null
    ui.toast('Run history cleared', 'success')
  }

  return {
    running,
    current,
    recent,
    iterations,
    delayMs,
    stopOnFailure,
    loadRecent,
    run,
    open,
    clear,
  }
})
