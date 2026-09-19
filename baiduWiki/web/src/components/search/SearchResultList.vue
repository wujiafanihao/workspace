<script setup lang="ts">
import type { SearchLemma } from '../../api/search'
import SearchResultItem from './SearchResultItem.vue'
defineProps<{ list: SearchLemma[] }>()
</script>

<template>
  <div class="list card card--ruled" role="list">
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
  padding: 0.15rem 1.35rem 0.35rem;
}
</style>
