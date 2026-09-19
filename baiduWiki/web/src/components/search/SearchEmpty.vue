<script setup lang="ts">
/** 搜索空态 */
defineProps<{ word: string }>()
</script>

<template>
  <div class="empty card" role="status">
    <h2>未找到相关词条</h2>
    <p v-if="word">没有与「{{ word }}」匹配的结果，换个关键词试试。</p>
    <p v-else>请输入关键词后搜索。</p>
    <p class="hint">可试：苹果、量子、长征</p>
  </div>
</template>

<style scoped>
.empty {
  padding: 2.5rem 1.5rem;
  text-align: center;
}
.empty h2 {
  margin: 0;
  color: var(--ink);
  font-size: 1.15rem;
}
.empty p {
  margin: 0.6rem 0 0;
  color: var(--muted);
}
.hint {
  color: var(--brand) !important;
  font-weight: 600;
}
</style>
