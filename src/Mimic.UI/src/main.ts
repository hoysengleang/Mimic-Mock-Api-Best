import { createPinia } from 'pinia'
import { createApp } from 'vue'

// Self-hosted so the app works offline and needs no third-party CDN.
import '@fontsource-variable/inter'
import '@fontsource-variable/jetbrains-mono'

import App from '@/App.vue'
import router from '@/router'
import '@/styles/main.css'

createApp(App).use(createPinia()).use(router).mount('#app')
