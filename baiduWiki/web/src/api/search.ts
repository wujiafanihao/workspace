/**
 * 搜索：mock 按 word 过滤，或 GET /api/search?word=
 */
import { getApiBase, isMockMode } from './mode'
import searchMock from '../mock/search.json'

/** 搜索合同字段 */
export interface SearchLemma {
  lemma_id: string
  title: string
  summary: string
  cover: string
  url_path: string
}

export interface SearchResponse {
  code: number
  message: string
  data: {
    word: string
    total: number
    list: SearchLemma[]
  }
}

export async function search(word: string, page = 1): Promise<SearchResponse> {
  const q = word.trim()
  if (isMockMode()) {
    await new Promise((r) => setTimeout(r, 60))
    const all = (searchMock as SearchResponse).data.list
    const list = q
      ? all.filter(
          (item) =>
            item.title.includes(q) ||
            item.summary.includes(q) ||
            item.lemma_id.includes(q),
        )
      : []
    return {
      code: 0,
      message: 'ok',
      data: { word: q, total: list.length, list },
    }
  }
  const base = getApiBase()
  const params = new URLSearchParams({ word: q, page: String(page) })
  const res = await fetch(`${base}/api/search?${params}`)
  if (!res.ok) throw new Error(`搜索请求失败：${res.status}`)
  return (await res.json()) as SearchResponse
}
