<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ProfileMenu from './ProfileMenu.vue'
import { useI18n } from '../composables/useI18n'

const props = defineProps({
  open: { type: Boolean, default: false },
  collapsed: { type: Boolean, default: false }
})
const emit = defineEmits(['close', 'toggle-collapse', 'show-profile-details', 'show-tasks'])

const { t } = useI18n()
const sidebarEl = ref(null)

// Inline SVG icon paths (24x24 viewBox, stroke based)
const groups = computed(() => [
  {
    id: 'overview',
    heading: null,
    links: [
      { to: '/', label: t('nav.overview'), icon: 'M3 12l9-8 9 8M5 10v10h5v-6h4v6h5V10' }
    ]
  },
  {
    id: 'operations',
    heading: t('nav.groupOperations'),
    links: [
      { to: '/inventory', label: t('nav.inventory'), icon: 'M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8' },
      { to: '/orders', label: t('nav.orders'), icon: 'M9 5H6a1 1 0 00-1 1v14a1 1 0 001 1h12a1 1 0 001-1V6a1 1 0 00-1-1h-3M9 3h6v4H9zM9 12h6M9 16h6' },
      { to: '/restocking', label: t('nav.restocking'), icon: 'M20 11a8 8 0 00-14.9-3M4 4v4h4M4 13a8 8 0 0014.9 3M20 20v-4h-4' }
    ]
  },
  {
    id: 'planning',
    heading: t('nav.groupPlanning'),
    links: [
      { to: '/demand', label: t('nav.demandForecast'), icon: 'M3 17l6-6 4 4 8-8M15 7h6v6' },
      { to: '/reports', label: t('nav.reports'), icon: 'M6 3h9l4 4v14H6zM14 3v5h5M9 13h6M9 17h6' }
    ]
  },
  {
    id: 'finance',
    heading: t('nav.groupFinance'),
    links: [
      { to: '/spending', label: t('nav.finance'), icon: 'M3 7h18v12H3zM3 11h18M7 15h3' }
    ]
  }
])

const focusableSelector = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
// Skip controls hidden by CSS (for example the rail toggle on phones)
const getFocusable = () =>
  Array.from(sidebarEl.value?.querySelectorAll(focusableSelector) ?? [])
    .filter(el => el.getClientRects().length > 0)

// Move focus into the drawer when it opens
watch(() => props.open, async (isOpen) => {
  if (isOpen) {
    await nextTick()
    getFocusable()[0]?.focus()
  }
})

// Trap focus inside the drawer while it is open (only active when drawer is shown)
const onKeydown = (event) => {
  if (!props.open) return
  if (event.key === 'Escape') {
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const focusable = getFocusable()
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}
</script>

<template>
  <aside
    id="app-sidebar"
    ref="sidebarEl"
    class="sidebar"
    :class="{ 'is-open': open, 'is-collapsed': collapsed }"
    @keydown="onKeydown"
  >
    <div class="sidebar-brand">
      <div class="brand-text">
        <span class="brand-name">{{ t('nav.companyName') }}</span>
        <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
      </div>
      <button
        type="button"
        class="collapse-toggle"
        :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :title="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :aria-expanded="collapsed ? 'false' : 'true'"
        aria-controls="app-sidebar"
        @click="emit('toggle-collapse')"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path v-if="collapsed" d="M6 6l6 6-6 6M13 6l6 6-6 6" />
          <path v-else d="M18 6l-6 6 6 6M11 6l-6 6 6 6" />
        </svg>
      </button>
      <button
        type="button"
        class="drawer-close"
        :aria-label="t('nav.closeMenu')"
        @click="emit('close')"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      </button>
    </div>

    <nav class="sidebar-nav" :aria-label="t('nav.primaryNav')">
      <div v-for="group in groups" :key="group.id" class="nav-group">
        <div v-if="group.heading" class="nav-heading">{{ group.heading }}</div>
        <div v-if="group.heading" class="nav-divider" aria-hidden="true"></div>
        <router-link
          v-for="link in group.links"
          :key="link.to"
          :to="link.to"
          class="nav-link"
          :aria-label="link.label"
          :title="collapsed ? link.label : null"
          active-class=""
          exact-active-class="active"
          @click="emit('close')"
        >
          <svg class="nav-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path :d="link.icon" />
          </svg>
          <span class="nav-label">{{ link.label }}</span>
        </router-link>
      </div>
    </nav>

    <div class="sidebar-footer">
      <LanguageSwitcher />
      <ProfileMenu
        @show-profile-details="emit('show-profile-details')"
        @show-tasks="emit('show-tasks')"
      />
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  width: 100%;
  height: 100vh;
  position: sticky;
  top: 0;
  z-index: 120;
  display: flex;
  flex-direction: column;
  padding: var(--space-4) var(--space-3);
  gap: var(--space-4);
}

