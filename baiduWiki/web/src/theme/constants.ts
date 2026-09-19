/**
 * 主题常量集中处（业务文件禁止再散落 storage key / 模式字面量）
 */
export const THEME_STORAGE_KEY = 'baiduwiki-theme' as const

export const THEME_MODES = ['light', 'dark'] as const

export type ThemeMode = (typeof THEME_MODES)[number]

export function isThemeMode(value: unknown): value is ThemeMode {
  return value === 'light' || value === 'dark'
}
