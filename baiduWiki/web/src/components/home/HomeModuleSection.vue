<script setup lang="ts">
/** 通用首页模块区块（标题 + 词条卡片） */
import { useRouter } from 'vue-router'
import type { ModuleBlock } from '../../api/home'

defineProps<{ block: ModuleBlock }>()
const router = useRouter()

function goSearch(title: string) {
  router.push({ path: '/search', query: { word: title } })
}
</script>

<template>
  <section class="mod card" :aria-label="block.title">
    <h2 class="mod__title">{{ block.title }}</h2>
    <div class="mod__grid">
      <button
        v-for="item in block.items"
        :key="item.lemma_id"
        type="button"
        class="mod__card"
        @click="goSearch(item.title)"
      >
        <h3>{{ item.title }}</h3>
        <p>{{ item.summary }}</p>
      </button>
    </div>
  </section>
</template>

<style scoped>
.mod {
  padding: 1rem 1.25rem 1.15rem;
}
.mod__title {
  margin: 0 0 0.85rem;
  font-size: 1.05rem;
  color: var(--ink);
}
.mod__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
}
.mod__card {
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  padding: 0.85rem;
  cursor: pointer;
}
.mod__card:hover {
  border-color: var(--brand);
  background: var(--brand-soft);
}
.mod__card h3 {
  margin: 0;
  font-size: 0.98rem;
  color: var(--ink);
}
.mod__card p {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.88rem;
}
</style>
