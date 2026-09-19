<script setup lang="ts">
/**
 * Builds response assertions from dropdowns rather than free-form script.
 *
 * The backend only ever evaluates these as data, so a collection shared
 * between people can never carry executable code.
 */
import { computed } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import {
  emptyAssertion,
  type Assertion,
  type AssertionOperator,
  type AssertionResult,
  type AssertionSource,
} from '@/types'

const props = defineProps<{
  modelValue: Assertion[]
  results?: AssertionResult[]
}>()

const emit = defineEmits<{ 'update:modelValue': [value: Assertion[]] }>()

const SOURCES: Array<{ value: AssertionSource; label: string }> = [
  { value: 'status', label: 'Status code' },
  { value: 'response_time', label: 'Response time (ms)' },
  { value: 'json_path', label: 'JSON field' },
  { value: 'header', label: 'Header' },
  { value: 'body', label: 'Raw body' },
]

const OPERATORS: Array<{ value: AssertionOperator; label: string }> = [
  { value: 'equals', label: 'equals' },
  { value: 'not_equals', label: 'does not equal' },
  { value: 'contains', label: 'contains' },
  { value: 'not_contains', label: 'does not contain' },
  { value: 'less_than', label: 'is less than' },
  { value: 'greater_than', label: 'is greater than' },
  { value: 'exists', label: 'exists' },
  { value: 'not_exists', label: 'does not exist' },
  { value: 'is_empty', label: 'is empty' },
  { value: 'is_not_empty', label: 'is not empty' },
  { value: 'matches', label: 'matches regex' },
]

/** Operators that compare against nothing, so the target box is hidden. */
const UNARY: AssertionOperator[] = [
  'exists',
  'not_exists',
  'is_empty',
  'is_not_empty',
]

/** Sources that need a property name (which header, which JSON field). */
const NEEDS_PROPERTY: AssertionSource[] = ['json_path', 'header']

const summary = computed(() => {
  if (!props.results?.length) return null
  const passed = props.results.filter((result) => result.passed).length
  return { passed, total: props.results.length }
})

function update(index: number, patch: Partial<Assertion>) {
  emit(
    'update:modelValue',
    props.modelValue.map((item, i) =>
      i === index ? { ...item, ...patch } : item,
    ),
  )
}

function add() {
  emit('update:modelValue', [...props.modelValue, emptyAssertion()])
}

function remove(index: number) {
  emit(
    'update:modelValue',
    props.modelValue.filter((_, i) => i !== index),
  )
}

function placeholderFor(source: AssertionSource) {
  if (source === 'json_path') return 'user.name  or  items[0].id'
  if (source === 'header') return 'content-type'
  return ''
}
</script>

<template>
  <div class="assert">
    <header class="assert__head">
      <div>
        <p class="assert__title">Assertions</p>
        <p class="assert__sub">
          Checks that run after every send, and on every loop of a collection run.
        </p>
      </div>
      <span
        v-if="summary"
        class="badge"
        :class="summary.passed === summary.total ? 'badge--ok' : 'badge--bad'"
      >
        {{ summary.passed }}/{{ summary.total }} passed
      </span>
    </header>

    <div v-if="!modelValue.length" class="empty-state">
      <AppIcon name="check" :size="24" class="empty-state__icon" :stroke="1.5" />
      <p class="empty-state__title">No assertions yet</p>
      <p class="empty-state__hint">
        Add one to check the status code, a JSON field, a header, or how long
        the response took.
      </p>
      <button class="btn btn--primary" type="button" @click="add">
        Add assertion
      </button>
    </div>

    <template v-else>
      <ul class="assert__list">
        <li
          v-for="(item, index) in modelValue"
          :key="index"
          class="assert__row"
          :class="{
            'assert__row--pass': results?.[index]?.passed === true,
            'assert__row--fail': results?.[index]?.passed === false,
          }"
        >
          <input
            class="checkbox"
            type="checkbox"
            :checked="item.enabled"
            aria-label="Enable assertion"
            @change="
              update(index, {
                enabled: ($event.target as HTMLInputElement).checked,
              })
            "
          />

          <select
            class="select assert__source"
            :value="item.source"
            aria-label="What to check"
            @change="
              update(index, {
                source: ($event.target as HTMLSelectElement)
                  .value as AssertionSource,
              })
            "
          >
            <option v-for="s in SOURCES" :key="s.value" :value="s.value">
              {{ s.label }}
            </option>
          </select>

          <input
            v-if="NEEDS_PROPERTY.includes(item.source)"
            class="input input--mono assert__property"
            :value="item.property"
            :placeholder="placeholderFor(item.source)"
            spellcheck="false"
            aria-label="Property"
            @input="
              update(index, {
                property: ($event.target as HTMLInputElement).value,
              })
            "
          />
          <span v-else />

          <select
            class="select assert__operator"
            :value="item.operator"
            aria-label="Comparison"
            @change="
              update(index, {
                operator: ($event.target as HTMLSelectElement)
                  .value as AssertionOperator,
              })
            "
          >
            <option v-for="o in OPERATORS" :key="o.value" :value="o.value">
              {{ o.label }}
            </option>
          </select>

          <input
            v-if="!UNARY.includes(item.operator)"
            class="input input--mono assert__target"
            :value="item.target"
            placeholder="Expected value"
            spellcheck="false"
            aria-label="Expected value"
            @input="
              update(index, { target: ($event.target as HTMLInputElement).value })
            "
          />
          <span v-else />

          <button
            class="btn btn--ghost btn--icon btn--sm"
            type="button"
            aria-label="Remove assertion"
            @click="remove(index)"
          >
            <AppIcon name="close" :size="12" />
          </button>

          <p v-if="results?.[index] && !results[index].passed" class="assert__error">
            {{ results[index].message || 'Assertion failed' }}
          </p>
        </li>
      </ul>

      <button class="btn btn--sm" type="button" @click="add">
        + Add assertion
      </button>
    </template>
  </div>
</template>

<style scoped>
.assert { display: flex; flex-direction: column; gap: var(--space-3); }

.assert__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}
.assert__title { font-weight: 600; }
.assert__sub { font-size: var(--text-xs); color: var(--text-muted); }

.assert__list { display: flex; flex-direction: column; gap: var(--space-2); }

.assert__row {
  display: grid;
  grid-template-columns: 24px 150px minmax(0, 1fr) 150px minmax(0, 1fr) 28px;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
.assert__row--pass { border-left-color: var(--ok); }
.assert__row--fail { border-left-color: var(--danger); }

.assert__row > select,
.assert__row > input:not(.checkbox) { height: 30px; }

.assert__error {
  grid-column: 2 / -1;
  font-size: var(--text-xs);
  color: var(--danger);
  font-family: var(--font-mono);
}

@media (max-width: 860px) {
  .assert__row {
    grid-template-columns: 24px 1fr 28px;
    grid-auto-rows: min-content;
    row-gap: var(--space-2);
  }
  .assert__row > :nth-child(2) { grid-column: 2 / 3; }
  .assert__row > :nth-child(3),
  .assert__row > :nth-child(4),
  .assert__row > :nth-child(5) { grid-column: 2 / 4; }
  .assert__error { grid-column: 1 / -1; }
}
</style>
