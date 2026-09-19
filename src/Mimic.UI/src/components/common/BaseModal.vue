<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'

const props = withDefaults(
  defineProps<{ open: boolean; title: string; width?: string }>(),
  { width: '520px' },
)

const emit = defineEmits<{ close: [] }>()

const panel = ref<HTMLElement | null>(null)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.open) emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

// Move focus into the dialog so keyboard and screen-reader users land inside it.
watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) return
    await Promise.resolve()
    panel.value?.querySelector<HTMLElement>(
      'input, textarea, select, button',
    )?.focus()
  },
)
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="overlay" @click.self="emit('close')">
        <div
          ref="panel"
          class="panel"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          :style="{ maxWidth: width }"
        >
          <header class="panel__head">
            <h2 class="panel__title">{{ title }}</h2>
            <button
              class="btn btn--ghost btn--icon btn--sm"
              type="button"
              aria-label="Close"
              @click="emit('close')"
            >
              <AppIcon name="close" :size="14" />
            </button>
          </header>

          <div class="panel__body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="panel__foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(2px);
}

.panel {
  width: 100%;
  max-height: calc(100vh - var(--space-8));
  display: flex;
  flex-direction: column;
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
}

.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
}

.panel__title { font-size: var(--text-lg); font-weight: 600; }

.panel__body {
  padding: var(--space-4);
  overflow-y: auto;
}

.panel__foot {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: var(--space-4);
  border-top: 1px solid var(--border);
}

.modal-enter-active,
.modal-leave-active { transition: opacity 160ms ease; }
.modal-enter-from,
.modal-leave-to { opacity: 0; }
.modal-enter-active .panel { transition: transform 160ms ease; }
.modal-enter-from .panel { transform: scale(0.97); }
</style>
