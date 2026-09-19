/**
 * 首页聚合数据：mock 或 GET /api/home
 */
import { getApiBase, isMockMode } from './mode'
import homeMock from '../mock/home.json'

export interface StatisticItem {
  label: string
  value: string
  unit?: string
}

export interface HotLemma {
  lemma_id: string
  title: string
  heat?: number
}

export interface DynamicItem {
  id: string
  title: string
  summary: string
  time: string
  type?: string
}

export interface HistoryEvent {
  id: string
  year: number
  title: string
  summary: string
}

export interface ModuleBlockItem {
  lemma_id: string
  title: string
  summary: string
}

export interface ModuleBlock {
  id: string
  title: string
  items: ModuleBlockItem[]
}

export interface HomeAggregate {
  version: number
  updated_at: string
  modules: {
    module: { blocks: ModuleBlock[] }
    statistic: { items: StatisticItem[] }
    dynamic: { list: DynamicItem[] }
    hot_lemmas: { list: HotLemma[] }
    events_on_history: { list: HistoryEvent[] }
  }
}

export async function getHome(): Promise<HomeAggregate> {
  if (isMockMode()) {
    // 模拟轻微延迟，贴近真实请求体感
    await new Promise((r) => setTimeout(r, 80))
    return homeMock as HomeAggregate
  }
  const base = getApiBase()
  const res = await fetch(`${base}/api/home`)
  if (!res.ok) throw new Error(`首页请求失败：${res.status}`)
  return (await res.json()) as HomeAggregate
}
