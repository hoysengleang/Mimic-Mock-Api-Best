<script setup lang="ts">
/**
 * Editable table of key/value rows, used for headers, query params and
 * form fields. A blank trailing row is always present so adding an entry
 * never needs a button press.
 */
import { computed } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import { emptyKeyValue, type KeyValue } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue: KeyValue[]
    keyPlaceholder?: string
    valuePlaceholder?: string
    /** Known variable names, shown as a datalist on the value field. */
    suggestions?: string[]
  }>(),
  {
    keyPlaceholder: 'Name',
    valuePlaceholder: 'Value',
    suggestions: () => [],
  },
)

const emit = defineEmits<{ 'update:modelValue': [value: KeyValue[]] }>()

/** The stored rows plus one blank row for new input. */
const rows = computed<KeyValue[]>(() => [...props.modelValue, emptyKeyValue()])

function commit(next: KeyValue[]) {
  // Drop trailing rows that were never filled in.
  emit(
    'update:modelValue',
    next.filter((row) => row.key.trim() !== '' || row.value.trim() !== ''),
  )
}

function updateRow(index: number, patch: Partial<KeyValue>) {
  const next = rows.value.map((row, i) =>
    i === index ? { ...row, ...patch } : { ...row },
  )
  commit(next)
}

function removeRow(index: number) {
  commit(rows.value.filter((_, i) => i !== index))
}

const listId = `vars-${Math.random().toString(36).slice(2, 9)}`
</script>

<template>
  <div class="kv">
    <datalist :id="listId">
      <option v-for="name in suggestions" :key="name" :value="`{{${name}}}`" />
    </datalist>

    <div class="kv__head">
      <span />
      <span>{{ keyPlaceholder }}</span>
      <span>{{ valuePlaceholder }}</span>
      <span />
    </div>

    <div
      v-for="(row, index) in rows"
      :key="index"
      class="kv__row"
      :class="{ 'kv__row--blank': index === rows.length - 1 }"
    >
      <input
        class="checkbox"
        type="checkbox"
        :checked="index === rows.length - 1 ? false : row.enabled"
        :aria-label="`Enable ${row.key || 'row'}`"
        :disabled="index === rows.length - 1"
        @change="
          updateRow(index, {
            enabled: ($event.target as HTMLInputElement).checked,
          })
        "
      />

      <input
        class="input input--mono kv__input"
        :value="row.key"
        :placeholder="keyPlaceholder"
        spellcheck="false"
        @input="updateRow(index, { key: ($event.target as HTMLInputElement).value })"
      />

      <input
        class="input input--mono kv__input"
        :value="row.value"
        :placeholder="valuePlaceholder"
        :list="listId"
        spellcheck="false"
        @input="
          updateRow(index, { value: ($event.target as HTMLInputElement).value })
        "
      />

      <button
        v-if="index !== rows.length - 1"
        class="btn btn--ghost btn--icon btn--sm kv__remove"
        type="button"
        :aria-label="`Remove ${row.key || 'row'}`"
        @click="removeRow(index)"
      >
        <AppIcon name="close" :size="12" />
      </button>
      <span v-else />
    </div>
  </div>
</template>

<style scoped>
.kv {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kv__head,
.kv__row {
  display: grid;
  grid-template-columns: 28px minmax(120px, 1fr) minmax(160px, 2fr) 28px;
  gap: var(--space-2);
  align-items: center;
}

.kv__head {
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-subtle);
  padding-bottom: var(--space-1);
}

/* The trailing row is a prompt to add, not real data — keep it quiet. */
.kv__row--blank .kv__input { opacity: 0.55; }
.kv__row--blank .kv__input:focus { opacity: 1; }
.kv__row--blank .checkbox { opacity: 0.25; }

.kv__input {
  height: 30px;
}

.kv__remove { color: var(--text-subtle); }
.kv__remove:hover { color: var(--danger); }

@media (max-width: 640px) {
  .kv__head {
    display: none;
  }
  .kv__row {
    grid-template-columns: 24px 1fr 24px;
    grid-template-areas:
      'check key remove'
      '.     value .';
    row-gap: var(--space-1);
    padding-bottom: var(--space-2);
    border-bottom: 1px solid var(--border);
  }
  .kv__row > :nth-child(1) { grid-area: check; }
  .kv__row > :nth-child(2) { grid-area: key; }
  .kv__row > :nth-child(3) { grid-area: value; }
  .kv__row > :nth-child(4) { grid-area: remove; }
}
</style>
