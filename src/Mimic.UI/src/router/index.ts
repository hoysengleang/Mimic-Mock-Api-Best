import { createRouter, createWebHistory } from 'vue-router'

/**
 * Every screen except the workspace is lazily loaded — the workspace is what
 * people land on, so it belongs in the initial bundle; the rest should not
 * delay first paint.
 */
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'workspace',
      component: () => import('@/views/WorkspaceView.vue'),
    },
    {
      path: '/mocks',
      name: 'mocks',
      component: () => import('@/views/MocksView.vue'),
    },
    {
      path: '/runner',
      name: 'runner',
      component: () => import('@/views/RunnerView.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
    },
    {
      path: '/environments',
      name: 'environments',
      component: () => import('@/views/EnvironmentsView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

export default router
