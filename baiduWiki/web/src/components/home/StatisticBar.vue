<script setup lang="ts">
import type { StatisticItem } from '../../api/home'
defineProps<{ items: StatisticItem[] }>()
</script>

<template>
  <section class="stat card card--ruled" aria-label="站点统计">
    <div v-for="(item, i) in items" :key="i" class="stat__item">
      <div class="stat__value">
        {{ item.value }}
        <span v-if="item.unit" class="stat__unit">{{ item.unit }}</span>
      </div>
      <div class="stat__label">{{ item.label }}</div>
    </div>
  </section>
</template>

<style scoped>
.stat {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 0;
  padding: 0;
  overflow: hidden;
}
.stat__item {
  text-align: left;
  padding: 1.1rem 1.25rem;
  border-right: 1px solid var(--line);
}
.stat__item:last-child {
  border-right: none;
}
.stat__value {
  font-family: var(--font-display);
  font-size: 1.55rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.04em;
  tabular-nums: true;
  font-variant-numeric: tabular-nums;
}
.stat__unit {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--muted);
  margin-left: 0.2rem;
  font-family: var(--font-body);
}
.stat__label {
  color: var(--muted);
  font-size: 0.78rem;
  margin-top: 0.35rem;
  letter-spacing: 0.12em;
}
</style>
