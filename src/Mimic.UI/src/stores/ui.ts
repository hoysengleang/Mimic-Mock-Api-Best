/** Theme, toasts and layout state. */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { IconName } from '@/components/common/icons'

export type ToastKind = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  kind: ToastKind
  message: string
}

/**
 * Three named themes rather than a light/dark switch.
 *
 * Paper and Slate are the same design in two brightnesses. Terminal is a
 * genuinely different direction — denser, higher contrast, amber accent —
 * offered as a real alternative rather than a third tint.
 */
export type Theme = 'paper' | 'slate' | 'terminal'

export interface ThemeOption {
  value: Theme
  label: string
  description: string
  icon: IconName
  /** Value written to `data-theme`; drives the CSS custom properties. */
  attribute: 'light' | 'dark' | 'terminal'
}

export const THEMES: ThemeOption[] = [
  {
    value: 'paper',
    label: 'Paper',
    description: 'Light and airy. The default.',
    icon: 'sun',
    attribute: 'light',
  },
  {
    value: 'slate',
    label: 'Slate',
    description: 'The same design, dark.',
    icon: 'moon',
    attribute: 'dark',
  },
  {
    value: 'terminal',
    label: 'Terminal',
    description: 'Denser, higher contrast, amber accent.',
    icon: 'terminal',
    attribute: 'terminal',
  },
]

const THEME_KEY = 'mimic.theme'

function initialTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored && THEMES.some((option) => option.value === stored)) {
    return stored as Theme
  }
  // Older builds stored the raw attribute value.
  if (stored === 'light') return 'paper'
  if (stored === 'dark') return 'slate'

  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'slate'
    : 'paper'
}

let nextToastId = 1

export const useUiStore = defineStore('ui', () => {
  const theme = ref<Theme>(initialTheme())
  const toasts = ref<Toast[]>([])
  const sidebarCollapsed = ref(false)

  const currentTheme = computed(
    () => THEMES.find((option) => option.value === theme.value) ?? THEMES[0]!,
  )

  const nextTheme = computed(() => {
    const index = THEMES.findIndex((option) => option.value === theme.value)
    return THEMES[(index + 1) % THEMES.length]!
  })

  function applyTheme() {
    document.documentElement.setAttribute(
      'data-theme',
      currentTheme.value.attribute,
    )
    localStorage.setItem(THEME_KEY, theme.value)
  }

  function setTheme(value: Theme) {
    theme.value = value
    applyTheme()
  }

  /** Step to the next theme. Bound to the header button. */
  function cycleTheme() {
    setTheme(nextTheme.value.value)
  }

  function toast(message: string, kind: ToastKind = 'info') {
    const id = nextToastId++
    toasts.value.push({ id, kind, message })
    // Errors linger; successes get out of the way.
    setTimeout(() => dismiss(id), kind === 'error' ? 6000 : 3000)
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((item) => item.id !== id)
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    theme,
    currentTheme,
    nextTheme,
    toasts,
    sidebarCollapsed,
    applyTheme,
    setTheme,
    cycleTheme,
    toast,
    dismiss,
    toggleSidebar,
  }
})
