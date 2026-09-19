<script setup lang="ts">
import type { AuthConfig, AuthType } from '@/types'

const props = defineProps<{ modelValue: AuthConfig; suggestions?: string[] }>()
const emit = defineEmits<{ 'update:modelValue': [value: AuthConfig] }>()

const TYPES: Array<{ value: AuthType; label: string; hint: string }> = [
  { value: 'none', label: 'No auth', hint: 'Send the request without credentials.' },
  {
    value: 'bearer',
    label: 'Bearer token',
    hint: 'Sends "Authorization: Bearer <token>".',
  },
  {
    value: 'basic',
    label: 'Basic auth',
    hint: 'Sends a base64-encoded username and password.',
  },
  {
    value: 'apikey',
    label: 'API key',
    hint: 'Sends a named key, as a header or a query parameter.',
  },
]

function patch(changes: Partial<AuthConfig>) {
  emit('update:modelValue', { ...props.modelValue, ...changes })
}
</script>

<template>
  <div class="auth">
    <div class="auth__types">
      <button
        v-for="option in TYPES"
        :key="option.value"
        class="auth__type"
        :class="{ 'auth__type--on': modelValue.type === option.value }"
        type="button"
        @click="patch({ type: option.value })"
      >
        {{ option.label }}
      </button>
    </div>

    <p class="auth__hint">
      {{ TYPES.find((t) => t.value === modelValue.type)?.hint }}
    </p>

    <div v-if="modelValue.type === 'bearer'" class="auth__fields">
      <label class="auth__field">
        <span class="label">Token</span>
        <input
          class="input input--mono"
          :value="modelValue.token"
          placeholder="{{token}} or a literal value"
          spellcheck="false"
          @input="patch({ token: ($event.target as HTMLInputElement).value })"
        />
      </label>
    </div>

    <div v-else-if="modelValue.type === 'basic'" class="auth__fields auth__fields--two">
      <label class="auth__field">
        <span class="label">Username</span>
        <input
          class="input input--mono"
          :value="modelValue.username"
          spellcheck="false"
          @input="patch({ username: ($event.target as HTMLInputElement).value })"
        />
      </label>
      <label class="auth__field">
        <span class="label">Password</span>
        <input
          class="input input--mono"
          type="password"
          :value="modelValue.password"
          @input="patch({ password: ($event.target as HTMLInputElement).value })"
        />
      </label>
    </div>

    <div v-else-if="modelValue.type === 'apikey'" class="auth__fields auth__fields--three">
      <label class="auth__field">
        <span class="label">Key name</span>
        <input
          class="input input--mono"
          :value="modelValue.key"
          placeholder="X-API-Key"
          spellcheck="false"
          @input="patch({ key: ($event.target as HTMLInputElement).value })"
        />
      </label>
      <label class="auth__field">
        <span class="label">Value</span>
        <input
          class="input input--mono"
          :value="modelValue.value"
          placeholder="{{apiKey}}"
          spellcheck="false"
          @input="patch({ value: ($event.target as HTMLInputElement).value })"
        />
      </label>
      <label class="auth__field">
        <span class="label">Send in</span>
        <select
          class="select"
          :value="modelValue.add_to"
          @change="
            patch({
              add_to: ($event.target as HTMLSelectElement).value as 'header' | 'query',
            })
          "
        >
          <option value="header">Header</option>
          <option value="query">Query string</option>
        </select>
      </label>
    </div>

    <p v-if="modelValue.type !== 'none'" class="auth__note">
      Credentials are masked in history and never written to disk in the clear.
    </p>
  </div>
</template>

<style scoped>
.auth { display: flex; flex-direction: column; gap: var(--space-3); }

.auth__types {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.auth__type {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-raised);
  font-size: var(--text-sm);
  color: var(--text-muted);
  transition: all var(--transition);
}
.auth__type:hover { border-color: var(--border-strong); color: var(--text); }
.auth__type--on {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.auth__hint { font-size: var(--text-sm); color: var(--text-muted); }

.auth__fields { display: grid; gap: var(--space-3); max-width: 720px; }
.auth__fields--two { grid-template-columns: repeat(2, 1fr); }
.auth__fields--three { grid-template-columns: 1fr 1fr 150px; }

.auth__field { display: block; }

.auth__note {
  font-size: var(--text-xs);
  color: var(--text-subtle);
  padding-top: var(--space-1);
}

@media (max-width: 720px) {
  .auth__fields--two,
  .auth__fields--three { grid-template-columns: 1fr; }
}
</style>
