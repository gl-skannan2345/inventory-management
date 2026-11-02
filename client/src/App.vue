<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <header class="mobile-bar">
      <button
        ref="menuButton"
        type="button"
        class="menu-button"
        :aria-label="t('nav.openMenu')"
        aria-controls="app-sidebar"
        :aria-expanded="drawerOpen ? 'true' : 'false'"
        @click="drawerOpen = true"
      >
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>
      <span class="mobile-title">{{ t('nav.companyName') }}</span>
    </header>

    <div
      v-if="drawerOpen"
      class="drawer-backdrop"
      aria-hidden="true"
      @click="closeDrawer"
    ></div>

    <AppSidebar
      :open="drawerOpen"
      :collapsed="sidebarCollapsed"
      @close="closeDrawer"
      @toggle-collapse="toggleSidebar"
      @show-profile-details="showProfileDetails = true"
      @show-tasks="showTasks = true"
    />

    <div class="app-main">
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import AppSidebar from './components/AppSidebar.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileDetailsModal,
    TasksModal,
    AppSidebar
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])
    const route = useRoute()
    const drawerOpen = ref(false)
    const menuButton = ref(null)

    // Rail state: default collapsed below 768px, expanded above; persisted choice wins.
    // On phones the sidebar is always the full-width drawer, so the rail applies from 768px up.
    const STORAGE_KEY = 'sidebar-collapsed'
    const readCollapsed = () => {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored === 'true') return true
        if (stored === 'false') return false
      } catch (err) {
        // storage unavailable, fall through to default
      }
      return window.matchMedia('(max-width: 767px)').matches
    }
    const sidebarCollapsed = ref(readCollapsed())
    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
      try {
        localStorage.setItem(STORAGE_KEY, String(sidebarCollapsed.value))
      } catch (err) {
        // storage unavailable, keep in-memory state only
      }
    }

    const closeDrawer = () => {
      if (!drawerOpen.value) return
      drawerOpen.value = false
      nextTick(() => menuButton.value?.focus())
    }

    const onEscape = (event) => {
      if (event.key === 'Escape') closeDrawer()
    }

    // Close the drawer if the viewport grows past the mobile breakpoint
    const desktopQuery = window.matchMedia('(min-width: 768px)')
    const onBreakpoint = (event) => {
      if (event.matches) drawerOpen.value = false
    }

    watch(() => route.fullPath, () => {
      drawerOpen.value = false
    })

    onMounted(() => {
      document.addEventListener('keydown', onEscape)
      desktopQuery.addEventListener('change', onBreakpoint)
    })
    onBeforeUnmount(() => {
      document.removeEventListener('keydown', onEscape)
      desktopQuery.removeEventListener('change', onBreakpoint)
    })

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      drawerOpen,
      sidebarCollapsed,
      toggleSidebar,
      menuButton,
      closeDrawer,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--color-bg);
  color: var(--color-text-body);
  font-size: var(--font-size-base);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-shell {
  --sidebar-current: var(--sidebar-width);
  display: grid;
  grid-template-columns: var(--sidebar-current) minmax(0, 1fr);
  min-height: 100vh;
  transition: grid-template-columns 0.2s ease;
}

.app-shell.sidebar-collapsed {
  --sidebar-current: var(--sidebar-width-collapsed);
}

@media (prefers-reduced-motion: reduce) {
  .app-shell {
    transition: none;
  }
}

.app-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.mobile-bar {
  display: none;
}

.drawer-backdrop {
  display: none;
}

.main-content {
  flex: 1;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8);
}

@media (max-width: 767px) {
  .app-shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .mobile-bar {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    height: 56px;
    padding: 0 var(--space-4);
    background: var(--sidebar-bg);
    color: var(--sidebar-text-strong);
    position: sticky;
    top: 0;
    z-index: 100;
  }

  .menu-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    margin-left: calc(var(--space-2) * -1);
    background: none;
    border: 0;
    border-radius: var(--radius-md);
    color: inherit;
    cursor: pointer;
  }

  .menu-button:focus-visible {
    outline: 2px solid var(--sidebar-accent);
    outline-offset: 2px;
  }

  .mobile-title {
    font-size: 16px;
    font-weight: 700;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .drawer-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.5);
    z-index: 150;
  }

  .main-content {
    padding: var(--space-4);
  }
}

.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-1);
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--color-text-muted);
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: var(--color-success);
}

.stat-card.danger .stat-value {
  color: var(--color-danger);
}

.stat-card.info .stat-value {
  color: var(--color-info);
}

.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  margin-bottom: var(--space-5);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-surface-muted);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid var(--color-border-subtle);
  color: var(--color-text-cell);
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--color-surface-muted);
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

@media (max-width: 767px) {
  .card,
  .stat-card {
    padding: var(--space-4);
  }

  .stat-value {
    font-size: 1.75rem;
  }
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-muted);
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
