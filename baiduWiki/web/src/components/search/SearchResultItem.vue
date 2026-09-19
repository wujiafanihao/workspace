<script setup lang="ts">
/** 单条搜索结果：title / summary / cover */
import type { SearchLemma } from '../../api/search'

defineProps<{ item: SearchLemma }>()
</script>

<template>
  <article class="item">
    <div class="item__cover" aria-hidden="true">
      <img
        v-if="item.cover"
        :src="item.cover"
        :alt="item.title"
      />
      <span v-else class="item__placeholder">词</span>
    </div>
    <div class="item__body">
      <h2 class="item__title">{{ item.title }}</h2>
      <p class="item__summary">{{ item.summary }}</p>
      <p class="item__path">{{ item.url_path }}</p>
    </div>
  </article>
</template>

<style scoped>
.item {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 1rem;
  padding: 1rem 0;
  border-bottom: 1px solid var(--border);
}
.item__cover {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--brand-soft);
  display: grid;
  place-items: center;
  border: 1px solid var(--border);
}
.item__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.item__placeholder {
  color: var(--brand);
  font-weight: 700;
  font-size: 1.25rem;
}
.item__title {
  margin: 0;
  font-size: 1.1rem;
  color: var(--ink);
}
.item__summary {
  margin: 0.35rem 0 0;
  color: var(--body);
}
.item__path {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.8rem;
}
</style>
