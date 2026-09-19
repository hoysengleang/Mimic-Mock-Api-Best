<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import CodeEditor from '@/components/common/CodeEditor.vue'
import MethodBadge from '@/components/common/MethodBadge.vue'
import { useMocksStore } from '@/stores/mocks'
import { useUiStore } from '@/stores/ui'
import { HTTP_METHODS, type HttpMethod, type Mock } from '@/types'

const mocks = useMocksStore()
const ui = useUiStore()

const editing = ref<Mock | null>(null)
const creating = ref(false)
const confirmTarget = ref<Mock | null>(null)
const saving = ref(false)

const form = reactive({
  name: '',
  path: '/api/example',
  method: 'GET' as HttpMethod,
  status_code: 200,
  delay: 0,
  body: '{\n  "message": "Hello from Mimic"\n}',
})

function resetForm() {
  form.name = ''
  form.path = '/api/example'
  form.method = 'GET'
  form.status_code = 200
  form.delay = 0
  form.body = '{\n  "message": "Hello from Mimic"\n}'
}

function openCreate() {
  resetForm()
  editing.value = null
  creating.value = true
}

function openEdit(mock: Mock) {
  form.name = mock.name
  form.path = mock.path
  form.method = mock.method
  form.status_code = mock.status_code
  form.delay = mock.delay
  form.body = JSON.stringify(mock.response ?? {}, null, 2)
  editing.value = mock
  creating.value = true
}

