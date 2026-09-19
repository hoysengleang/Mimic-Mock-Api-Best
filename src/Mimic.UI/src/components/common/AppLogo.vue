<script setup lang="ts">
/**
 * The Mimic wordmark.
 *
 * The mark is the idea of the product drawn literally: a solid chevron with
 * two fading repeats behind it — a signal and the copies that imitate it.
 * Read left to right it is also a request going out and its echo returning.
 *
 * The wordmark is set in the same monospace as the rest of the data in the
 * app, lowercase and tightly tracked, with the second `i` picked out in the
 * accent. One deliberate detail is worth more than a decorative typeface.
 */
withDefaults(defineProps<{ size?: number; showWord?: boolean }>(), {
  size: 26,
  showWord: true,
})
</script>

<template>
  <span class="logo">
    <svg
      class="logo__mark"
      :width="size"
      :height="size"
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="Mimic"
    >
      <rect width="32" height="32" rx="9" class="logo__tile" />

      <!-- The echoes, furthest and faintest first. -->
      <path
        d="M9 10.5 13.5 16 9 21.5"
        class="logo__echo logo__echo--far"
        stroke-width="2.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <path
        d="M14 10.5 18.5 16 14 21.5"
        class="logo__echo logo__echo--near"
        stroke-width="2.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <!-- The original. -->
      <path
        d="M19 10.5 23.5 16 19 21.5"
        class="logo__signal"
        stroke-width="2.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>

    <span v-if="showWord" class="logo__word">
      mim<span class="logo__i">i</span>c
    </span>
  </span>
</template>

<style scoped>
.logo {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.logo__mark { flex-shrink: 0; }

.logo__tile { fill: var(--logo-tile); }

.logo__signal { stroke: var(--logo-signal); }
.logo__echo   { stroke: var(--logo-signal); }
.logo__echo--near { opacity: 0.45; }
.logo__echo--far  { opacity: 0.2; }

.logo__word {
  font-family: var(--font-mono);
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: -0.045em;
  color: var(--text);
  /* Monospace advances leave a gap after the mark; pull it back optically. */
  margin-left: -1px;
}

/* The one flourish: the second i picked out in the accent. Colouring the
   whole letter rather than overlaying a dot avoids fighting the glyph the
   font already draws. */
.logo__i { color: var(--accent); }
</style>
