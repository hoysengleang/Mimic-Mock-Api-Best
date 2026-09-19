<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import { useEnvironmentsStore } from '@/stores/environments'
import { useUiStore } from '@/stores/ui'
import type { Variable } from '@/types'

const environments = useEnvironmentsStore()
const ui = useUiStore()

// Held as constants because a literal "{{name}}" written directly in the
// template would be parsed as an interpolation and break the compiler.
const EXAMPLE_VAR = '{{baseUrl}}'
const EXAMPLE_PLACEHOLDER = '{{name}}'

const selectedId = ref<string | null>(null)
const draft = ref<Variable[]>([])
const creating = ref(false)
const newName = ref('')
const confirmDelete = ref(false)

const selected = computed(
  () => environments.environments.find((e) => e.id === selectedId.value) ?? null,
)

/** Always keep a blank trailing row so adding a variable needs no button. */
const rows = computed<Variable[]>(() => [
  ...draft.value,
  { key: '', value: '', enabled: true, secret: false },
])

function loadDraft() {
  draft.value = selected.value
    ? selected.value.variables.map((v) => ({ ...v }))
    : []
}

watch(selected, loadDraft, { immediate: true })

watch(
  () => environments.environments.length,
  () => {
    if (!selectedId.value) selectedId.value = environments.environments[0]?.id ?? null
  },
  { immediate: true },
)

function updateRow(index: number, patch: Partial<Variable>) {
  const next = rows.value.map((row, i) => (i === index ? { ...row, ...patch } : { ...row }))
  draft.value = next.filter((row) => row.key.trim() !== '' || row.value.trim() !== '')
}

function removeRow(index: number) {
  draft.value = rows.value.filter((_, i) => i !== index).filter(
    (row) => row.key.trim() !== '' || row.value.trim() !== '',
  )
}

async function save() {
  if (!selected.value) return
  try {
    await environments.saveVariables(selected.value.id, draft.value)
  } catch {
    ui.toast('Could not save the variables', 'error')
  }
}

async function create() {
  const name = newName.value.trim()
  if (!name) return
  try {
    const created = await environments.create(name)
    selectedId.value = created.id
    creating.value = false
    newName.value = ''
  } catch {
    ui.toast('Could not create the environment', 'error')
  }
}

async function remove() {
  if (!selected.value) return
  await environments.remove(selected.value.id)
  selectedId.value = environments.environments[0]?.id ?? null
  confirmDelete.value = false
}
</script>

