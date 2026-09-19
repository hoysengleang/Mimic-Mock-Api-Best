<script setup lang="ts">
import { RouterLink } from 'vue-router'

import AppIcon from '@/components/common/AppIcon.vue'
import AppLogo from '@/components/common/AppLogo.vue'
import type { IconName } from '@/components/common/icons'
import { useEnvironmentsStore } from '@/stores/environments'
import { useUiStore } from '@/stores/ui'

const environments = useEnvironmentsStore()
const ui = useUiStore()

const NAV: Array<{ to: string; label: string; icon: IconName; title: string }> = [
  { to: '/', label: 'Build', icon: 'request', title: 'Compose and send requests' },
  { to: '/mocks', label: 'Mocks', icon: 'mock', title: 'Define mock endpoints' },
  { to: '/runner', label: 'Runner', icon: 'runner', title: 'Run collections in a loop' },
  { to: '/history', label: 'History', icon: 'history', title: 'Past requests' },
  { to: '/environments', label: 'Variables', icon: 'variable', title: 'Environment variables' },
]

function onEnvironmentChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  void environments.activate(value || null)
}
</script>

<template>
  <header class="header">
    <RouterLink to="/" class="brand" aria-label="Mimic home">
      <AppLogo :size="26" />
    </RouterLink>

    <nav class="nav">
      <RouterLink
        v-for="item in NAV"
        :key="item.to"
        :to="item.to"
        class="nav__link"
        :title="item.title"
      >
        <AppIcon :name="item.icon" :size="14" />
        <span class="nav__label">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="header__spacer" />

    <label class="env">
      <span class="visually-hidden">Active environment</span>
      <span class="env__dot" :class="{ 'env__dot--on': environments.activeId }" />
      <select
        class="select env__select"
        :value="environments.activeId ?? ''"
        @change="onEnvironmentChange"
      >
        <option value="">No environment</option>
        <option v-for="item in environments.environments" :key="item.id" :value="item.id">
          {{ item.name }}
        </option>
      </select>
    </label>

    <button
      class="btn btn--ghost theme-btn"
      type="button"
      :title="`${ui.currentTheme.label} — click for ${ui.nextTheme.label} (${ui.nextTheme.description})`"
      :aria-label="`Theme: ${ui.currentTheme.label}. Switch to ${ui.nextTheme.label}.`"
      @click="ui.cycleTheme()"
    >
      <AppIcon :name="ui.currentTheme.icon" :size="15" />
      <span class="theme-btn__label">{{ ui.currentTheme.label }}</span>
    </button>
  </header>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  height: var(--header-height);
  flex-shrink: 0;
  padding: 0 var(--space-3);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.brand {
  display: flex;
  align-items: center;
  padding-right: var(--space-3);
  margin-right: var(--space-1);
  border-right: 1px solid var(--border);
  height: 28px;
}
.brand:hover { text-decoration: none; }

.nav { display: flex; gap: 2px; }

.nav__link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: 30px;
  padding: 0 var(--space-3);
  border-radius: var(--radius);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: var(--tracking-mono);
  transition: background var(--transition), color var(--transition);
}
.nav__link:hover { background: var(--surface-hover); color: var(--text); text-decoration: none; }
.nav__link.router-link-active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.header__spacer { flex: 1; }

.env { display: flex; align-items: center; gap: var(--space-2); }

.env__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border-strong);
  flex-shrink: 0;
  transition: background var(--transition);
}
.env__dot--on { background: var(--ok); }

.env__select { width: 176px; }

.theme-btn { padding: 0 var(--space-3); }
.theme-btn__label { font-size: var(--text-2xs); }

@media (max-width: 960px) {
  .nav__label { display: none; }
  .nav__link { padding: 0 var(--space-2); }
}
@media (max-width: 720px) {
  .brand { padding-right: var(--space-2); }
  .env__select { width: 124px; }
  .theme-btn__label { display: none; }
  .theme-btn { width: 34px; padding: 0; }
}
</style>
