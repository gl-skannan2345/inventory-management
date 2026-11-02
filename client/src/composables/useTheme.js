import { ref } from 'vue'

const STORAGE_KEY = 'app-theme'

// Storage can be blocked (privacy mode, sandboxed iframes), so every access is guarded.
const readStored = () => {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === 'light' || v === 'dark' ? v : null
  } catch (err) {
    return null
  }
}

const systemTheme = () =>
  window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'

// Saved choice wins; otherwise follow the OS preference.
const resolveTheme = () => readStored() || systemTheme()

const apply = (value) => {
  document.documentElement.setAttribute('data-theme', value)
}

// Module-level so every component shares one reactive value.
const theme = ref(resolveTheme())
apply(theme.value)

// Called from main.js before createApp so the attribute is set before first paint,
// avoiding a flash of the light theme for dark users. Doing it in JS (not an inline
// index.html script) keeps resolution logic in one place; the module runs before mount
// and the stylesheet-driven paint happens after the entry module executes.
export function initTheme() {
  theme.value = resolveTheme()
  apply(theme.value)
}

export function useTheme() {
  const setTheme = (value) => {
    theme.value = value
    apply(value)
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch (err) {
      // storage blocked: choice applies for this session only
    }
  }
  const toggleTheme = () => setTheme(theme.value === 'dark' ? 'light' : 'dark')
  return { theme, setTheme, toggleTheme }
}
