<script setup lang="ts">
/**
 * Logo + 搜索框 + 主题切换；提交跳转 /search?word=
 */
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ThemeToggle from './ThemeToggle.vue'

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
        <span class="logo__seal" aria-hidden="true">典</span>
        <span class="logo__text">
          <span class="logo__name">百科Wiki</span>
          <span class="logo__sub">纸墨 · 自建词条</span>
        </span>
      </router-link>

      <form class="search" role="search" @submit.prevent="onSubmit">
        <label class="sr-only" for="global-search">搜索词条</label>
        <input
          id="global-search"
          v-model="word"
          type="search"
          name="word"
          placeholder="检索词条…"
          aria-label="搜索词条"
          autocomplete="off"
        />
        <button type="submit">检索</button>
      </form>

      <ThemeToggle />
    </div>
  </header>
</template>

<style scoped>
.header {
  background: var(--header-bg);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(8px);
}
.header__inner {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 0.9rem 0;
  flex-wrap: wrap;
}
.logo {
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
  color: var(--fg);
  text-decoration: none;
  flex-shrink: 0;
}
.logo:hover {
  text-decoration: none;
  color: var(--fg);
}
.logo__seal {
  width: 2.35rem;
  height: 2.35rem;
  border: 1.5px solid var(--accent);
  color: var(--accent);
  display: grid;
  place-items: center;
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 700;
  transform: rotate(-6deg);
  background: var(--accent-soft);
}
.logo__text {
  display: flex;
  flex-direction: column;
  gap: 0.05rem;
}
.logo__name {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}
.logo__sub {
  font-size: 0.7rem;
  color: var(--fg-muted);
  letter-spacing: 0.18em;
}
.search {
  flex: 1;
  min-width: 200px;
  display: flex;
  align-items: stretch;
  border-bottom: 1.5px solid var(--fg);
  background: transparent;
}
.search input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0.55rem 0.15rem;
  color: var(--fg);
  outline: none;
  border-radius: 0;
}
.search input::placeholder {
  color: var(--fg-faint);
}
.search button {
  border: none;
  border-radius: 0;
  padding: 0.45rem 0.9rem;
  background: var(--control-bg);
  color: var(--control-fg);
  cursor: pointer;
  font-family: var(--font-display);
  font-weight: 600;
  letter-spacing: 0.2em;
  font-size: 0.85rem;
}
.search button:hover {
  background: var(--control-hover-bg);
  color: var(--control-hover-fg);
}
.search button:focus-visible,
.logo:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
</style>
