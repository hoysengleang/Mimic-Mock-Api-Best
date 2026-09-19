<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/common/AppIcon.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import MethodBadge from '@/components/common/MethodBadge.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useUiStore } from '@/stores/ui'
import { useWorkspaceStore } from '@/stores/workspace'
import type { CollectionDetail, SavedRequest } from '@/types'

const collections = useCollectionsStore()
const workspace = useWorkspaceStore()
const ui = useUiStore()
const router = useRouter()

const creating = ref(false)
const newName = ref('')
const confirmTarget = ref<CollectionDetail | null>(null)

function openRequest(request: SavedRequest) {
  workspace.openRequest(request)
  if (router.currentRoute.value.name !== 'workspace') router.push('/')
}

async function createCollection() {
  const name = newName.value.trim()
  if (!name) return
  try {
    await collections.createCollection(name)
    creating.value = false
    newName.value = ''
  } catch {
    ui.toast('Could not create the collection', 'error')
  }
}

async function confirmDelete() {
  if (!confirmTarget.value) return
  try {
    await collections.deleteCollection(confirmTarget.value.id)
  } catch {
    ui.toast('Could not delete the collection', 'error')
  } finally {
    confirmTarget.value = null
  }
}

function runCollection(collection: CollectionDetail) {
  router.push({ name: 'runner', query: { collection: collection.id } })
}
</script>

<template>
  <aside class="sidebar">
    <header class="sidebar__head">
      <div class="sidebar__searchwrap">
        <AppIcon name="search" :size="13" class="sidebar__searchicon" />
        <input
          v-model="collections.search"
          class="input sidebar__search"
          type="search"
          placeholder="Search requests"
          aria-label="Search requests"
        />
      </div>
      <button
        class="btn btn--icon"
        type="button"
        title="New collection"
        aria-label="New collection"
        @click="creating = true"
      >
        <AppIcon name="plus" :size="15" />
      </button>
    </header>

    <div class="sidebar__body scroll-y">
      <p v-if="collections.loading" class="sidebar__status">Loading…</p>

      <div v-else-if="!collections.filtered.length" class="empty-state">
        <AppIcon name="collection" :size="26" class="empty-state__icon" :stroke="1.4" />
        <p class="empty-state__title">
          {{ collections.search ? 'No matches' : 'No collections yet' }}
        </p>
        <p class="empty-state__hint">
          {{
            collections.search
              ? 'Try a different search term.'
              : 'Create a collection to group and save your requests.'
          }}
        </p>
        <button
          v-if="!collections.search"
          class="btn btn--primary btn--sm"
          type="button"
          @click="creating = true"
        >
          New collection
        </button>
      </div>

      <ul v-else class="tree">
        <li
          v-for="collection in collections.filtered"
          :key="collection.id"
          class="tree__group"
        >
          <div class="tree__collection">
            <button
              class="tree__toggle"
              type="button"
              :aria-expanded="collections.expanded.has(collection.id)"
              @click="collections.toggleExpanded(collection.id)"
            >
              <AppIcon
                name="chevron"
                :size="12"
                class="tree__chevron"
                :class="{ 'tree__chevron--open': collections.expanded.has(collection.id) }"
              />
              <span class="tree__name truncate">{{ collection.name }}</span>
              <span class="tree__count">{{ collection.requests.length }}</span>
            </button>

            <div class="tree__actions">
              <button
                class="btn btn--ghost btn--icon btn--sm"
                type="button"
                title="Run this collection"
                :aria-label="`Run ${collection.name}`"
                @click="runCollection(collection)"
              >
                <AppIcon name="play" :size="12" />
              </button>
              <button
                class="btn btn--ghost btn--icon btn--sm"
                type="button"
                title="Delete collection"
                :aria-label="`Delete ${collection.name}`"
                @click="confirmTarget = collection"
              >
                <AppIcon name="trash" :size="13" />
              </button>
            </div>
          </div>

          <ul v-if="collections.expanded.has(collection.id)" class="tree__requests">
            <li v-if="!collection.requests.length" class="tree__hint">
              No requests yet
            </li>
            <li v-for="request in collection.requests" :key="request.id">
              <button
                class="tree__request"
                :class="{
                  'tree__request--on':
                    workspace.activeTab?.requestId === request.id,
                }"
                type="button"
                @click="openRequest(request)"
              >
                <MethodBadge :method="request.method" size="sm" />
                <span class="truncate">{{ request.name }}</span>
              </button>
            </li>
          </ul>
        </li>
      </ul>
    </div>

    <!-- New collection -->
    <BaseModal
      :open="creating"
      title="New collection"
      width="420px"
      @close="creating = false"
    >
      <label class="label" for="collection-name">Name</label>
      <input
        id="collection-name"
        v-model="newName"
        class="input"
        placeholder="e.g. User API"
        @keydown.enter="createCollection"
      />
      <template #footer>
        <button class="btn" type="button" @click="creating = false">Cancel</button>
        <button
          class="btn btn--primary"
          type="button"
          :disabled="!newName.trim()"
          @click="createCollection"
        >
          Create
        </button>
      </template>
    </BaseModal>

    <!-- Delete confirmation -->
    <BaseModal
      :open="!!confirmTarget"
      title="Delete collection?"
      width="420px"
      @close="confirmTarget = null"
    >
      <p>
        <strong>{{ confirmTarget?.name }}</strong> and its
        {{ confirmTarget?.requests.length }} request(s) will be permanently
        removed. This cannot be undone.
      </p>
      <template #footer>
        <button class="btn" type="button" @click="confirmTarget = null">
          Cancel
        </button>
        <button class="btn btn--danger" type="button" @click="confirmDelete">
          Delete
        </button>
      </template>
    </BaseModal>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: var(--surface);
  min-height: 0;
}

