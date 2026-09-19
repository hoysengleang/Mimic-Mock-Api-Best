<script setup lang="ts">
import { computed, ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import CodeEditor from '@/components/common/CodeEditor.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useUiStore } from '@/stores/ui'
import type { ExecuteResponse } from '@/types'

const props = defineProps<{ response: ExecuteResponse | null; sending: boolean }>()

const ui = useUiStore()

type View = 'body' | 'headers' | 'tests'
const view = ref<View>('body')
const wrapped = ref(true)

const prettyBody = computed(() => {
  const raw = props.response?.body ?? ''
  if (!props.response?.is_json || !raw) return raw
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
})

const headerCount = computed(
  () => Object.keys(props.response?.headers ?? {}).length,
)

const assertionSummary = computed(() => {
  if (!props.response) return null
  const { assertions_passed: passed, assertions_failed: failed } = props.response
  if (passed + failed === 0) return null
  return { passed, failed, total: passed + failed }
})

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

async function copyBody() {
  try {
    await navigator.clipboard.writeText(prettyBody.value)
    ui.toast('Response copied', 'success')
  } catch {
    ui.toast('Could not access the clipboard', 'error')
  }
}

const editorLanguage = computed<'json' | 'text'>(() =>
  props.response?.is_json ? 'json' : 'text',
)
</script>

<template>
  <section class="response">
    <!-- Waiting -->
    <div v-if="sending" class="response__center">
      <span class="spinner spinner--lg" />
      <p class="response__waiting">Sending request…</p>
    </div>

    <!-- Nothing yet -->
    <div v-else-if="!response" class="empty-state">
      <AppIcon name="response" :size="26" class="empty-state__icon" :stroke="1.4" />
      <p class="empty-state__title">No response yet</p>
      <p class="empty-state__hint">
        Press <kbd>Send</kbd> to run this request. The status, timing, headers
        and body will appear here.
      </p>
    </div>

    <!-- Transport failure -->
    <div v-else-if="!response.ok" class="response__error">
      <div class="response__error-head">
        <StatusBadge :status="null" />
        <span class="response__meta">{{ response.duration_ms.toFixed(0) }} ms</span>
      </div>
      <p class="response__error-text">{{ response.error }}</p>
      <p class="response__error-hint">
        Check the URL, that the server is running, and that your network allows
        the connection.
      </p>
    </div>

    <!-- Success -->
    <template v-else>
      <header class="response__bar">
        <StatusBadge :status="response.status_code" :text="response.status_text" />

        <span class="response__meta">
          <strong>{{ response.duration_ms.toFixed(0) }}</strong> ms
        </span>
        <span class="response__meta">
          <strong>{{ formatSize(response.size_bytes) }}</strong>
        </span>

        <span
          v-if="assertionSummary"
          class="badge"
          :class="assertionSummary.failed ? 'badge--bad' : 'badge--ok'"
        >
          {{ assertionSummary.passed }}/{{ assertionSummary.total }} tests
        </span>

        <span v-if="response.redirects.length" class="badge badge--info">
          {{ response.redirects.length }} redirect{{ response.redirects.length > 1 ? 's' : '' }}
        </span>

        <span v-if="response.truncated" class="badge badge--warn">truncated</span>

        <div class="response__spacer" />

        <button class="btn btn--ghost btn--sm" type="button" @click="copyBody">
          Copy
        </button>
      </header>

      <nav class="views" role="tablist">
        <button
          v-for="item in (['body', 'headers', 'tests'] as View[])"
          :key="item"
          class="views__tab"
          :class="{ 'views__tab--on': view === item }"
          role="tab"
          :aria-selected="view === item"
          type="button"
          @click="view = item"
        >
          {{ item.charAt(0).toUpperCase() + item.slice(1) }}
          <span v-if="item === 'headers'" class="views__count">{{ headerCount }}</span>
          <span
            v-else-if="item === 'tests' && assertionSummary"
            class="views__count"
            :class="{ 'views__count--bad': assertionSummary.failed > 0 }"
          >{{ assertionSummary.total }}</span>
        </button>

        <div class="response__spacer" />

        <label v-if="view === 'body'" class="views__wrap">
          <input v-model="wrapped" class="checkbox" type="checkbox" />
          Wrap
        </label>
      </nav>

      <div class="response__content">
        <!-- Body -->
        <div v-if="view === 'body'" class="response__body">
          <p v-if="!response.body" class="response__empty-body">
            The response had an empty body.
          </p>
          <CodeEditor
            v-else
            :model-value="prettyBody"
            :language="editorLanguage"
            readonly
            min-height="100%"
          />
        </div>

        <!-- Headers -->
        <div v-else-if="view === 'headers'" class="response__headers scroll-y">
          <dl class="headers">
            <template v-for="(value, key) in response.headers" :key="key">
              <dt class="headers__key">{{ key }}</dt>
              <dd class="headers__value">{{ value }}</dd>
            </template>
          </dl>
        </div>

        <!-- Tests -->
        <div v-else class="response__tests scroll-y">
          <p v-if="!response.assertion_results.length" class="response__empty-body">
            This request has no assertions. Add some in the Tests tab to check
            the response automatically.
          </p>
          <ul v-else class="results">
            <li
              v-for="(result, index) in response.assertion_results"
              :key="index"
              class="results__row"
              :class="result.passed ? 'results__row--pass' : 'results__row--fail'"
            >
              <AppIcon
                :name="result.passed ? 'check' : 'close'"
                :size="13"
                class="results__icon"
                :stroke="2.2"
              />
              <div class="results__detail">
                <p class="results__claim">
                  <strong>{{ result.source }}</strong>
                  <span v-if="result.property" class="mono"> {{ result.property }}</span>
                  {{ result.operator.replace(/_/g, ' ') }}
                  <span v-if="result.target" class="mono">"{{ result.target }}"</span>
                </p>
                <p v-if="!result.passed" class="results__message">
                  {{ result.message }}
                </p>
                <p v-else-if="result.actual" class="results__actual">
                  got <span class="mono">{{ result.actual }}</span>
                </p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.response {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--surface);
}

