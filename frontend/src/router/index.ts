import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: {
      title: 'Home',
    },
  },
  {
    path: '/configurations',
    name: 'configurations',
    component: () => import('@/views/ConfigurationsView.vue'),
    meta: {
      title: 'Configurations',
    },
  },
  {
    path: '/configurations/:name',
    name: 'config-detail',
    component: () => import('@/views/ConfigurationDetailView.vue'),
    meta: {
      title: 'Configuration Details',
    },
  },
  {
    path: '/data-sources',
    name: 'data-sources',
    component: () => import('@/views/DataSourcesView.vue'),
    meta: {
      title: 'Data Sources',
    },
  },
  {
    path: '/schema-explorer',
    name: 'schema-explorer',
    component: () => import('@/views/SchemaExplorerView.vue'),
    meta: {
      title: 'Schema Explorer',
    },
  },
  {
    path: '/query-tester',
    name: 'query-tester',
    component: () => import('@/views/QueryTesterView.vue'),
    meta: {
      title: 'Query Tester',
    },
  },
  {
    path: '/entities',
    name: 'entities',
    component: () => import('@/views/EntitiesView.vue'),
    meta: {
      title: 'Entities',
    },
  },
  {
    path: '/graph',
    name: 'graph',
    component: () => import('@/views/DependencyGraphView.vue'),
    meta: {
      title: 'Dependency Graph',
    },
  },
  {
    path: '/validation',
    name: 'validation',
    component: () => import('@/views/ValidationView.vue'),
    meta: {
      title: 'Validation',
    },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: {
      title: 'Settings',
    },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// Update document title on route change
router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - Shape Shifter` : 'Shape Shifter Configuration Editor'
})

export default router