<template>
  <div class="envs">
    <aside class="env-list">
      <header class="env-list__head">
        <h1 class="env-list__title">Environments</h1>
        <button class="btn btn--icon btn--sm" type="button" aria-label="New environment" @click="creating = true">
          <AppIcon name="plus" :size="13" />
        </button>
      </header>

      <ul class="env-list__items scroll-y">
        <li v-for="item in environments.environments" :key="item.id">
          <button
            class="env-item"
            :class="{ 'env-item--on': item.id === selectedId }"
            type="button"
            @click="selectedId = item.id"
          >
            <span class="truncate">{{ item.name }}</span>
            <span v-if="item.is_active" class="env-item__active">active</span>
          </button>
        </li>
        <li v-if="!environments.environments.length" class="env-list__empty">
          No environments yet
        </li>
      </ul>
    </aside>

    <section class="editor">
      <div v-if="!selected" class="empty-state">
        <AppIcon name="variable" :size="26" class="empty-state__icon" :stroke="1.4" />
        <p class="empty-state__title">No environment selected</p>
        <p class="empty-state__hint">
          Environments hold variables like <code class="mono">baseUrl</code>
          that you reference as <code class="mono">{{ EXAMPLE_VAR }}</code>
          in any request. Switch environments to point the same requests at
          staging or production.
        </p>
        <button class="btn btn--primary" type="button" @click="creating = true">
          New environment
        </button>
      </div>

      <template v-else>
        <header class="editor__head">
          <div>
            <h2 class="editor__title">{{ selected.name }}</h2>
            <p class="editor__sub">
              {{ draft.length }} variable(s)
              <template v-if="selected.is_active"> · currently active</template>
            </p>
          </div>

          <div class="editor__actions">
            <button
              v-if="!selected.is_active"
              class="btn"
              type="button"
              @click="environments.activate(selected.id)"
            >
              Make active
            </button>
            <button class="btn btn--danger" type="button" @click="confirmDelete = true">
              Delete
            </button>
            <button class="btn btn--primary" type="button" @click="save">Save</button>
          </div>
        </header>

        <p class="editor__hint">
          Reference any variable in a URL, header, body or auth field as
          <code class="mono">{{ EXAMPLE_PLACEHOLDER }}</code>.
          Marking one secret only hides it on screen — it is not encrypted, so
          keep real production credentials out of here.
        </p>

        <div class="vars">
          <div class="vars__head">
            <span />
            <span>Name</span>
            <span>Value</span>
            <span>Secret</span>
            <span />
          </div>

          <div
            v-for="(row, index) in rows"
            :key="index"
            class="vars__row"
            :class="{ 'vars__row--blank': index === rows.length - 1 }"
          >
            <input
              class="checkbox"
              type="checkbox"
              :checked="index === rows.length - 1 ? false : row.enabled"
              :disabled="index === rows.length - 1"
              aria-label="Enabled"
              @change="updateRow(index, { enabled: ($event.target as HTMLInputElement).checked })"
            />
            <input
              class="input input--mono"
              :value="row.key"
              placeholder="baseUrl"
              spellcheck="false"
              @input="updateRow(index, { key: ($event.target as HTMLInputElement).value })"
            />
            <input
              class="input input--mono"
              :value="row.value"
              :type="row.secret ? 'password' : 'text'"
              placeholder="http://localhost:5000"
              spellcheck="false"
              @input="updateRow(index, { value: ($event.target as HTMLInputElement).value })"
            />
            <input
              class="checkbox"
              type="checkbox"
              :checked="index === rows.length - 1 ? false : row.secret"
              :disabled="index === rows.length - 1"
              aria-label="Secret"
              @change="updateRow(index, { secret: ($event.target as HTMLInputElement).checked })"
            />
            <button
              v-if="index !== rows.length - 1"
              class="btn btn--ghost btn--icon btn--sm"
              type="button"
              aria-label="Remove variable"
              @click="removeRow(index)"
            >
              <AppIcon name="close" :size="12" />
            </button>
            <span v-else />
          </div>
        </div>
      </template>
    </section>

    <BaseModal :open="creating" title="New environment" width="420px" @close="creating = false">
      <label class="label" for="env-name">Name</label>
      <input
        id="env-name"
        v-model="newName"
        class="input"
        placeholder="e.g. Staging"
        @keydown.enter="create"
      />
      <template #footer>
        <button class="btn" type="button" @click="creating = false">Cancel</button>
        <button class="btn btn--primary" type="button" :disabled="!newName.trim()" @click="create">
          Create
        </button>
      </template>
    </BaseModal>

    <BaseModal
      :open="confirmDelete"
      title="Delete environment?"
      width="420px"
      @close="confirmDelete = false"
    >
      <p><strong>{{ selected?.name }}</strong> and its variables will be removed.</p>
      <template #footer>
        <button class="btn" type="button" @click="confirmDelete = false">Cancel</button>
        <button class="btn btn--danger" type="button" @click="remove">Delete</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.envs { display: flex; flex: 1; min-height: 0; min-width: 0; }

.env-list {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--surface);
  min-height: 0;
}

.env-list__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
}
.env-list__title { font-size: var(--text-lg); font-weight: 650; }

.env-list__items { flex: 1; min-height: 0; padding: var(--space-2); }
.env-list__empty { padding: var(--space-3); font-size: var(--text-sm); color: var(--text-subtle); }

.env-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  font-size: var(--text-sm);
  color: var(--text-muted);
  text-align: left;
}
.env-item:hover { background: var(--surface-hover); color: var(--text); }
.env-item--on { background: var(--accent-soft); color: var(--accent); font-weight: 500; }

.env-item__active {
  margin-left: auto;
  padding: 1px 6px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--ok) 18%, transparent);
  color: var(--ok);
  font-size: 0.625rem;
  font-weight: 700;
}

.editor {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  overflow-y: auto;
}

.editor__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}
.editor__title { font-size: var(--text-xl); font-weight: 650; }
.editor__sub { font-size: var(--text-sm); color: var(--text-muted); }
.editor__actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }

.editor__hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  padding: var(--space-3);
  border-radius: var(--radius);
  background: var(--surface);
  border: 1px solid var(--border);
}
.editor__hint code, .empty-state code {
  padding: 1px 4px;
  border-radius: var(--radius-sm);
  background: var(--surface-active);
}

.vars { display: flex; flex-direction: column; gap: 2px; }

.vars__head, .vars__row {
  display: grid;
  grid-template-columns: 28px minmax(120px, 1fr) minmax(160px, 2fr) 60px 28px;
  gap: var(--space-2);
  align-items: center;
}

.vars__head {
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-subtle);
  padding-bottom: var(--space-1);
}

.vars__row--blank input:not([type='checkbox']) { opacity: 0.55; }
.vars__row--blank input:focus { opacity: 1; }
.vars__row--blank .checkbox { opacity: 0.25; }
.vars__row input:not(.checkbox) { height: 30px; }

@media (max-width: 860px) {
  .envs { flex-direction: column; }
  .env-list { width: 100%; max-height: 30%; border-right: none; border-bottom: 1px solid var(--border); }
  .vars__head { display: none; }
  .vars__row { grid-template-columns: 24px 1fr 50px 24px; }
}
</style>
