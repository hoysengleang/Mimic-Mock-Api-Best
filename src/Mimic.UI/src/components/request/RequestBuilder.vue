<script setup lang="ts">
import { computed, ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import CodeEditor from '@/components/common/CodeEditor.vue'
import KeyValueEditor from '@/components/common/KeyValueEditor.vue'
import AssertionEditor from '@/components/request/AssertionEditor.vue'
import AuthEditor from '@/components/request/AuthEditor.vue'
import { useEnvironmentsStore } from '@/stores/environments'
import { useUiStore } from '@/stores/ui'
import { useWorkspaceStore } from '@/stores/workspace'
import { HTTP_METHODS, type BodyMode, type HttpMethod, type RequestTab } from '@/types'

const props = defineProps<{ tab: RequestTab }>()

const workspace = useWorkspaceStore()
const environments = useEnvironmentsStore()
const ui = useUiStore()

type PanelTab = 'params' | 'headers' | 'body' | 'auth' | 'tests'
const panel = ref<PanelTab>('params')

const BODY_MODES: Array<{ value: BodyMode; label: string }> = [
  { value: 'none', label: 'None' },
  { value: 'json', label: 'JSON' },
  { value: 'text', label: 'Text' },
  { value: 'xml', label: 'XML' },
  { value: 'form', label: 'Form' },
]

const counts = computed(() => ({
  params: props.tab.query_params.filter((p) => p.enabled && p.key).length,
  headers: props.tab.headers.filter((h) => h.enabled && h.key).length,
  tests: props.tab.assertions.filter((a) => a.enabled).length,
}))

const hasBody = computed(() => props.tab.body_mode !== 'none')

/** Variables referenced in the URL that the active environment does not define. */
const missingVariables = computed(() => {
  const referenced = [...props.tab.url.matchAll(/\{\{\s*([\w.-]+)\s*\}\}/g)]
    .map((match) => match[1])
    .filter((name): name is string => Boolean(name))
  const known = new Set(environments.activeKeys)
  return [...new Set(referenced.filter((name) => !known.has(name)))]
})

function touch() {
  workspace.markDirty(props.tab)
}

function send() {
  void workspace.send(props.tab)
}

function formatBody() {
  try {
    props.tab.body = JSON.stringify(JSON.parse(props.tab.body), null, 2)
    touch()
  } catch {
    ui.toast('Body is not valid JSON, so it was left alone', 'error')
  }
}

const editorLanguage = computed<'json' | 'xml' | 'text'>(() => {
  if (props.tab.body_mode === 'json') return 'json'
  if (props.tab.body_mode === 'xml') return 'xml'
  return 'text'
})
</script>

<template>
  <div class="builder">
    <!-- URL bar -->
    <div class="urlbar">
      <select
        class="select urlbar__method"
        :value="tab.method"
        aria-label="HTTP method"
        :style="{ color: `var(--method-${tab.method.toLowerCase()})` }"
        @change="
          workspace.setMethod(
            tab,
            ($event.target as HTMLSelectElement).value as HttpMethod,
          )
        "
      >
        <option v-for="method in HTTP_METHODS" :key="method" :value="method">
          {{ method }}
        </option>
      </select>

      <input
        v-model="tab.url"
        class="input input--mono urlbar__url"
        placeholder="{{baseUrl}}/api/users   —   or a full URL"
        spellcheck="false"
        aria-label="Request URL"
        @input="touch"
        @keydown.enter="send"
      />

      <button
        class="btn btn--primary urlbar__send"
        type="button"
        :disabled="tab.sending"
        @click="send"
      >
        <span v-if="tab.sending" class="spinner" />
        <AppIcon v-else name="send" :size="13" />
        {{ tab.sending ? 'Sending' : 'Send' }}
      </button>

      <button
        class="btn"
        type="button"
        :disabled="!tab.dirty && !!tab.requestId"
        @click="workspace.save(tab)"
      >
        Save
      </button>
    </div>

    <p v-if="missingVariables.length" class="warnbar">
      <strong>{{ missingVariables.join(', ') }}</strong>
      {{ missingVariables.length === 1 ? 'is' : 'are' }} not defined in the
      active environment — the request will be sent with the placeholder text
      as-is.
    </p>

    <!-- Section tabs -->
    <nav class="tabs" role="tablist">
      <button
        v-for="item in (['params', 'headers', 'body', 'auth', 'tests'] as PanelTab[])"
        :key="item"
        class="tabs__tab"
        :class="{ 'tabs__tab--on': panel === item }"
        role="tab"
        :aria-selected="panel === item"
        type="button"
        @click="panel = item"
      >
        {{ item === 'tests' ? 'Tests' : item.charAt(0).toUpperCase() + item.slice(1) }}
        <span
          v-if="item === 'params' && counts.params"
          class="tabs__count"
        >{{ counts.params }}</span>
        <span
          v-else-if="item === 'headers' && counts.headers"
          class="tabs__count"
        >{{ counts.headers }}</span>
        <span
          v-else-if="item === 'tests' && counts.tests"
          class="tabs__count"
        >{{ counts.tests }}</span>
        <span
          v-else-if="item === 'body' && hasBody"
          class="tabs__dot"
        />
        <span
          v-else-if="item === 'auth' && tab.auth.type !== 'none'"
          class="tabs__dot"
        />
      </button>
    </nav>

    <!-- Panels -->
    <div class="panel scroll-y">
      <KeyValueEditor
        v-if="panel === 'params'"
        v-model="tab.query_params"
        key-placeholder="Parameter"
        :suggestions="environments.activeKeys"
        @update:model-value="touch"
      />

      <KeyValueEditor
        v-else-if="panel === 'headers'"
        v-model="tab.headers"
        key-placeholder="Header"
        :suggestions="environments.activeKeys"
        @update:model-value="touch"
      />

      <div v-else-if="panel === 'body'" class="body">
        <div class="body__bar">
          <div class="body__modes">
            <button
              v-for="mode in BODY_MODES"
              :key="mode.value"
              class="body__mode"
              :class="{ 'body__mode--on': tab.body_mode === mode.value }"
              type="button"
              @click="tab.body_mode = mode.value; touch()"
            >
              {{ mode.label }}
            </button>
          </div>
          <button
            v-if="tab.body_mode === 'json'"
            class="btn btn--sm"
            type="button"
            @click="formatBody"
          >
            Format
          </button>
        </div>

        <p v-if="tab.body_mode === 'none'" class="body__none">
          This request sends no body. Pick a format above to add one.
        </p>

        <KeyValueEditor
          v-else-if="tab.body_mode === 'form'"
          v-model="tab.form_data"
          key-placeholder="Field"
          :suggestions="environments.activeKeys"
          @update:model-value="touch"
        />

        <CodeEditor
          v-else
          v-model="tab.body"
          :language="editorLanguage"
          min-height="240px"
          placeholder='{ "name": "value" }'
          @update:model-value="touch"
        />
      </div>

      <AuthEditor
        v-else-if="panel === 'auth'"
        v-model="tab.auth"
        :suggestions="environments.activeKeys"
        @update:model-value="touch"
      />

      <AssertionEditor
        v-else-if="panel === 'tests'"
        v-model="tab.assertions"
        :results="tab.response?.assertion_results"
        @update:model-value="touch"
      />
    </div>
  </div>
</template>

<style scoped>
.builder {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

/* --- URL bar --- */
.urlbar {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3);
  border-bottom: 1px solid var(--border);
}

.urlbar__method {
  width: 116px;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-weight: 700;
}

.urlbar__url { flex: 1; min-width: 0; }
.urlbar__send { min-width: 84px; }

.warnbar {
  padding: var(--space-2) var(--space-3);
  background: color-mix(in srgb, var(--warn) 12%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--warn) 30%, transparent);
  color: var(--warn);
  font-size: var(--text-xs);
}
.warnbar strong { font-family: var(--font-mono); }

