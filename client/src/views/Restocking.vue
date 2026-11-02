<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget') }}</h3>
        <span class="budget-value">{{ formatCurrency(budget) }}</span>
      </div>
      <input
        v-model.number="budget"
        type="range"
        class="budget-slider"
        :min="BUDGET_MIN"
        :max="BUDGET_MAX"
        :step="BUDGET_STEP"
        :aria-label="t('restocking.budget')"
      />
      <div class="slider-scale">
        <span>{{ formatCurrency(BUDGET_MIN) }}</span>
        <span>{{ formatCurrency(BUDGET_MAX) }}</span>
      </div>
    </div>

    <div v-if="orderSuccess" class="success-message" role="status">{{ orderSuccess }}</div>
    <div v-if="orderError" class="error" role="alert">{{ orderError }}</div>

    <div v-if="loading && !recommendations" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="recommendations">
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.selectedCost') }}</div>
          <div class="stat-value">{{ formatCurrency(selectedTotal) }}</div>
        </div>
        <div :class="['stat-card', remaining < 0 ? 'danger' : 'success']">
          <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div class="stat-value">{{ formatCurrency(remaining) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.leadTime') }}</div>
          <div class="stat-value">{{ t('orders.leadTimeDays', { days: recommendations.lead_time_days }) }}</div>
        </div>
      </div>

      <div :class="['card', { refreshing: loading }]">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ recommendations.items.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="!canSubmit"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>

        <p v-if="remaining < 0" class="over-budget">{{ t('restocking.overBudget') }}</p>

        <div v-if="recommendations.items.length === 0" class="empty">{{ t('restocking.noRecommendations') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th class="col-check"></th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th class="num">{{ t('restocking.table.currentStock') }}</th>
                <th class="num">{{ t('restocking.table.forecastedDemand') }}</th>
                <th class="num">{{ t('restocking.table.recommended') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.total') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations.items" :key="item.sku">
                <td class="col-check">
                  <input
                    v-model="selected[item.sku]"
                    type="checkbox"
                    :aria-label="t('restocking.selectItem', { name: translateProductName(item.name) })"
                    :disabled="submitting"
                  />
                </td>
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td class="num">{{ item.current_stock.toLocaleString() }}</td>
                <td class="num">{{ item.forecasted_demand.toLocaleString() }}</td>
                <td class="num">{{ item.units.toLocaleString() }}</td>
                <td class="num">
                  <input
                    type="number"
                    class="qty-input"
                    min="1"
                    :max="item.units"
                    step="1"
                    :value="quantities[item.sku]"
                    :disabled="submitting"
                    :aria-label="t('restocking.table.quantity')"
                    @input="setQuantity(item, $event.target.value)"
                  />
                </td>
                <td class="num">{{ formatCurrency(item.unit_cost) }}</td>
                <td class="num"><strong>{{ formatCurrency(lineTotal(item)) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

    const BUDGET_MIN = 0
    const BUDGET_MAX = 20000
    const BUDGET_STEP = 100
    const DEBOUNCE_MS = 300

    const budget = ref(5000)
    const recommendations = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const orderSuccess = ref(null)
    const orderError = ref(null)
    const selected = reactive({})
    const quantities = reactive({})

    let debounceTimer = null
    let requestId = 0

    const formatCurrency = (value) => {
      const num = Number(value)
      if (!Number.isFinite(num)) return '-'
      return num.toLocaleString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        style: 'currency',
        currency: currentCurrency.value,
        maximumFractionDigits: 2
      })
    }

    const clampQuantity = (item, raw) => {
      const n = Math.floor(Number(raw))
      if (!Number.isFinite(n) || n < 1) return 1
      return Math.min(n, item.units)
    }

    const setQuantity = (item, raw) => {
      if (raw === '') return
      quantities[item.sku] = clampQuantity(item, raw)
    }

    const lineTotal = (item) => (quantities[item.sku] || 0) * item.unit_cost

    const selectedItems = computed(() => {
      if (!recommendations.value) return []
      return recommendations.value.items.filter(item => selected[item.sku])
    })

    const selectedTotal = computed(() =>
      selectedItems.value.reduce((sum, item) => sum + lineTotal(item), 0)
    )

    const remaining = computed(() => budget.value - selectedTotal.value)

    const canSubmit = computed(() =>
      !submitting.value && !loading.value && selectedItems.value.length > 0 && remaining.value >= 0
    )

    const loadRecommendations = async () => {
      const id = ++requestId
      loading.value = true
      error.value = null
      try {
        const data = await api.getRestockingRecommendations(budget.value)
        if (id !== requestId) return // a newer request superseded this one
        recommendations.value = data
        // Reset selection to the server's recommendation for this budget
        Object.keys(selected).forEach(k => delete selected[k])
        Object.keys(quantities).forEach(k => delete quantities[k])
        data.items.forEach(item => {
          selected[item.sku] = true
          quantities[item.sku] = item.units
        })
      } catch (err) {
        if (id !== requestId) return
        error.value = t('restocking.loadFailed') + ': ' + err.message
        console.error('Restocking load error:', err)
      } finally {
        if (id === requestId) loading.value = false
      }
    }

    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, DEBOUNCE_MS)
    })

    const placeOrder = async () => {
      if (!canSubmit.value) return
      submitting.value = true
      orderSuccess.value = null
      orderError.value = null
      try {
        const payload = selectedItems.value.map(item => ({
          sku: item.sku,
          quantity: quantities[item.sku]
        }))
        const order = await api.createRestockingOrder(payload)
        orderSuccess.value = t('restocking.orderSuccess', {
          orderNumber: order.order_number,
          days: order.lead_time_days
        })
        await loadRecommendations()
      } catch (err) {
        const detail = err.response?.data?.detail
        orderError.value = t('restocking.orderFailed') +
          ': ' + (typeof detail === 'string' ? detail : err.message)
        console.error('Place order error:', err)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)
    onBeforeUnmount(() => clearTimeout(debounceTimer))

    return {
      t,
      BUDGET_MIN,
      BUDGET_MAX,
      BUDGET_STEP,
      budget,
      recommendations,
      loading,
      error,
      submitting,
      orderSuccess,
      orderError,
      selected,
      quantities,
      selectedTotal,
      remaining,
      canSubmit,
      formatCurrency,
      setQuantity,
      lineTotal,
      placeOrder,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.success-message {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-5);
  font-size: 0.938rem;
}

.stat-value {
  font-size: 1.75rem;
}

.refreshing {
  opacity: 0.6;
  transition: opacity 0.15s ease;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  color: #64748b;
  cursor: not-allowed;
}

.over-budget {
  color: #991b1b;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.empty {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-size: 0.938rem;
}

.col-check {
  width: 40px;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.qty-input {
  width: 80px;
  padding: 0.25rem 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.875rem;
  text-align: right;
  color: #334155;
}

.qty-input:focus {
  outline: 2px solid #2563eb;
  outline-offset: -1px;
}

@media (max-width: 640px) {
  .card-header {
    flex-wrap: wrap;
    gap: 0.75rem;
  }
}
</style>