.sidebar-brand {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.brand-name {
  color: var(--sidebar-text-strong);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.brand-subtitle {
  color: var(--sidebar-muted);
  font-size: 12px;
}

.collapse-toggle,
.drawer-close {
  display: none;
  background: none;
  border: 0;
  color: var(--sidebar-text);
  padding: var(--space-1);
  border-radius: var(--radius-md);
  cursor: pointer;
}

.sidebar-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-heading {
  color: var(--sidebar-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0 var(--space-3) var(--space-2);
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  color: var(--sidebar-text);
  font-size: var(--font-size-base);
  font-weight: 500;
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-link:hover {
  background: var(--sidebar-hover);
  color: var(--sidebar-text-strong);
}

.nav-link.active {
  background: var(--sidebar-active-bg);
  color: var(--sidebar-text-strong);
}

.nav-link.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--sidebar-accent);
}

.nav-link:focus-visible,
.collapse-toggle:focus-visible,
.drawer-close:focus-visible {
  outline: 2px solid var(--sidebar-accent);
  outline-offset: 2px;
}

.nav-divider {
  display: none;
  height: 1px;
  margin: var(--space-1) var(--space-3);
  background: var(--sidebar-border);
}

.collapse-toggle:hover {
  background: var(--sidebar-hover);
  color: var(--sidebar-text-strong);
}

.nav-icon {
  flex-shrink: 0;
}

.nav-label {
  min-width: 0;
  overflow-wrap: anywhere;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-4);
  border-top: 1px solid var(--sidebar-border);
}

/* Restyle relocated controls for the dark surface; menus open upward */
.sidebar-footer :deep(.language-button),
.sidebar-footer :deep(.profile-button) {
  width: 100%;
  background: var(--sidebar-hover);
  border-color: var(--sidebar-border);
  color: var(--sidebar-text);
  padding: var(--space-2) var(--space-3);
}

.sidebar-footer :deep(.language-button:hover),
.sidebar-footer :deep(.profile-button:hover) {
  background: #273449;
  border-color: #334155;
}

.sidebar-footer :deep(.language-button:focus-visible),
.sidebar-footer :deep(.profile-button:focus-visible) {
  outline: 2px solid var(--sidebar-accent);
  outline-offset: 2px;
}

.sidebar-footer :deep(.globe-icon),
.sidebar-footer :deep(.chevron) {
  color: var(--sidebar-muted);
}

.sidebar-footer :deep(.chevron) {
  margin-left: auto;
}

.sidebar-footer :deep(.profile-name) {
  color: var(--sidebar-text-strong);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer :deep(.dropdown-menu) {
  top: auto;
  bottom: calc(100% + var(--space-2));
  left: 0;
  right: 0;
  min-width: 0;
}

/* Desktop and tablet: collapsible icon rail */
@media (min-width: 768px) {
  .collapse-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    background: none;
    border: 0;
    border-radius: var(--radius-md);
    color: var(--sidebar-text);
    cursor: pointer;
  }

  .sidebar {
    transition: padding 0.2s ease;
  }

  .nav-link {
    white-space: nowrap;
  }

  .is-collapsed .sidebar-brand {
    justify-content: center;
    padding: var(--space-2) 0;
  }

  .is-collapsed .brand-text,
  .is-collapsed .nav-heading,
  .is-collapsed .nav-label {
    display: none;
  }

  .is-collapsed .nav-divider {
    display: block;
  }

  .is-collapsed .nav-group:first-child .nav-divider {
    display: none;
  }

  .is-collapsed .nav-link {
    justify-content: center;
    padding: var(--space-3) 0;
  }

  .is-collapsed .nav-group {
    gap: var(--space-1);
  }

  .is-collapsed .sidebar-nav {
    gap: var(--space-2);
  }

  /* Footer controls become icon-only; menus fly out to the right */
  .is-collapsed .sidebar-footer :deep(.language-label),
  .is-collapsed .sidebar-footer :deep(.chevron),
  .is-collapsed .sidebar-footer :deep(.profile-name) {
    display: none;
  }

  .is-collapsed .sidebar-footer :deep(.language-button),
  .is-collapsed .sidebar-footer :deep(.profile-button) {
    justify-content: center;
    padding: var(--space-2) 0;
  }

  .is-collapsed .sidebar-footer :deep(.dropdown-menu) {
    left: calc(100% + var(--space-4));
    right: auto;
    bottom: 0;
    width: 220px;
  }
}

@media (max-width: 767px) {
  .sidebar {
    width: var(--sidebar-width);
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 200;
    max-width: 85vw;
    transform: translateX(-100%);
    visibility: hidden;
    transition: transform 0.2s ease, visibility 0s linear 0.2s;
  }

  .sidebar.is-open {
    transform: translateX(0);
    visibility: visible;
    transition: transform 0.2s ease, visibility 0s;
  }

  .drawer-close {
    display: inline-flex;
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .sidebar.is-open {
    transition: none;
  }
}
</style>
