<script setup lang="ts">
/**
 * 亮/暗主题切换；只依赖 useTheme，不散落色值
 */
import { useTheme } from '../theme'

const { theme, isDark, toggleTheme } = useTheme()
</script>

<template>
  <button
    type="button"
    class="theme-toggle"
    :aria-pressed="isDark"
    :aria-label="isDark ? '切换到亮色主题' : '切换到暗色主题'"
    :title="isDark ? '当前暗色，点击切亮色' : '当前亮色，点击切暗色'"
    @click="toggleTheme"
  >
    <span class="theme-toggle__glyph" aria-hidden="true">{{ isDark ? '月' : '日' }}</span>
    <span class="theme-toggle__text">{{ theme === 'dark' ? '暗色' : '亮色' }}</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--fg);
  padding: 0.35rem 0.65rem;
  cursor: pointer;
  font-family: var(--font-display);
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  border-radius: var(--radius);
}
.theme-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.theme-toggle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  box-shadow: 0 0 0 3px var(--focus-ring);
}
.theme-toggle__glyph {
  font-weight: 700;
}
</style>
