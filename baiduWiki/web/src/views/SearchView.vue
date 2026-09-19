<script setup lang="ts">
/**
 * 搜索页：读 route.query.word，调用 search()，展示 total / 空态
 * Header 通过 watch query 自动回填
 */
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { search, type SearchLemma } from '../api/search'
import SearchResultList from '../components/search/SearchResultList.vue'
import SearchEmpty from '../components/search/SearchEmpty.vue'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const word = ref('')
const total = ref(0)
const list = ref<SearchLemma[]>([])

async function runSearch(w: string) {
  word.value = w
  loading.value = true
  error.value = ''
  try {
    const res = await search(w)
    total.value = res.data.total
    list.value = res.data.list
  } catch (e) {
    error.value = e instanceof Error ? e.message : '搜索失败'
    total.value = 0
    list.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query.word,
  (w) => {
    const q = typeof w === 'string' ? w : ''
    void runSearch(q)
  },
  { immediate: true },
)
</script>

<template>
  <div class="container search-page">
    <header class="search-page__head">
      <h1 v-if="word">以下结果关于：{{ word }}</h1>
      <h1 v-else>搜索词条</h1>
      <p v-if="!loading && !error">共 {{ total }} 条</p>
    </header>

    <p v-if="loading" class="state">正在搜索…</p>
    <p v-else-if="error" class="state state--err">{{ error }}</p>
    <SearchEmpty v-else-if="total === 0" :word="word" />
    <SearchResultList v-else :list="list" />
  </div>
</template>

<style scoped>
.search-page {
  display: grid;
  gap: 1rem;
}
.search-page__head h1 {
  margin: 0;
  font-size: 1.35rem;
  color: var(--ink);
}
.search-page__head p {
  margin: 0.35rem 0 0;
  color: var(--muted);
}
.state {
  color: var(--muted);
}
.state--err {
  color: #b91c1c;
}
</style>
