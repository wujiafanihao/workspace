<script setup lang="ts">
import type { SearchLemma } from '../../api/search'
defineProps<{ item: SearchLemma }>()
</script>

<template>
  <article class="item">
    <div class="item__cover" aria-hidden="true">
      <img v-if="item.cover" :src="item.cover" :alt="item.title" />
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
  grid-template-columns: 64px 1fr;
  gap: 1.1rem;
  padding: 1.15rem 0;
  border-bottom: 1px solid var(--line);
}
.item:last-child {
  border-bottom: none;
}
.item__cover {
  width: 64px;
  height: 64px;
  overflow: hidden;
  background: var(--cover-bg);
  display: grid;
  place-items: center;
  border: 1px solid var(--line);
}
.item__cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: var(--cover-filter);
}
.item__placeholder {
  color: var(--cinnabar);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.15rem;
}
.item__title {
  margin: 0;
  font-size: 1.15rem;
  letter-spacing: 0.08em;
}
.item__summary {
  margin: 0.4rem 0 0;
  color: var(--body);
  font-size: 0.92rem;
}
.item__path {
  margin: 0.4rem 0 0;
  color: var(--muted);
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
</style>
