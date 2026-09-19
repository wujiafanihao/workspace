<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { HotLemma } from '../../api/home'

defineProps<{ list: HotLemma[] }>()
const router = useRouter()

function goSearch(title: string) {
  router.push({ path: '/search', query: { word: title } })
}
</script>

<template>
  <section class="hot card card--ruled" aria-label="热门词条">
    <div class="hot__head">
      <h2 class="hot__title">热门词条</h2>
      <span class="hot__hint">点击即检索</span>
    </div>
    <ol class="hot__list">
      <li v-for="(item, idx) in list" :key="item.lemma_id">
        <button type="button" class="hot__row" @click="goSearch(item.title)">
          <span class="hot__idx" :data-top="idx < 3 ? '1' : undefined">
            {{ String(idx + 1).padStart(2, '0') }}
          </span>
          <span class="hot__name">{{ item.title }}</span>
          <span v-if="item.heat" class="hot__heat">{{ item.heat }}</span>
        </button>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.hot {
  padding: 1rem 0 0.35rem;
}
.hot__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 0 1.25rem 0.65rem;
  border-bottom: 1px solid var(--line);
}
.hot__title {
  margin: 0;
  font-size: 1.05rem;
  letter-spacing: 0.14em;
}
.hot__hint {
  font-size: 0.72rem;
  color: var(--muted);
  letter-spacing: 0.1em;
}
.hot__list {
  list-style: none;
  margin: 0;
  padding: 0.25rem 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}
.hot__row {
  width: 100%;
  display: grid;
  grid-template-columns: 2.2rem 1fr auto;
  gap: 0.55rem;
  align-items: baseline;
  text-align: left;
  border: none;
  background: transparent;
  padding: 0.65rem 1.25rem;
  cursor: pointer;
  color: inherit;
}
.hot__row:hover .hot__name {
  color: var(--cinnabar);
}
.hot__idx {
  font-family: var(--font-display);
  font-size: 0.85rem;
  color: var(--muted);
  letter-spacing: 0.06em;
}
.hot__idx[data-top] {
  color: var(--cinnabar);
  font-weight: 700;
}
.hot__name {
  font-family: var(--font-display);
  font-size: 0.98rem;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 0.06em;
}
.hot__heat {
  color: var(--muted);
  font-size: 0.75rem;
}
</style>
