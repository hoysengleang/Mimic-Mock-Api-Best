<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppIcon from '@/components/common/AppIcon.vue'
import MethodBadge from '@/components/common/MethodBadge.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useEnvironmentsStore } from '@/stores/environments'
import { useRunnerStore } from '@/stores/runner'

const runner = useRunnerStore()
const collections = useCollectionsStore()
const environments = useEnvironmentsStore()
const route = useRoute()

const selectedId = ref('')
const expandedIteration = ref<number | null>(null)

const selected = computed(() =>
  collections.collections.find((item) => item.id === selectedId.value) ?? null,
)

const plannedRequests = computed(
  () => (selected.value?.requests.length ?? 0) * runner.iterations,
)

/** Per-iteration rollup, so a 50-loop run stays readable. */
const iterationSummary = computed(() => {
  const result = runner.current
  if (!result) return []

  const buckets = new Map<
    number,
    { iteration: number; passed: number; failed: number; durationMs: number }
  >()

  for (const step of result.results) {
    const bucket = buckets.get(step.iteration) ?? {
      iteration: step.iteration,
      passed: 0,
      failed: 0,
      durationMs: 0,
    }
    bucket.passed += step.assertions_passed
    bucket.failed += step.assertions_failed
    bucket.durationMs += step.duration_ms
    buckets.set(step.iteration, bucket)
  }

  return [...buckets.values()].sort((a, b) => a.iteration - b.iteration)
})

function stepsFor(iteration: number) {
  return runner.current?.results.filter((s) => s.iteration === iteration) ?? []
}

function start() {
  if (!selectedId.value) return
  expandedIteration.value = null
  void runner.run(selectedId.value)
}

onMounted(async () => {
  await runner.loadRecent()
  const fromQuery = route.query.collection
  if (typeof fromQuery === 'string') selectedId.value = fromQuery
  else selectedId.value = collections.collections[0]?.id ?? ''
})

watch(
  () => collections.collections.length,
  () => {
    if (!selectedId.value) selectedId.value = collections.collections[0]?.id ?? ''
  },
)
</script>

