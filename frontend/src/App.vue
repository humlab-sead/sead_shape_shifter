<template>
  <v-app>
    <v-navigation-drawer 
      v-model="drawer" 
      app 
      :rail="rail" 
      :width="sidebarWidth"
      @click="rail = false"
    >
      <!-- Resize Handle -->
      <div 
        v-if="!rail"
        class="resize-handle"
        @mousedown="startResize"
      />
      
      <v-list-item :title="rail ? '' : 'SEAD Shape Shifter'" :subtitle="rail ? '' : 'Project Editor'" nav>
        <!-- <template #prepend>
          <div class="d-flex align-center justify-center" :style="{ width: rail ? '40px' : '48px', height: '48px' }">
            <v-img 
              src="/src/assets/images/sead-logo.svg" 
              alt="SEAD Logo" 
              :width="rail ? 32 : 40"
              :height="rail ? 32 : 40"
              contain
            />
          </div>
        </template> -->
        <template #append>
          <v-btn v-if="!rail" icon="mdi-chevron-left" variant="text" size="small" @click.stop="rail = true" />
        </template>
      </v-list-item>

      <v-divider />

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-home" title="Home" value="home" :to="{ name: 'home' }" />

        <v-list-item
          prepend-icon="mdi-file-document-multiple"
          title="Projects"
          value="projects"
          :to="{ name: 'projects' }"
        />

        <v-list-item
          prepend-icon="mdi-database"
          title="Data Sources"
          value="data-sources"
          :to="{ name: 'data-sources' }"
        />

        <v-list-item
          prepend-icon="mdi-database-search"
          title="Schema Explorer"
          value="schema-explorer"
          :to="{ name: 'schema-explorer' }"
        />

        <v-list-item
          prepend-icon="mdi-code-braces"
          title="Query Tester"
          value="query-tester"
          :to="{ name: 'query-tester' }"
        />
      </v-list>

      <!-- Context-Sensitive Help -->
      <context-help :rail="rail" />

      <template #append>
        <v-divider />
        <v-list density="compact" nav>
          <v-list-item prepend-icon="mdi-cog" title="Settings" value="settings" :to="{ name: 'settings' }" />

          <v-list-item prepend-icon="mdi-help-circle" title="Help" value="help" :to="{ name: 'help' }" />
        </v-list>
      </template>
    </v-navigation-drawer>

    <v-app-bar app color="primary" density="compact">
      <v-app-bar-nav-icon @click="drawer = !drawer" />

      <v-toolbar-title class="d-flex align-center">

        <span class="font-weight-bold">SEAD Shape Shifter</span>
        <span v-if="currentProject" class="ml-2 text-caption"> / {{ currentProject }} </span>
      </v-toolbar-title>
        
      <v-spacer />

      <v-btn
        :icon="theme.isDark.value ? 'mdi-white-balance-sunny' : 'mdi-moon-waning-crescent'"
        variant="text"
        @click="theme.toggleDarkMode()"
      />

      <v-btn icon="mdi-magnify" variant="text" @click="showCommandPalette = true" />

      <v-menu>
        <template #activator="{ props }">
          <v-btn icon="mdi-dots-vertical" variant="text" v-bind="props" />
        </template>
        <v-list>
          <v-list-item @click="handleNewProject">
            <v-list-item-title>
              <v-icon icon="mdi-plus" class="mr-2" />
              New Project
            </v-list-item-title>
          </v-list-item>
          <v-list-item @click="handleRefresh">
            <v-list-item-title>
              <v-icon icon="mdi-refresh" class="mr-2" />
              Refresh
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-breadcrumbs v-if="breadcrumbs.length > 0" :items="breadcrumbs" class="px-4 py-2">
        <template #divider>
          <v-icon icon="mdi-chevron-right" />
        </template>
      </v-breadcrumbs>

      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </v-main>

    <v-dialog v-model="showCommandPalette" max-width="600">
      <v-card>
        <v-card-title>Quick Actions</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="commandSearch"
            placeholder="Search commands..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            autofocus
            hide-details
          />
          <v-list class="mt-2">
            <v-list-item v-for="cmd in filteredCommands" :key="cmd.id" @click="executeCommand(cmd)">
              <template #prepend>
                <v-icon :icon="cmd.icon" />
              </template>
              <v-list-item-title>{{ cmd.title }}</v-list-item-title>
              <template #append>
                <v-chip size="small" variant="outlined">
                  {{ cmd.shortcut }}
                </v-chip>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showHelpDialog" max-width="600">
      <v-card>
        <v-card-title>Keyboard Shortcuts</v-card-title>
        <v-card-text>
          <v-list>
            <v-list-item>
              <template #prepend>
                <v-chip size="small">Ctrl+K</v-chip>
              </template>
              <v-list-item-title>Open Command Palette</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-chip size="small">Ctrl+H</v-chip>
              </template>
              <v-list-item-title>Go to Home</v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-chip size="small">Esc</v-chip>
              </template>
              <v-list-item-title>Close Dialog</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showHelpDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">Close</v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import { useSettings } from '@/composables/useSettings'
