<script setup lang="ts">
import { computed } from 'vue'

import { ICON_PATHS, type IconName } from '@/components/common/icons'

const props = withDefaults(
  defineProps<{ name: IconName; size?: number | string; stroke?: number }>(),
  { size: 16, stroke: 1.75 },
)

const path = computed(() => ICON_PATHS[props.name] ?? ICON_PATHS.info)
const dimension = computed(() =>
  typeof props.size === 'number' ? `${props.size}px` : props.size,
)
</script>

<template>
  <svg
    :width="dimension"
    :height="dimension"
    viewBox="0 0 24 24"
    fill="none"
    :stroke-width="stroke"
    stroke="currentColor"
    stroke-linecap="round"
    aria-hidden="true"
    focusable="false"
    v-html="path"
  />
</template>
