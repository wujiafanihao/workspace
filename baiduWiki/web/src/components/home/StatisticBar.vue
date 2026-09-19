<script setup lang="ts">
/** 首页统计数字条 */
import type { StatisticItem } from '../../api/home'

defineProps<{ items: StatisticItem[] }>()
</script>

<template>
  <section class="stat card" aria-label="站点统计">
    <div
      v-for="(item, i) in items"
      :key="i"
      class="stat__item"
    >
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
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  padding: 1rem 1.25rem;
}
.stat__item {
  text-align: center;
  padding: 0.5rem;
}
.stat__value {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.01em;
}
.stat__unit {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--muted);
  margin-left: 0.15rem;
}
.stat__label {
  color: var(--muted);
  font-size: 0.85rem;
  margin-top: 0.2rem;
}
</style>
