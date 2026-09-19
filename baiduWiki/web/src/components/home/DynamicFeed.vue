<script setup lang="ts">
import type { DynamicItem } from '../../api/home'
defineProps<{ list: DynamicItem[] }>()
</script>

<template>
  <section class="feed card card--ruled" aria-label="最近动态">
    <h2 class="feed__title">馆内动态</h2>
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
  padding: 1.05rem 1.2rem 0.65rem;
}
.feed__title {
  margin: 0 0 0.85rem;
  font-size: 1.05rem;
  letter-spacing: 0.14em;
  padding-bottom: 0.55rem;
  border-bottom: 1px dashed var(--line);
}
.feed__list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.feed__item {
  padding: 0.9rem 0;
  border-top: 1px solid var(--line);
}
.feed__item:first-of-type {
  border-top: none;
  padding-top: 0.15rem;
}
.feed__meta {
  display: flex;
  gap: 0.65rem;
  align-items: center;
  color: var(--muted);
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  margin-bottom: 0.3rem;
}
.feed__type {
  color: var(--cinnabar);
  font-weight: 600;
}
.feed__heading {
  margin: 0;
  font-size: 0.98rem;
  letter-spacing: 0.06em;
}
.feed__summary {
  margin: 0.3rem 0 0;
  color: var(--muted);
  font-size: 0.88rem;
}
</style>
