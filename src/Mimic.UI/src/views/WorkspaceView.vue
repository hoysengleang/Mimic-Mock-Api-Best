<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import MethodBadge from '@/components/common/MethodBadge.vue'
import RequestBuilder from '@/components/request/RequestBuilder.vue'
import ResponsePanel from '@/components/response/ResponsePanel.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useWorkspaceStore } from '@/stores/workspace'

const workspace = useWorkspaceStore()
const collections = useCollectionsStore()

/**
 * Percentage of the pane height given to the request builder.
 * Weighted toward the response: a params table is short, but a JSON body you
 * are actually reading wants every row it can get.
 */
const splitPercent = ref(40)
const dragging = ref(false)
const panes = ref<HTMLElement | null>(null)

const savingTab = ref<string | null>(null)
const saveTarget = ref('')

function startDrag() {
  dragging.value = true
  document.body.style.userSelect = 'none'
}

function onDrag(event: MouseEvent) {
  if (!dragging.value || !panes.value) return
  const rect = panes.value.getBoundingClientRect()
  const ratio = ((event.clientY - rect.top) / rect.height) * 100
  splitPercent.value = Math.min(80, Math.max(20, ratio))
}

function stopDrag() {
  dragging.value = false
  document.body.style.userSelect = ''
}

/** Cmd/Ctrl+Enter sends, Cmd/Ctrl+S saves — the two actions used constantly. */
function onKeydown(event: KeyboardEvent) {
  const tab = workspace.activeTab
  if (!tab) return
  const meta = event.metaKey || event.ctrlKey
  if (!meta) return

  if (event.key === 'Enter') {
    event.preventDefault()
    void workspace.send(tab)
  } else if (event.key.toLowerCase() === 's') {
    event.preventDefault()
    if (tab.collectionId) void workspace.save(tab)
    else openSaveDialog()
  }
}

function openSaveDialog() {
  const tab = workspace.activeTab
  if (!tab) return
  saveTarget.value = collections.collections[0]?.id ?? ''
  savingTab.value = tab.tabId
}

async function confirmSave() {
  const tab = workspace.tabs.find((item) => item.tabId === savingTab.value)
  if (!tab || !saveTarget.value) return
  await workspace.save(tab, saveTarget.value)
  savingTab.value = null
}

function saveOrPrompt() {
  const tab = workspace.activeTab
  if (!tab) return
  if (tab.collectionId) void workspace.save(tab)
  else openSaveDialog()
}

onMounted(() => {
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('keydown', onKeydown)
  if (!workspace.tabs.length) workspace.openBlank()
})

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="workspace">
    <AppSidebar />

    <section class="workspace__main">
      <!-- Open tabs -->
      <div class="tabbar">
        <div class="tabbar__list">
          <button
            v-for="tab in workspace.tabs"
            :key="tab.tabId"
            class="tabbar__tab"
            :class="{ 'tabbar__tab--on': tab.tabId === workspace.activeTabId }"
            type="button"
            @click="workspace.selectTab(tab.tabId)"
          >
            <MethodBadge :method="tab.method" size="sm" />
            <span class="truncate">{{ tab.name }}</span>
            <span v-if="tab.dirty" class="tabbar__dot" title="Unsaved changes" />
            <span
              class="tabbar__close"
              role="button"
              tabindex="0"
              aria-label="Close tab"
              @click.stop="workspace.closeTab(tab.tabId)"
              @keydown.enter.stop="workspace.closeTab(tab.tabId)"
            ><AppIcon name="close" :size="11" /></span>
          </button>
        </div>

        <button
          class="btn btn--ghost btn--icon"
          type="button"
          title="New request"
          aria-label="New request"
          @click="workspace.openBlank()"
        >
          <AppIcon name="plus" :size="15" />
        </button>
      </div>

      <!-- Panes -->
      <div v-if="workspace.activeTab" ref="panes" class="panes">
        <div class="panes__top" :style="{ height: `${splitPercent}%` }">
          <RequestBuilder :tab="workspace.activeTab" @save="saveOrPrompt" />
        </div>

        <div
          class="panes__handle"
          :class="{ 'panes__handle--active': dragging }"
          role="separator"
          aria-label="Resize panels"
          @mousedown.prevent="startDrag"
        >
          <span class="panes__grip" />
        </div>

        <div class="panes__bottom">
          <ResponsePanel
            :response="workspace.activeTab.response"
            :sending="workspace.activeTab.sending"
          />
        </div>
      </div>

      <div v-else class="empty-state">
        <AppIcon name="request" :size="26" class="empty-state__icon" :stroke="1.4" />
        <p class="empty-state__title">No request open</p>
        <p class="empty-state__hint">
          Pick one from the sidebar, or start a new one.
        </p>
        <button class="btn btn--primary" type="button" @click="workspace.openBlank()">
          New request
        </button>
      </div>
    </section>

    <!-- Save-into-collection prompt -->
    <BaseModal
      :open="!!savingTab"
      title="Save request"
      width="420px"
      @close="savingTab = null"
    >
      <p v-if="!collections.collections.length" class="save__warn">
        You need a collection first. Create one from the sidebar, then save.
      </p>
      <template v-else>
        <label class="label" for="save-target">Save into</label>
        <select id="save-target" v-model="saveTarget" class="select">
          <option
            v-for="collection in collections.collections"
            :key="collection.id"
            :value="collection.id"
          >
            {{ collection.name }}
          </option>
        </select>
      </template>

      <template #footer>
        <button class="btn" type="button" @click="savingTab = null">Cancel</button>
        <button
          class="btn btn--primary"
          type="button"
          :disabled="!saveTarget"
          @click="confirmSave"
        >
          Save
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.workspace { display: flex; flex: 1; min-height: 0; min-width: 0; }

.workspace__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* --- Tab bar --- */
.tabbar {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-2) 0;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.tabbar__list {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 2px;
  overflow-x: auto;
}

.tabbar__tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  max-width: 230px;
  padding: var(--space-3) var(--space-3);
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: var(--radius) var(--radius) 0 0;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  letter-spacing: var(--tracking-mono);
  white-space: nowrap;
}
.tabbar__tab:hover { background: var(--surface-hover); color: var(--text); }
.tabbar__tab--on {
  background: var(--bg);
  border-color: var(--border);
  color: var(--text);
}

.tabbar__dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.tabbar__close {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 16px; height: 16px;
  border-radius: var(--radius-sm);
  color: var(--text-subtle);
  cursor: pointer;
  transition: background var(--transition), color var(--transition);
}
.tabbar__close:hover { background: var(--surface-active); color: var(--danger); }

/* --- Split panes --- */
.panes {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

.panes__top { min-height: 0; overflow: hidden; }
.panes__bottom { flex: 1; min-height: 0; overflow: hidden; }

.panes__handle {
  height: 8px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  cursor: row-resize;
  background: var(--surface);
  border-block: 1px solid var(--border);
}
.panes__handle:hover, .panes__handle--active { background: var(--accent-soft); }

.panes__grip {
  width: 36px;
  height: 2px;
  border-radius: 2px;
  background: var(--border-strong);
}
.panes__handle:hover .panes__grip { background: var(--accent); }

.save__warn { color: var(--warn); font-size: var(--text-sm); }

@media (max-width: 860px) {
  .workspace { flex-direction: column; }
}
</style>
