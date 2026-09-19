/**
 * 数据模式开关：mock | api
 * 由 VITE_DATA_MODE 控制，阶段一默认 mock。
 */
export type DataMode = 'mock' | 'api'

export function getDataMode(): DataMode {
  const raw = (import.meta.env.VITE_DATA_MODE as string | undefined)?.toLowerCase()
  return raw === 'api' ? 'api' : 'mock'
}

export function isMockMode(): boolean {
  return getDataMode() === 'mock'
}

export function getApiBase(): string {
  return (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? ''
}
