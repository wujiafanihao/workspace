/**
 * 将主题落到 <html data-theme>；唯一写 DOM 主题属性的出口
 */
import { THEME_STORAGE_KEY, type ThemeMode, isThemeMode } from './constants'

export function readStoredTheme(): ThemeMode | null {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY)
    return isThemeMode(raw) ? raw : null
  } catch {
    return null
  }
}

export function systemPrefersDark(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  )
}

/** 解析当前应使用的主题：存储优先，否则跟随系统 */
export function resolveTheme(explicit?: ThemeMode | null): ThemeMode {
  if (explicit && isThemeMode(explicit)) return explicit
  return readStoredTheme() ?? (systemPrefersDark() ? 'dark' : 'light')
}

export function applyTheme(mode: ThemeMode): void {
  const root = document.documentElement
  root.setAttribute('data-theme', mode)
  root.style.colorScheme = mode
}

export function persistTheme(mode: ThemeMode): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, mode)
  } catch {
    /* ignore quota / private mode */
  }
}

/** 启动时同步应用，减少闪屏 */
export function bootstrapTheme(): ThemeMode {
  const mode = resolveTheme()
  applyTheme(mode)
  return mode
}
