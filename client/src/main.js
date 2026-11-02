import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import './styles/tokens.css'
import { initTheme } from './composables/useTheme'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import Inventory from './views/Inventory.vue'
import Orders from './views/Orders.vue'
import Demand from './views/Demand.vue'
import Spending from './views/Spending.vue'
import Reports from './views/Reports.vue'
import Restocking from './views/Restocking.vue'
import Backlog from './views/Backlog.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/inventory', component: Inventory },
    { path: '/orders', component: Orders },
    { path: '/demand', component: Demand },
    { path: '/spending', component: Spending },
    { path: '/reports', component: Reports },

    { path: '/restocking', component: Restocking },
    // Backlog is reached from the profile menu, not the primary sidebar nav
    { path: '/backlog', component: Backlog }
  ]
})

// Apply the stored/system theme before createApp so the first paint is already correct
initTheme()

const app = createApp(App)
app.use(router)
app.mount('#app')