.sidebar__head {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3);
  border-bottom: 1px solid var(--border);
}

.sidebar__searchwrap { position: relative; flex: 1; min-width: 0; }

.sidebar__searchicon {
  position: absolute;
  left: var(--space-2);
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-subtle);
  pointer-events: none;
}

.sidebar__search { width: 100%; padding-left: calc(var(--space-4) + var(--space-3)); }
.sidebar__search::-webkit-search-cancel-button { filter: grayscale(1) opacity(0.5); }

.sidebar__body { flex: 1; min-height: 0; padding: var(--space-2); }
.sidebar__status { padding: var(--space-4); color: var(--text-muted); font-size: var(--text-sm); }

.tree { display: flex; flex-direction: column; gap: var(--space-1); }

.tree__collection {
  display: flex;
  align-items: center;
  border-radius: var(--radius);
}
.tree__collection:hover { background: var(--surface-hover); }
.tree__collection:hover .tree__actions { opacity: 1; }

.tree__toggle {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: var(--tracking-mono);
  text-align: left;
}

.tree__chevron {
  flex-shrink: 0;
  color: var(--text-subtle);
  transition: transform var(--transition);
}
.tree__chevron--open { transform: rotate(90deg); }

.tree__name { flex: 1; min-width: 0; }

.tree__count {
  flex-shrink: 0;
  padding: 0 6px;
  border-radius: 9px;
  background: var(--surface-active);
  color: var(--text-subtle);
  font-size: 0.625rem;
  font-weight: 700;
}

.tree__actions {
  display: flex;
  gap: 2px;
  padding-right: var(--space-1);
  opacity: 0;
  transition: opacity var(--transition);
}
.tree__actions:focus-within { opacity: 1; }

.tree__requests {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-left: var(--space-4);
  margin-top: 1px;
}

.tree__hint {
  padding: var(--space-2);
  font-size: var(--text-xs);
  color: var(--text-subtle);
  font-style: italic;
}

.tree__request {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-align: left;
  transition: background var(--transition), color var(--transition);
}
.tree__request:hover { background: var(--surface-hover); color: var(--text); }
.tree__request--on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
</style>
