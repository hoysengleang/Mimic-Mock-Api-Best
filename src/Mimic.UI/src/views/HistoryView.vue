<script setup lang="ts">
import { onMounted } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import CodeEditor from '@/components/common/CodeEditor.vue'
import MethodBadge from '@/components/common/MethodBadge.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useHistoryStore } from '@/stores/history'

const history = useHistoryStore()

function relativeTime(iso: string) {
  const then = new Date(iso).getTime()
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

function prettify(body: string) {
  try {
    return JSON.stringify(JSON.parse(body), null, 2)
  } catch {
    return body
  }
}

onMounted(() => history.load())
</script>

<template>
  <div class="history">
    <aside class="list-pane">
      <header class="list-pane__head">
        <div>
          <h1 class="list-pane__title">History</h1>
          <p class="list-pane__sub">{{ history.total }} request(s) recorded</p>
        </div>
        <button
          v-if="history.entries.length"
          class="btn btn--sm"
          type="button"
          @click="history.clear()"
        >
          Clear
        </button>
      </header>

      <div class="list-pane__body scroll-y">
        <p v-if="history.loading" class="list-pane__status">Loading…</p>

        <div v-else-if="!history.entries.length" class="empty-state">
          <AppIcon name="history" :size="26" class="empty-state__icon" :stroke="1.4" />
          <p class="empty-state__title">Nothing here yet</p>
          <p class="empty-state__hint">
            Every request you send is recorded here, with its response and
            timing. Credentials are masked before anything is stored.
          </p>
        </div>

        <ul v-else class="entries">
          <li v-for="entry in history.entries" :key="entry.id">
            <button
              class="entry"
              :class="{ 'entry--on': history.selected?.id === entry.id }"
              type="button"
              @click="history.selected = entry"
            >
              <div class="entry__top">
                <MethodBadge :method="entry.method" size="sm" />
                <span
                  class="entry__status mono"
                  :class="{
                    'entry__status--bad':
                      entry.status_code === null || entry.status_code >= 400,
                  }"
                >{{ entry.status_code ?? 'ERR' }}</span>
                <span class="entry__time">{{ relativeTime(entry.created_at) }}</span>
              </div>
              <p class="entry__url truncate mono">{{ entry.url }}</p>
              <p class="entry__meta">
                {{ entry.duration_ms.toFixed(0) }} ms · {{ entry.response_size }} B
              </p>
            </button>
          </li>
        </ul>
      </div>
    </aside>

    <section class="detail">
      <div v-if="!history.selected" class="empty-state">
        <AppIcon name="response" :size="26" class="empty-state__icon" :stroke="1.4" />
        <p class="empty-state__title">Select a request</p>
        <p class="empty-state__hint">Pick an entry to see its full response.</p>
      </div>

      <template v-else>
        <header class="detail__head">
          <MethodBadge :method="history.selected.method" />
          <StatusBadge :status="history.selected.status_code" />
          <span class="detail__meta">{{ history.selected.duration_ms.toFixed(0) }} ms</span>
          <div class="detail__spacer" />
          <button
            class="btn btn--ghost btn--sm"
            type="button"
            @click="history.remove(history.selected!.id)"
          >
            Delete
          </button>
        </header>

        <p class="detail__url mono">{{ history.selected.url }}</p>

        <p v-if="history.selected.error" class="detail__error">
          {{ history.selected.error }}
        </p>

        <div class="detail__section">
          <span class="label">Request headers</span>
          <dl v-if="Object.keys(history.selected.request_headers).length" class="kvlist">
            <template v-for="(value, key) in history.selected.request_headers" :key="key">
              <dt>{{ key }}</dt>
              <dd>{{ value }}</dd>
            </template>
          </dl>
          <p v-else class="detail__none">None</p>
        </div>

        <div class="detail__section detail__section--grow">
          <span class="label">Response body</span>
          <CodeEditor
            v-if="history.selected.response_body"
            :model-value="prettify(history.selected.response_body)"
            language="json"
            readonly
            min-height="240px"
          />
          <p v-else class="detail__none">Empty</p>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.history { display: flex; flex: 1; min-height: 0; min-width: 0; }

.list-pane {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--surface);
  min-height: 0;
}

.list-pane__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
}
.list-pane__title { font-size: var(--text-lg); font-weight: 650; }
.list-pane__sub { font-size: var(--text-xs); color: var(--text-muted); }
.list-pane__body { flex: 1; min-height: 0; padding: var(--space-2); }
.list-pane__status { padding: var(--space-4); color: var(--text-muted); }

.entries { display: flex; flex-direction: column; gap: var(--space-1); }

.entry {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border-radius: var(--radius);
  border: 1px solid transparent;
  text-align: left;
}
.entry:hover { background: var(--surface-hover); }
.entry--on { background: var(--accent-soft); border-color: var(--accent); }

.entry__top { display: flex; align-items: center; gap: var(--space-2); }
.entry__status { font-size: var(--text-xs); font-weight: 700; color: var(--ok); }
.entry__status--bad { color: var(--danger); }
.entry__time { margin-left: auto; font-size: var(--text-xs); color: var(--text-subtle); }
.entry__url { font-size: var(--text-xs); color: var(--text-muted); }
.entry__meta { font-size: var(--text-xs); color: var(--text-subtle); }

.detail {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  overflow-y: auto;
}

.detail__head { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.detail__meta { font-size: var(--text-sm); color: var(--text-muted); }
.detail__spacer { flex: 1; }

.detail__url {
  font-size: var(--text-sm);
  color: var(--text-muted);
  word-break: break-all;
  padding: var(--space-2) var(--space-3);
  background: var(--surface);
  border-radius: var(--radius);
}

.detail__error {
  padding: var(--space-3);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  color: var(--danger);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.detail__section { display: flex; flex-direction: column; }
.detail__section--grow { flex: 1; min-height: 240px; }
.detail__none { font-size: var(--text-sm); color: var(--text-subtle); }

.kvlist {
  display: grid;
  grid-template-columns: minmax(120px, auto) 1fr;
  gap: var(--space-1) var(--space-4);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.kvlist dt { color: var(--accent); word-break: break-all; }
.kvlist dd { color: var(--text-muted); word-break: break-all; }

@media (max-width: 900px) {
  .history { flex-direction: column; }
  .list-pane { width: 100%; max-height: 40%; border-right: none; border-bottom: 1px solid var(--border); }
}
</style>