import { useNotification } from '@/composables/useNotification'
import ContextHelp from '@/components/ContextHelp.vue'

const router = useRouter()
const route = useRoute()
const theme = useTheme()
const settings = useSettings()
const { snackbar } = useNotification()

const drawer = ref(true)
const rail = ref(false)
const sidebarWidth = ref(280) // Default width
const isResizing = ref(false)
const showCommandPalette = ref(false)
const showHelpDialog = ref(false)
const commandSearch = ref('')

const currentProject = computed(() => route.params.name as string | undefined)

interface Breadcrumb {
  title: string
  disabled?: boolean
  href?: string
}

const breadcrumbs = computed<Breadcrumb[]>(() => {
  const crumbs: Breadcrumb[] = []

  if (route.name === 'home') return []

  crumbs.push({ title: 'Home', href: '/' })

  if (route.name === 'projects') {
    crumbs.push({ title: 'Projects', disabled: true })
  } else if (route.name === 'project-detail' && route.params.name) {
    crumbs.push({ title: 'Projects', href: '/projects' })
    crumbs.push({ title: String(route.params.name), disabled: true })
  } else if (route.name === 'graph') {
    crumbs.push({ title: 'Dependency Graph', disabled: true })
  } else if (route.name === 'entities') {
    crumbs.push({ title: 'Entities', disabled: true })
  } else if (route.name === 'validation') {
    crumbs.push({ title: 'Validation', disabled: true })
  } else if (route.name === 'settings') {
    crumbs.push({ title: 'Settings', disabled: true })
  }

  return crumbs
})

interface Command {
  id: string
  title: string
  icon: string
  shortcut: string
  action: () => void
}

const commands = ref<Command[]>([
  {
    id: 'goto-home',
    title: 'Go to Home',
    icon: 'mdi-home',
    shortcut: 'Ctrl+H',
    action: () => router.push('/'),
  },
  {
    id: 'goto-projects',
    title: 'Go to Projects',
    icon: 'mdi-file-document-multiple',
    shortcut: 'Ctrl+Shift+C',
    action: () => router.push('/projects'),
  },
])

const filteredCommands = computed(() => {
  if (!commandSearch.value) return commands.value
  const search = commandSearch.value.toLowerCase()
  return commands.value.filter((cmd) => cmd.title.toLowerCase().includes(search))
})

function executeCommand(cmd: Command) {
  showCommandPalette.value = false
  commandSearch.value = ''
  cmd.action()
}

function handleNewProject() {
  router.push('/projects')
}

function handleRefresh() {
  window.location.reload()
}

// Sidebar resize functionality
function startResize(e: MouseEvent) {
  e.preventDefault()
  isResizing.value = true
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
}

function handleResize(e: MouseEvent) {
  if (!isResizing.value) return
  
  const newWidth = e.clientX
  // Constrain between 240px and 500px
  if (newWidth >= 240 && newWidth <= 500) {
    sidebarWidth.value = newWidth
  }
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  
  // Save to localStorage
  localStorage.setItem('sidebarWidth', sidebarWidth.value.toString())
}

function handleKeydown(event: KeyboardEvent) {
  if (event.ctrlKey && event.key === 'k') {
    event.preventDefault()
    showCommandPalette.value = !showCommandPalette.value
  }

  if (event.ctrlKey && event.key === 'h') {
    event.preventDefault()
    router.push('/')
  }

  if (event.ctrlKey && event.shiftKey && event.key === 'C') {
    event.preventDefault()
    router.push('/projects')
  }

  if (event.key === 'Escape') {
    showCommandPalette.value = false
    showHelpDialog.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  
  // Load saved sidebar width
  const savedWidth = localStorage.getItem('sidebarWidth')
  if (savedWidth) {
    const width = parseInt(savedWidth, 10)
    if (width >= 240 && width <= 500) {
      sidebarWidth.value = width
    }
  }
  
  if (window.innerWidth > 1280) {
    drawer.value = true
    rail.value = settings.railNavigation.value
  } else {
    drawer.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

// Watch for rail navigation setting changes
watch(
  () => settings.railNavigation.value,
  (newVal) => {
    if (window.innerWidth > 1280) {
      rail.value = newVal
    }
  }
)
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  width: 4px;
  height: 100%;
  cursor: ew-resize;
  background: transparent;
  z-index: 1000;
  transition: background-color 0.2s;
}

.resize-handle:hover {
  background-color: rgba(var(--v-theme-primary), 0.3);
}

.resize-handle:active {
  background-color: rgba(var(--v-theme-primary), 0.5);
}
</style>