.response__center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--text-muted);
}
.spinner--lg { width: 24px; height: 24px; border-width: 3px; }
.response__waiting { font-size: var(--text-sm); }

/* --- Status bar --- */
.response__bar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border);
}

.response__meta { font-size: var(--text-sm); color: var(--text-muted); }
.response__meta strong { color: var(--text); font-family: var(--font-mono); }

.response__spacer { flex: 1; }

/* --- Error --- */
.response__error { padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }
.response__error-head { display: flex; align-items: center; gap: var(--space-3); }
.response__error-text {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--danger);
  padding: var(--space-3);
  background: color-mix(in srgb, var(--danger) 8%, transparent);
  border-radius: var(--radius);
  word-break: break-word;
}
.response__error-hint { font-size: var(--text-sm); color: var(--text-muted); }

/* --- View tabs --- */
.views {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  border-bottom: 1px solid var(--border);
}

.views__tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-3);
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-mono);
  transition: color var(--transition), border-color var(--transition);
}
.views__tab:hover { color: var(--text); }
.views__tab--on { color: var(--accent); border-bottom-color: var(--accent); }

.views__count {
  padding: 0 5px;
  border-radius: 9px;
  background: var(--surface-active);
  font-size: 0.625rem;
  font-weight: 700;
}
.views__count--bad { background: color-mix(in srgb, var(--danger) 20%, transparent); color: var(--danger); }

.views__wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-muted);
  cursor: pointer;
}

/* --- Content --- */
.response__content { flex: 1; min-height: 0; padding: var(--space-3); }
.response__body { height: 100%; }

.response__empty-body {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.response__headers, .response__tests { height: 100%; }

.headers {
  display: grid;
  grid-template-columns: minmax(140px, auto) 1fr;
  gap: var(--space-1) var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}
.headers__key { color: var(--accent); word-break: break-all; }
.headers__value { color: var(--text-muted); word-break: break-all; }

.results { display: flex; flex-direction: column; gap: var(--space-2); }

.results__row {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);
  border-radius: var(--radius);
}
.results__row--pass { border-left-color: var(--ok); }
.results__row--fail { border-left-color: var(--danger); }

.results__icon { flex-shrink: 0; margin-top: 2px; }
.results__row--pass .results__icon { color: var(--ok); }
.results__row--fail .results__icon { color: var(--danger); }

.results__detail { min-width: 0; }
.results__claim { font-size: var(--text-sm); word-break: break-word; }
.results__message { font-size: var(--text-xs); color: var(--danger); margin-top: var(--space-1); }
.results__actual { font-size: var(--text-xs); color: var(--text-subtle); margin-top: var(--space-1); }

kbd {
  padding: 1px 5px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface-raised);
  font-family: var(--font-mono);
  font-size: 0.75em;
}
</style>