<template>
  <div class="runner">
    <!-- Controls -->
    <aside class="controls">
      <h1 class="controls__title">Collection runner</h1>
      <p class="controls__sub">
        Runs every request in a collection and checks its assertions. Loop it
        to catch endpoints that only fail sometimes.
      </p>

      <label class="field">
        <span class="label">Collection</span>
        <select v-model="selectedId" class="select">
          <option v-if="!collections.collections.length" value="">
            No collections yet
          </option>
          <option
            v-for="item in collections.collections"
            :key="item.id"
            :value="item.id"
          >
            {{ item.name }} ({{ item.requests.length }})
          </option>
        </select>
      </label>

      <label class="field">
        <span class="label">Iterations</span>
        <input
          v-model.number="runner.iterations"
          class="input input--mono"
          type="number"
          min="1"
          max="100"
        />
        <span class="field__hint">
          Runs the whole collection this many times.
        </span>
      </label>

      <label class="field">
        <span class="label">Delay between requests (ms)</span>
        <input
          v-model.number="runner.delayMs"
          class="input input--mono"
          type="number"
          min="0"
          max="60000"
          step="50"
        />
        <span class="field__hint">
          Use this to avoid tripping rate limits.
        </span>
      </label>

      <label class="field field--check">
        <input v-model="runner.stopOnFailure" class="checkbox" type="checkbox" />
        <span>Stop at the first failure</span>
      </label>

      <div class="controls__env">
        Environment:
        <strong>{{ environments.active?.name ?? 'none selected' }}</strong>
      </div>

      <p v-if="plannedRequests > 0" class="controls__plan">
        Will send <strong>{{ plannedRequests }}</strong> request(s).
      </p>

      <button
        class="btn btn--primary controls__run"
        type="button"
        :disabled="runner.running || !selectedId || !selected?.requests.length"
        @click="start"
      >
        <span v-if="runner.running" class="spinner" />
        {{ runner.running ? 'Running…' : 'Run collection' }}
      </button>

      <p v-if="selected && !selected.requests.length" class="controls__warn">
        This collection has no requests yet.
      </p>

      <!-- Recent runs -->
      <div v-if="runner.recent.length" class="recent">
        <div class="recent__head">
          <span class="label">Recent runs</span>
          <button class="btn btn--ghost btn--sm" type="button" @click="runner.clear()">
            Clear
          </button>
        </div>
        <ul class="recent__list">
          <li v-for="item in runner.recent.slice(0, 8)" :key="item.id">
            <button class="recent__item" type="button" @click="runner.open(item.id)">
              <span
                class="recent__dot"
                :class="item.status === 'passed' ? 'recent__dot--ok' : 'recent__dot--bad'"
              />
              <span class="truncate">{{ item.collection_name }}</span>
              <span class="recent__score mono">
                {{ item.passed }}/{{ item.passed + item.failed }}
              </span>
            </button>
          </li>
        </ul>
      </div>
    </aside>

    <!-- Results -->
    <section class="results scroll-y">
      <div v-if="runner.running" class="results__center">
        <span class="spinner spinner--lg" />
        <p>Running {{ plannedRequests }} request(s)…</p>
      </div>

      <div v-else-if="!runner.current" class="empty-state">
        <AppIcon name="runner" :size="26" class="empty-state__icon" :stroke="1.4" />
        <p class="empty-state__title">No run yet</p>
        <p class="empty-state__hint">
          Choose a collection and press Run. Every assertion on every request
          is checked, and you get a pass/fail report per iteration.
        </p>
      </div>

      <template v-else>
        <header
          class="summary"
          :class="runner.current.status === 'passed' ? 'summary--ok' : 'summary--bad'"
        >
          <div class="summary__verdict">
            <AppIcon
              :name="runner.current.status === 'passed' ? 'check' : 'close'"
              :size="18"
              :stroke="2.4"
              class="summary__icon"
            />
            <div>
              <p class="summary__title">
                {{ runner.current.status === 'passed' ? 'All checks passed' : 'Some checks failed' }}
              </p>
              <p class="summary__name">{{ runner.current.collection_name }}</p>
            </div>
          </div>

          <dl class="summary__stats">
            <div><dt>Requests</dt><dd>{{ runner.current.total_requests }}</dd></div>
            <div><dt>Iterations</dt><dd>{{ runner.current.iterations }}</dd></div>
            <div><dt>Passed</dt><dd class="ok">{{ runner.current.passed }}</dd></div>
            <div><dt>Failed</dt><dd :class="{ bad: runner.current.failed > 0 }">{{ runner.current.failed }}</dd></div>
            <div><dt>Duration</dt><dd>{{ runner.current.duration_ms.toFixed(0) }} ms</dd></div>
          </dl>
        </header>

        <ul class="iterations">
          <li
            v-for="bucket in iterationSummary"
            :key="bucket.iteration"
            class="iteration"
          >
            <button
              class="iteration__head"
              type="button"
              :aria-expanded="expandedIteration === bucket.iteration"
              @click="expandedIteration = expandedIteration === bucket.iteration ? null : bucket.iteration"
            >
              <AppIcon
                name="chevron"
                :size="12"
                class="iteration__chevron"
                :class="{ 'iteration__chevron--open': expandedIteration === bucket.iteration }"
              />
              <span class="iteration__label">Iteration {{ bucket.iteration }}</span>
              <span class="iteration__bar">
                <span
                  class="iteration__fill"
                  :style="{
                    width: `${(bucket.passed / Math.max(1, bucket.passed + bucket.failed)) * 100}%`,
                  }"
                />
              </span>
              <span class="iteration__score mono">
                {{ bucket.passed }}/{{ bucket.passed + bucket.failed }}
              </span>
              <span class="iteration__time mono">{{ bucket.durationMs.toFixed(0) }} ms</span>
            </button>

            <ul v-if="expandedIteration === bucket.iteration" class="steps">
              <li
                v-for="(step, index) in stepsFor(bucket.iteration)"
                :key="index"
                class="step"
                :class="step.ok ? 'step--ok' : 'step--bad'"
              >
                <MethodBadge :method="step.method" size="sm" />
                <span class="step__name truncate">{{ step.name }}</span>
                <span class="step__status mono">{{ step.status_code ?? 'ERR' }}</span>
                <span class="step__time mono">{{ step.duration_ms.toFixed(0) }} ms</span>

                <ul v-if="step.assertion_results.length" class="step__asserts">
                  <li
                    v-for="(check, i) in step.assertion_results"
                    :key="i"
                    :class="check.passed ? 'ok' : 'bad'"
                  >
                    <AppIcon
                      :name="check.passed ? 'check' : 'close'"
                      :size="11"
                      :stroke="2.4"
                      class="step__assert-icon"
                    />
                    {{ check.source }}
                    <span v-if="check.property" class="mono">{{ check.property }}</span>
                    {{ check.operator.replace(/_/g, ' ') }}
                    <span v-if="check.target" class="mono">{{ check.target }}</span>
                    <span v-if="!check.passed" class="step__msg">— {{ check.message }}</span>
                  </li>
                </ul>

                <p v-if="step.error" class="step__error">{{ step.error }}</p>
              </li>
            </ul>
          </li>
        </ul>
      </template>
    </section>
  </div>
</template>

<style scoped>
.runner { display: flex; flex: 1; min-height: 0; min-width: 0; }

