<script setup lang="ts">
/**
 * Logo + 搜索框；提交跳转 /search?word=
 * 支持路由 query 回填（搜索页）
 */
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const word = ref('')

watch(
  () => route.query.word,
  (w) => {
    word.value = typeof w === 'string' ? w : ''
  },
  { immediate: true },
)

function onSubmit() {
  const q = word.value.trim()
  router.push({ path: '/search', query: q ? { word: q } : {} })
}
</script>

<template>
  <header class="header">
    <div class="container header__inner">
      <router-link to="/" class="logo" aria-label="百科Wiki 首页">
        <span class="logo__mark">百</span>
        <span class="logo__text">百科Wiki</span>
      </router-link>

      <form class="search" role="search" @submit.prevent="onSubmit">
        <label class="sr-only" for="global-search">搜索词条</label>
        <input
          id="global-search"
          v-model="word"
          type="search"
          name="word"
          placeholder="搜索词条，例如：量子、苹果、长征"
          aria-label="搜索词条"
          autocomplete="off"
        />
        <button type="submit">搜索</button>
      </form>
    </div>
  </header>
</template>

<style scoped>
.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 20;
}
.header__inner {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 0.85rem 0;
  flex-wrap: wrap;
}
.logo {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--ink);
  text-decoration: none;
  font-weight: 700;
  flex-shrink: 0;
}
.logo:hover {
  text-decoration: none;
}
.logo__mark {
  width: 2rem;
  height: 2rem;
  border-radius: 8px;
  background: var(--brand);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 0.95rem;
}
.logo__text {
  font-size: 1.1rem;
  letter-spacing: 0.02em;
}
.search {
  flex: 1;
  min-width: 220px;
  display: flex;
  gap: 0.5rem;
}
.search input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.55rem 0.85rem;
  background: var(--bg);
  color: var(--ink);
  outline: none;
}
.search input:focus {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-soft);
}
.search button {
  border: none;
  border-radius: 8px;
  padding: 0.55rem 1.1rem;
  background: var(--brand);
  color: #fff;
  cursor: pointer;
  font-weight: 600;
}
.search button:hover {
  filter: brightness(1.05);
}
.search button:active {
  transform: translateY(1px);
}
</style>
