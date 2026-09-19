<script setup lang="ts">
/** 历史上的今天 */
import type { HistoryEvent } from '../../api/home'

defineProps<{ list: HistoryEvent[] }>()
</script>

<template>
  <section class="eoh card" aria-label="历史上的今天">
    <h2 class="eoh__title">历史上的今天</h2>
    <ul class="eoh__list">
      <li v-for="item in list" :key="item.id" class="eoh__item">
        <div class="eoh__year">{{ item.year }}</div>
        <div>
          <h3 class="eoh__heading">{{ item.title }}</h3>
          <p class="eoh__summary">{{ item.summary }}</p>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.eoh {
  padding: 1rem 1.25rem 0.75rem;
}
.eoh__title {
  margin: 0 0 0.85rem;
  font-size: 1.05rem;
  color: var(--ink);
}
.eoh__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.85rem;
}
.eoh__item {
  display: grid;
  grid-template-columns: 4.5rem 1fr;
  gap: 0.85rem;
  align-items: start;
}
.eoh__year {
  font-weight: 700;
  color: var(--brand);
  font-size: 1.05rem;
  padding-top: 0.1rem;
}
.eoh__heading {
  margin: 0;
  font-size: 0.98rem;
  color: var(--ink);
}
.eoh__summary {
  margin: 0.25rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
}
</style>