/* --- Controls --- */
.controls {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-4);
  border-right: 1px solid var(--border);
  background: var(--surface);
  overflow-y: auto;
}

.controls__title { font-size: var(--text-lg); font-weight: 650; }
.controls__sub { font-size: var(--text-xs); color: var(--text-muted); margin-top: calc(var(--space-4) * -1 + var(--space-2)); }

.field { display: block; }
.field--check { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-sm); cursor: pointer; }
.field__hint { display: block; font-size: var(--text-xs); color: var(--text-subtle); margin-top: var(--space-1); }

.controls__env { font-size: var(--text-xs); color: var(--text-muted); }
.controls__env strong { color: var(--text); }

.controls__plan { font-size: var(--text-xs); color: var(--text-muted); }
.controls__plan strong { color: var(--accent); font-family: var(--font-mono); }

.controls__run { width: 100%; height: 36px; }
.controls__warn { font-size: var(--text-xs); color: var(--warn); }

.recent { border-top: 1px solid var(--border); padding-top: var(--space-3); }
.recent__head { display: flex; align-items: center; justify-content: space-between; }
.recent__list { display: flex; flex-direction: column; gap: 1px; }

.recent__item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius);
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-align: left;
}
.recent__item:hover { background: var(--surface-hover); color: var(--text); }

.recent__dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.recent__dot--ok  { background: var(--ok); }
.recent__dot--bad { background: var(--danger); }
.recent__score { margin-left: auto; flex-shrink: 0; }

/* --- Results --- */
.results { flex: 1; min-width: 0; padding: var(--space-4); }

.results__center {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--text-muted);
}
.spinner--lg { width: 24px; height: 24px; border-width: 3px; }

.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  flex-wrap: wrap;
  padding: var(--space-4);
  border: 1px solid var(--border);
  border-left: 4px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  margin-bottom: var(--space-4);
}
.summary--ok  { border-left-color: var(--ok); }
.summary--bad { border-left-color: var(--danger); }

.summary__verdict { display: flex; align-items: center; gap: var(--space-3); }

.summary__icon {
  width: 30px; height: 30px;
  padding: 6px;
  border-radius: 50%;
  color: #fff;
}
.summary--ok  .summary__icon { background: var(--ok); }
.summary--bad .summary__icon { background: var(--danger); }

.summary__title { font-weight: 650; }
.summary__name { font-size: var(--text-sm); color: var(--text-muted); }

.summary__stats { display: flex; gap: var(--space-5); flex-wrap: wrap; }
.summary__stats dt { font-size: var(--text-xs); color: var(--text-subtle); text-transform: uppercase; letter-spacing: 0.04em; }
.summary__stats dd { font-family: var(--font-mono); font-size: var(--text-lg); font-weight: 600; }

.ok  { color: var(--ok); }
.bad { color: var(--danger); }

.iterations { display: flex; flex-direction: column; gap: var(--space-2); }

.iteration { border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); overflow: hidden; }

.iteration__head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  text-align: left;
}
.iteration__head:hover { background: var(--surface-hover); }

.iteration__chevron { flex-shrink: 0; color: var(--text-subtle); transition: transform var(--transition); }
.iteration__chevron--open { transform: rotate(90deg); }

.iteration__label { font-size: var(--text-sm); font-weight: 500; min-width: 90px; }

.iteration__bar {
  flex: 1;
  min-width: 60px;
  height: 6px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--danger) 35%, transparent);
  overflow: hidden;
}
.iteration__fill { display: block; height: 100%; background: var(--ok); }

.iteration__score, .iteration__time { font-size: var(--text-xs); color: var(--text-muted); }

.steps { border-top: 1px solid var(--border); }

.step {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: var(--space-2) var(--space-3);
  align-items: center;
  padding: var(--space-3);
  border-bottom: 1px solid var(--border);
  border-left: 3px solid transparent;
}
.step:last-child { border-bottom: none; }
.step--ok  { border-left-color: var(--ok); }
.step--bad { border-left-color: var(--danger); }

.step__name { font-size: var(--text-sm); }
.step__status, .step__time { font-size: var(--text-xs); color: var(--text-muted); }

.step__asserts {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-left: var(--space-5);
  font-size: var(--text-2xs);
}
.step__asserts li { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; }
.step__assert-icon { flex-shrink: 0; }
.step__msg { color: var(--danger); }

.step__error {
  grid-column: 1 / -1;
  font-size: var(--text-xs);
  color: var(--danger);
  font-family: var(--font-mono);
  padding-left: var(--space-5);
}

@media (max-width: 900px) {
  .runner { flex-direction: column; }
  .controls { width: 100%; border-right: none; border-bottom: 1px solid var(--border); }
}
</style>
