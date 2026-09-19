<script setup lang="ts">
/** 动态信息流 */
import type { DynamicItem } from '../../api/home'

defineProps<{ list: DynamicItem[] }>()
</script>

<template>
  <section class="feed card" aria-label="最近动态">
    <h2 class="feed__title">最近动态</h2>
    <ul class="feed__list">
      <li v-for="item in list" :key="item.id" class="feed__item">
        <div class="feed__meta">
          <span v-if="item.type" class="feed__type">{{ item.type }}</span>
          <time>{{ item.time }}</time>
        </div>
        <h3 class="feed__heading">{{ item.title }}</h3>
        <p class="feed__summary">{{ item.summary }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.feed {
  padding: 1rem 1.25rem 0.5rem;
}
.feed__title {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  color: var(--ink);
}
.feed__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.feed__item {
  padding: 0.85rem 0;
  border-top: 1px solid var(--border);
}
.feed__item:first-of-type {
  border-top: none;
  padding-top: 0.25rem;
}
.feed__meta {
  display: flex;
  gap: 0.6rem;
  align-items: center;
  color: var(--muted);
  font-size: 0.8rem;
  margin-bottom: 0.25rem;
}
.feed__type {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.05rem 0.4rem;
}
.feed__heading {
  margin: 0;
  font-size: 0.98rem;
  color: var(--ink);
}
.feed__summary {
  margin: 0.3rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
}
</style>
