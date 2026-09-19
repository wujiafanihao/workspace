<script setup lang="ts">
/** 热词轨道：点击跳转搜索 */
import { useRouter } from 'vue-router'
import type { HotLemma } from '../../api/home'

defineProps<{ list: HotLemma[] }>()
const router = useRouter()

function goSearch(title: string) {
  router.push({ path: '/search', query: { word: title } })
}
</script>

<template>
  <section class="hot card" aria-label="热门词条">
    <h2 class="hot__title">热门词条</h2>
    <div class="hot__rail">
      <button
        v-for="item in list"
        :key="item.lemma_id"
        type="button"
        class="hot__chip"
        @click="goSearch(item.title)"
      >
        {{ item.title }}
        <span v-if="item.heat" class="hot__heat">{{ item.heat }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.hot {
  padding: 1rem 1.25rem 1.15rem;
}
.hot__title {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  color: var(--ink);
}
.hot__rail {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.hot__chip {
  border: 1px solid var(--border);
  background: var(--brand-soft);
  color: var(--brand);
  border-radius: 999px;
  padding: 0.35rem 0.85rem;
  cursor: pointer;
  font-weight: 600;
}
.hot__chip:hover {
  border-color: var(--brand);
}
.hot__heat {
  margin-left: 0.35rem;
  color: var(--muted);
  font-weight: 500;
  font-size: 0.75rem;
}
</style>
