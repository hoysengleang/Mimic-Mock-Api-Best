<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

import AppHeader from '@/components/layout/AppHeader.vue'
import ToastHost from '@/components/common/ToastHost.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useEnvironmentsStore } from '@/stores/environments'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const collections = useCollectionsStore()
const environments = useEnvironmentsStore()

onMounted(async () => {
  ui.applyTheme()
  // Both are needed by nearly every screen, so load them once up front.
  await Promise.all([collections.load(), environments.load()])
})
</script>

<template>
  <div class="app">
    <AppHeader />
    <main class="app__main">
      <RouterView v-slot="{ Component }">
        <component :is="Component" />
      </RouterView>
    </main>
    <ToastHost />
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.app__main {
  flex: 1;
  min-height: 0;
  display: flex;
}
</style>
