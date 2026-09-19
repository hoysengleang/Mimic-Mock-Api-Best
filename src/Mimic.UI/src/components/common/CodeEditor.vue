<script setup lang="ts">
/**
 * CodeMirror 6 wrapper with two-way binding.
 *
 * The editor is rebuilt when the language or theme changes, because
 * reconfiguring compartments for this few options is more moving parts than
 * simply recreating a cheap editor.
 */
import { json } from '@codemirror/lang-json'
import { xml } from '@codemirror/lang-xml'
import { EditorState, type Extension } from '@codemirror/state'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorView, basicSetup } from 'codemirror'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { useUiStore } from '@/stores/ui'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: 'json' | 'xml' | 'text'
    readonly?: boolean
    placeholder?: string
    minHeight?: string
  }>(),
  {
    language: 'json',
    readonly: false,
    placeholder: '',
    minHeight: '160px',
  },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const ui = useUiStore()
const host = ref<HTMLDivElement | null>(null)
let view: EditorView | null = null

function languageExtension(): Extension[] {
  if (props.language === 'json') return [json()]
  if (props.language === 'xml') return [xml()]
  return []
}

function baseTheme() {
  return EditorView.theme({
    '&': {
      fontSize: 'var(--text-sm)',
      backgroundColor: 'transparent',
      height: '100%',
    },
    '.cm-content': {
      fontFamily: 'var(--font-mono)',
      padding: 'var(--space-3) 0',
    },
    '.cm-gutters': {
      backgroundColor: 'transparent',
      border: 'none',
      color: 'var(--text-subtle)',
    },
    '.cm-activeLine': { backgroundColor: 'var(--surface-hover)' },
    '.cm-activeLineGutter': { backgroundColor: 'transparent' },
    '&.cm-focused': { outline: 'none' },
    '.cm-scroller': { overflow: 'auto' },
  })
}

function build() {
  if (!host.value) return
  view?.destroy()

  const extensions: Extension[] = [
    basicSetup,
    ...languageExtension(),
    baseTheme(),
    EditorView.lineWrapping,
    EditorState.readOnly.of(props.readonly),
    EditorView.updateListener.of((update) => {
      if (update.docChanged && !props.readonly) {
        emit('update:modelValue', update.state.doc.toString())
      }
    }),
  ]

  // Any theme that is not Paper wants the dark syntax palette.
  if (ui.currentTheme.attribute !== 'light') extensions.push(oneDark)

  view = new EditorView({
    state: EditorState.create({ doc: props.modelValue, extensions }),
    parent: host.value,
  })
}

onMounted(build)
onBeforeUnmount(() => view?.destroy())

// External changes (loading a saved request, formatting) push into the editor.
watch(
  () => props.modelValue,
  (value) => {
    if (!view || value === view.state.doc.toString()) return
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: value },
    })
  },
)

watch(() => [props.language, props.readonly, ui.theme], build)

defineExpose({
  focus: () => view?.focus(),
})
</script>

<template>
  <div class="editor" :style="{ minHeight }">
    <div ref="host" class="editor__host" />
    <p v-if="!modelValue && placeholder" class="editor__placeholder">
      {{ placeholder }}
    </p>
  </div>
</template>

<style scoped>
.editor {
  position: relative;
  height: 100%;
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.editor__host {
  height: 100%;
}

.editor__placeholder {
  position: absolute;
  top: var(--space-3);
  left: calc(var(--space-6) + var(--space-3));
  color: var(--text-subtle);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  pointer-events: none;
}

:deep(.cm-editor) {
  height: 100%;
}
</style>
