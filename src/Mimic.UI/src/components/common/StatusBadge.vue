<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: number | null; text?: string }>()

/** 2xx green, 3xx blue, 4xx amber, 5xx red — the convention every API tool uses. */
const tone = computed(() => {
  const code = props.status
  if (code === null) return 'danger'
  if (code < 300) return 'ok'
  if (code < 400) return 'info'
  if (code < 500) return 'warn'
  return 'danger'
})

const label = computed(() =>
  props.status === null
    ? 'Failed'
    : `${props.status}${props.text ? ` ${props.text}` : ''}`,
)
</script>

<template>
  <span class="status" :class="`status--${tone}`">
    <span class="status__dot" />
    {{ label }}
  </span>
</template>

<style scoped>
.status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px var(--space-3);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: var(--tracking-mono);
  white-space: nowrap;
}

.status--ok     { background: var(--chip-ok-bg);     color: var(--chip-ok-fg); }
.status--info   { background: var(--chip-info-bg);   color: var(--chip-info-fg); }
.status--warn   { background: var(--chip-warn-bg);   color: var(--chip-warn-fg); }
.status--danger { background: var(--chip-danger-bg); color: var(--chip-danger-fg); }

.status__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>
