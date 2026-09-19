/**
 * 主题 composable：页面只通过这里读写主题
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { THEME_STORAGE_KEY, type ThemeMode } from './constants'
import {
  applyTheme,
  bootstrapTheme,
  persistTheme,
  resolveTheme,
  readStoredTheme,
} from './applyTheme'

const theme = ref<ThemeMode>('light')
let bootstrapped = false

function ensureBoot() {
  if (!bootstrapped) {
    theme.value = bootstrapTheme()
    bootstrapped = true
  }
}

export function useTheme() {
  ensureBoot()

  const isDark = computed(() => theme.value === 'dark')
  const label = computed(() => (theme.value === 'dark' ? '暗色' : '亮色'))

  function setTheme(mode: ThemeMode) {
    theme.value = mode
    applyTheme(mode)
    persistTheme(mode)
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  let mq: MediaQueryList | null = null
  function onSystemChange() {
    // 用户已手动选择则不跟随系统
    if (readStoredTheme()) return
    const next = resolveTheme(null)
    theme.value = next
    applyTheme(next)
  }

  onMounted(() => {
    mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', onSystemChange)
  })
  onUnmounted(() => {
    mq?.removeEventListener('change', onSystemChange)
  })

  return { theme, isDark, label, setTheme, toggleTheme, storageKey: THEME_STORAGE_KEY }
}
