<template>
  <div class="backlog">
    <div class="page-header">
      <h2>{{ t('backlog.title') }}</h2>
      <p>{{ t('backlog.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('backlog.loading') }}</div>
    <div v-else-if="errorKey" class="error">{{ t(errorKey) }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card danger">
          <div class="stat-label">{{ t('backlog.stats.highPriority') }}</div>
          <div class="stat-value">{{ getBacklogByPriority('high').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('backlog.stats.mediumPriority') }}</div>
          <div class="stat-value">{{ getBacklogByPriority('medium').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('backlog.stats.lowPriority') }}</div>
          <div class="stat-value">{{ getBacklogByPriority('low').length }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('backlog.stats.totalItems') }}</div>
          <div class="stat-value">{{ backlogItems.length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('backlog.itemsTitle') }}</h3>
        </div>
        <div v-if="allBacklogItems.length === 0" style="padding: 3rem; text-align: center;">
          <p style="font-size: 1.125rem; color: #10b981; font-weight: 600;">
            ✓ {{ t('dashboard.inventoryShortages.noShortages') }}
          </p>
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('dashboard.inventoryShortages.orderId') }}</th>
                <th>{{ t('backlog.table.sku') }}</th>
                <th>{{ t('dashboard.inventoryShortages.itemName') }}</th>
                <th>{{ t('dashboard.inventoryShortages.quantityNeeded') }}</th>
                <th>{{ t('dashboard.inventoryShortages.quantityAvailable') }}</th>
                <th>{{ t('dashboard.inventoryShortages.shortage') }}</th>
                <th>{{ t('dashboard.inventoryShortages.daysDelayed') }}</th>
                <th>{{ t('dashboard.inventoryShortages.priority') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="backlogItems.length === 0">
                <td colspan="8" style="text-align: center; padding: 2rem; color: #64748b;">
                  {{ t('backlog.noMatches') }}
                </td>
              </tr>
              <tr v-for="item in backlogItems" :key="item.id">
                <td><strong>{{ item.order_id }}</strong></td>
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.quantity_needed }}</td>
                <td>{{ item.quantity_available }}</td>
                <td>
                  <span class="badge danger">
                    {{ item.quantity_needed - item.quantity_available }} {{ t('dashboard.inventoryShortages.unitsShort') }}
                  </span>
                </td>
                <td>
                  <span :style="{ color: item.days_delayed > 7 ? '#ef4444' : '#f59e0b' }">
                    {{ item.days_delayed === 1 ? t('backlog.dayOne', { count: 1 }) : t('backlog.daysCount', { count: item.days_delayed }) }}
                  </span>
                </td>
                <td>
                  <span :class="['badge', item.priority]">
                    {{ t('priority.' + item.priority) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Backlog',
  setup() {
    const { t } = useI18n()
    const loading = ref(true)
    // Store the key (not the translated text) so the message follows locale switches
    const errorKey = ref(null)
    const allBacklogItems = ref([])
    const inventoryItems = ref([])

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    // Filter backlog based on inventory filters
    const backlogItems = computed(() => {
      if (selectedLocation.value === 'all' && selectedCategory.value === 'all') {
        return allBacklogItems.value
      }

      // Get SKUs of items that match the filters
      const validSkus = new Set(inventoryItems.value.map(item => item.sku))
      return allBacklogItems.value.filter(b => validSkus.has(b.item_sku))
    })

    // Guard against out-of-order responses: only the latest request may update state
    let latestRequestId = 0

    const loadBacklog = async () => {
      const requestId = ++latestRequestId
      try {
        loading.value = true
        errorKey.value = null
        const filters = getCurrentFilters()

        const [backlogData, inventoryData] = await Promise.all([
          api.getBacklog(),
          api.getInventory({
            warehouse: filters.warehouse,
            category: filters.category
          })
        ])

        if (requestId !== latestRequestId) return
        allBacklogItems.value = backlogData
        inventoryItems.value = inventoryData
      } catch (err) {
        if (requestId !== latestRequestId) return
        // Store a key instead of raw err.message so the error follows the active locale
        errorKey.value = 'backlog.loadError'
      } finally {
        if (requestId === latestRequestId) loading.value = false
      }
    }

    const getBacklogByPriority = (priority) => {
      return backlogItems.value.filter(item => item.priority === priority)
    }

    // Watch for filter changes and reload data
    // Period and status are included for consistency with the other pages
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadBacklog()
    })

    onMounted(loadBacklog)

    return {
      t,
      loading,
      errorKey,
      allBacklogItems,
      backlogItems,
      getBacklogByPriority
    }
  }
}
</script>
