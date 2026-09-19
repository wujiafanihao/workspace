<script setup lang="ts">
import type { HistoryEvent } from '../../api/home'
defineProps<{ list: HistoryEvent[] }>()
</script>

<template>
  <section class="eoh card card--ruled" aria-label="历史上的今天">
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
  padding: 1.05rem 1.25rem 1rem;
}
.eoh__title {
  margin: 0 0 1rem;
  font-size: 1.05rem;
  letter-spacing: 0.14em;
  padding-bottom: 0.55rem;
  border-bottom: 1px dashed var(--line);
}
.eoh__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 1rem;
}
.eoh__item {
  display: grid;
  grid-template-columns: 5rem 1fr;
  gap: 1rem;
  align-items: start;
}
.eoh__year {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--cinnabar);
  font-size: 1.15rem;
  letter-spacing: 0.04em;
  border-right: 1px solid var(--line);
  padding-right: 0.85rem;
  line-height: 1.2;
}
.eoh__heading {
  margin: 0;
  font-size: 1rem;
  letter-spacing: 0.06em;
}
.eoh__summary {
  margin: 0.3rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
}
</style>
