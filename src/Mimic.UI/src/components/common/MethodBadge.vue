<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ method: string; size?: 'sm' | 'md' }>(),
  { size: 'md' },
)

const color = computed(
  () => `var(--method-${props.method.toLowerCase()}, var(--text-muted))`,
)
</script>

<template>
  <span
    class="method"
    :class="[`method--${size}`]"
    :style="{
      color,
      // A tint of the method's own colour rather than a border — quieter in
      // a long list, and it keeps the row height honest.
      background: `color-mix(in srgb, ${color} 12%, transparent)`,
    }"
  >{{ method }}</span>
</template>

<style scoped>
.method {
  display: inline-block;
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-weight: 700;
  letter-spacing: var(--tracking-mono);
  text-align: center;
  border-radius: var(--radius-sm);
}

.method--md {
  font-size: var(--text-2xs);
  padding: 3px 7px;
  min-width: 54px;
}

.method--sm {
  font-size: 0.625rem;
  padding: 2px 5px;
  min-width: 46px;
}
</style>