async function save() {
  let parsed: unknown
  try {
    parsed = form.body.trim() ? JSON.parse(form.body) : null
  } catch {
    ui.toast('The response body is not valid JSON', 'error')
    return
  }

  saving.value = true
  const payload = {
    name: form.name,
    path: form.path,
    method: form.method,
    status_code: form.status_code,
    delay: form.delay,
    response: parsed,
  }

  try {
    if (editing.value) await mocks.update(editing.value.id, payload)
    else await mocks.create(payload)
    creating.value = false
  } catch (error) {
    ui.toast(error instanceof Error ? error.message : 'Could not save', 'error')
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  if (!confirmTarget.value) return
  await mocks.remove(confirmTarget.value.id)
  confirmTarget.value = null
}

async function copyUrl(mock: Mock) {
  const url = `${window.location.origin}/mock${mock.path}`
  try {
    await navigator.clipboard.writeText(url)
    ui.toast('URL copied', 'success')
  } catch {
    ui.toast('Could not access the clipboard', 'error')
  }
}

onMounted(() => mocks.load())
</script>

<template>
  <div class="mocks">
    <header class="mocks__head">
      <div>
        <h1 class="mocks__title">Mock endpoints</h1>
        <p class="mocks__sub">
          Served under <code class="mono">/mock/…</code>. Use
          <code class="mono">:name</code> for a path parameter and
          <code class="mono">*</code> to match the rest of a path.
        </p>
      </div>

      <div class="mocks__actions">
        <input
          v-model="mocks.search"
          class="input mocks__search"
          type="search"
          placeholder="Search mocks…"
          aria-label="Search mocks"
        />
        <button class="btn" type="button" @click="mocks.resetHits()">
          Reset hits
        </button>
        <button class="btn btn--primary" type="button" @click="openCreate">
          New mock
        </button>
      </div>
    </header>

    <div class="mocks__stats">
      <span><strong>{{ mocks.mocks.length }}</strong> total</span>
      <span><strong>{{ mocks.enabledCount }}</strong> enabled</span>
      <span><strong>{{ mocks.totalHits }}</strong> hits served</span>
    </div>

    <div class="mocks__body scroll-y">
      <p v-if="mocks.loading" class="mocks__status">Loading…</p>

      <div v-else-if="!mocks.filtered.length" class="empty-state">
        <AppIcon name="mock" :size="26" class="empty-state__icon" :stroke="1.4" />
        <p class="empty-state__title">
          {{ mocks.search ? 'No mocks match' : 'No mocks yet' }}
        </p>
        <p class="empty-state__hint">
          A mock is a fake endpoint that returns whatever you tell it to —
          useful when the real API is not built yet, is slow, or is hard to
          trigger on demand.
        </p>
        <button v-if="!mocks.search" class="btn btn--primary" type="button" @click="openCreate">
          Create your first mock
        </button>
      </div>

      <ul v-else class="list">
        <li v-for="mock in mocks.filtered" :key="mock.id" class="row" :class="{ 'row--off': !mock.is_enabled }">
          <label class="row__toggle">
            <input
              class="checkbox"
              type="checkbox"
              :checked="mock.is_enabled"
              :aria-label="`Enable ${mock.path}`"
              @change="mocks.toggle(mock)"
            />
          </label>

          <MethodBadge :method="mock.method" />

          <div class="row__main">
            <p class="row__path mono truncate">{{ mock.path }}</p>
            <p v-if="mock.name" class="row__name truncate">{{ mock.name }}</p>
          </div>

          <span class="row__status" :class="mock.status_code >= 400 ? 'row__status--bad' : 'row__status--ok'">
            {{ mock.status_code }}
          </span>

          <span v-if="mock.delay > 0" class="row__delay">{{ mock.delay }}s</span>

          <span class="row__hits" :title="`${mock.hit_count} request(s) served`">
            {{ mock.hit_count }}
          </span>

          <div class="row__actions">
            <button class="btn btn--ghost btn--sm" type="button" @click="copyUrl(mock)">
              Copy URL
            </button>
            <button class="btn btn--ghost btn--sm" type="button" @click="openEdit(mock)">
              Edit
            </button>
            <button
              class="btn btn--ghost btn--icon btn--sm"
              type="button"
              :aria-label="`Delete ${mock.path}`"
              @click="confirmTarget = mock"
            >
              <AppIcon name="trash" :size="13" />
            </button>
          </div>
        </li>
      </ul>
    </div>

    <!-- Create / edit -->
    <BaseModal
      :open="creating"
      :title="editing ? 'Edit mock' : 'New mock'"
      width="640px"
      @close="creating = false"
    >
      <div class="form">
        <div class="form__row form__row--split">
          <label>
            <span class="label">Method</span>
            <select v-model="form.method" class="select">
              <option v-for="m in HTTP_METHODS" :key="m" :value="m">{{ m }}</option>
            </select>
          </label>
          <label class="form__grow">
            <span class="label">Path</span>
            <input v-model="form.path" class="input input--mono" placeholder="/api/users/:id" />
          </label>
        </div>

        <label>
          <span class="label">Name <span class="form__optional">(optional)</span></span>
          <input v-model="form.name" class="input" placeholder="What this mock represents" />
        </label>

        <div class="form__row form__row--split">
          <label>
            <span class="label">Status code</span>
            <input v-model.number="form.status_code" class="input input--mono" type="number" min="100" max="599" />
          </label>
          <label>
            <span class="label">Delay (seconds)</span>
            <input v-model.number="form.delay" class="input input--mono" type="number" min="0" max="60" step="0.1" />
          </label>
        </div>

        <div>
          <span class="label">Response body (JSON)</span>
          <CodeEditor v-model="form.body" language="json" min-height="220px" />
        </div>
      </div>

      <template #footer>
        <button class="btn" type="button" @click="creating = false">Cancel</button>
        <button class="btn btn--primary" type="button" :disabled="saving" @click="save">
          <span v-if="saving" class="spinner" />
          {{ editing ? 'Save changes' : 'Create mock' }}
        </button>
      </template>
    </BaseModal>

    <!-- Delete -->
    <BaseModal
      :open="!!confirmTarget"
      title="Delete mock?"
      width="420px"
      @close="confirmTarget = null"
    >
      <p>
        <code class="mono">{{ confirmTarget?.method }} {{ confirmTarget?.path }}</code>
        will stop responding. This cannot be undone.
      </p>
      <template #footer>
        <button class="btn" type="button" @click="confirmTarget = null">Cancel</button>
        <button class="btn btn--danger" type="button" @click="confirmDelete">Delete</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.mocks {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.mocks__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
}

.mocks__title { font-size: var(--text-xl); font-weight: 650; }
.mocks__sub { font-size: var(--text-sm); color: var(--text-muted); margin-top: var(--space-1); }
.mocks__sub code {
  padding: 1px 4px;
  border-radius: var(--radius-sm);
  background: var(--surface-active);
  font-size: 0.92em;
}

.mocks__actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.mocks__search { width: 200px; }

.mocks__stats {
  display: flex;
  gap: var(--space-5);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  font-size: var(--text-xs);
  color: var(--text-muted);
}
.mocks__stats strong { color: var(--text); font-family: var(--font-mono); }

.mocks__body { flex: 1; min-height: 0; padding: var(--space-3) var(--space-4); }
.mocks__status { padding: var(--space-4); color: var(--text-muted); }

.list { display: flex; flex-direction: column; gap: var(--space-2); }

.row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  transition: border-color var(--transition);
}
.row:hover { border-color: var(--border-strong); }
.row:hover .row__actions { opacity: 1; }
.row--off { opacity: 0.5; }

.row__main { flex: 1; min-width: 0; }
.row__path { font-size: var(--text-sm); }
.row__name { font-size: var(--text-xs); color: var(--text-muted); }

.row__status {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
}
.row__status--ok  { color: var(--ok);     background: color-mix(in srgb, var(--ok) 14%, transparent); }
.row__status--bad { color: var(--danger); background: color-mix(in srgb, var(--danger) 14%, transparent); }

.row__delay, .row__hits {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--text-subtle);
  min-width: 28px;
  text-align: right;
}

.row__actions {
  display: flex;
  gap: var(--space-1);
  opacity: 0;
  transition: opacity var(--transition);
}
.row__actions:focus-within { opacity: 1; }

.form { display: flex; flex-direction: column; gap: var(--space-4); }
.form__row--split { display: grid; grid-template-columns: 130px 1fr; gap: var(--space-3); }
.form__grow { min-width: 0; }
.form__optional { font-weight: 400; text-transform: none; letter-spacing: 0; }

@media (max-width: 760px) {
  .row__delay, .row__hits { display: none; }
  .row__actions { opacity: 1; }
  .form__row--split { grid-template-columns: 1fr; }
}
</style>
