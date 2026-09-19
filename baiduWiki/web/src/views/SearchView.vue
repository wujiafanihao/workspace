<script setup lang="ts">
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
      <p class="eyebrow">SEARCH</p>
      <h1 v-if="word">「{{ word }}」</h1>
      <h1 v-else>检索</h1>
      <p v-if="!loading && !error" class="meta">共 {{ total }} 条相关词条</p>
    </header>

    <p v-if="loading" class="state">正在检索…</p>
    <p v-else-if="error" class="state state--err">{{ error }}</p>
    <SearchEmpty v-else-if="total === 0" :word="word" />
    <SearchResultList v-else :list="list" />
  </div>
</template>

<style scoped>
.search-page {
  display: grid;
  gap: 1.25rem;
}
.search-page__head {
  border-bottom: 1px solid var(--line);
  padding-bottom: 0.85rem;
  max-width: 40rem;
}
.eyebrow {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.28em;
  color: var(--cinnabar);
  font-weight: 600;
}
.search-page__head h1 {
  margin: 0.3rem 0 0;
  font-size: clamp(1.6rem, 3vw, 2.1rem);
  letter-spacing: 0.12em;
}
.meta {
  margin: 0.45rem 0 0;
  color: var(--muted);
  font-size: 0.88rem;
}
.state {
  color: var(--muted);
  font-family: var(--font-display);
}
.state--err {
  color: var(--cinnabar);
}
</style>