/* --- Tabs --- */
.tabs {
  display: flex;
  gap: var(--space-1);
  padding: 0 var(--space-3);
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}

.tabs__tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-3);
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: var(--tracking-mono);
  white-space: nowrap;
  transition: color var(--transition), border-color var(--transition);
}
.tabs__tab:hover { color: var(--text); }
.tabs__tab--on { color: var(--accent); border-bottom-color: var(--accent); }

.tabs__count {
  padding: 0 5px;
  border-radius: 9px;
  background: var(--surface-active);
  color: var(--text-muted);
  font-size: 0.625rem;
  font-weight: 700;
}
.tabs__tab--on .tabs__count { background: var(--accent-soft); color: var(--accent); }

.tabs__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

/* --- Panel --- */
.panel {
  flex: 1;
  min-height: 0;
  padding: var(--space-4) var(--space-3);
}

.body { display: flex; flex-direction: column; gap: var(--space-3); height: 100%; }

.body__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.body__modes { display: flex; gap: var(--space-1); }

.body__mode {
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  color: var(--text-muted);
  transition: all var(--transition);
}
.body__mode:hover { background: var(--surface-hover); color: var(--text); }
.body__mode--on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.body__none {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

@media (max-width: 720px) {
  .urlbar { flex-wrap: wrap; }
  .urlbar__url { order: 3; width: 100%; flex-basis: 100%; }
}
</style>
