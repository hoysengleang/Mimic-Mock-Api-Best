<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import type { IconName } from '@/components/common/icons'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()

const icons: Record<string, IconName> = {
  success: 'check',
  error: 'alert',
  info: 'info',
}
</script>

<template>
  <div class="toasts" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <div
        v-for="item in ui.toasts"
        :key="item.id"
        class="toast"
        :class="`toast--${item.kind}`"
      >
        <AppIcon :name="icons[item.kind] ?? 'info'" :size="15" class="toast__icon" />
        <span class="toast__message">{{ item.message }}</span>
        <button
          class="toast__close"
          type="button"
          aria-label="Dismiss"
          @click="ui.dismiss(item.id)"
        >
          <AppIcon name="close" :size="13" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed;
  bottom: var(--space-4);
  right: var(--space-4);
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: min(420px, calc(100vw - var(--space-8)));
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  background: var(--surface-raised);
  box-shadow: var(--shadow-lg);
  font-size: var(--text-sm);
}

.toast--success { border-left-color: var(--ok); }
.toast--error   { border-left-color: var(--danger); }
.toast--info    { border-left-color: var(--info); }

.toast__icon { flex-shrink: 0; margin-top: 1px; color: var(--info); }
.toast--success .toast__icon { color: var(--ok); }
.toast--error   .toast__icon { color: var(--danger); }

.toast__message { flex: 1; word-break: break-word; }

.toast__close {
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--text-subtle);
  transition: color var(--transition);
}
.toast__close:hover { color: var(--text); }

.toast-enter-active,
.toast-leave-active { transition: all 200ms ease; }
.toast-enter-from { opacity: 0; transform: translateX(16px); }
.toast-leave-to   { opacity: 0; transform: translateX(16px); }
</style>
