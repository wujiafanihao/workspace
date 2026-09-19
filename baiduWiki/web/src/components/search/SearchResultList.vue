<script setup lang="ts">
/** 搜索结果列表容器 */
import type { SearchLemma } from '../../api/search'
import SearchResultItem from './SearchResultItem.vue'

defineProps<{ list: SearchLemma[] }>()
</script>

<template>
  <div class="list" role="list">
    <SearchResultItem
      v-for="item in list"
      :key="item.lemma_id"
      :item="item"
      role="listitem"
    />
  </div>
</template>

<style scoped>
.list {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.25rem 1.25rem;
  box-shadow: var(--shadow);
}
</style>
