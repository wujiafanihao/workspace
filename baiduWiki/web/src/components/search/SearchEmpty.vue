<script setup lang="ts">
defineProps<{ word: string }>()
</script>

<template>
  <div class="empty card card--ruled" role="status">
    <h2>馆藏未收录</h2>
    <p v-if="word">没有与「{{ word }}」匹配的词条，换个写法再试。</p>
    <p v-else>请在顶栏输入关键词后检索。</p>
    <p class="hint">可试：苹果 · 量子 · 长征</p>
  </div>
</template>

<style scoped>
.empty {
  padding: 2.75rem 1.5rem;
  text-align: left;
}
.empty h2 {
  margin: 0;
  font-size: 1.25rem;
  letter-spacing: 0.16em;
}
.empty p {
  margin: 0.7rem 0 0;
  color: var(--muted);
  max-width: 28rem;
}
.hint {
  color: var(--cinnabar) !important;
  font-family: var(--font-display);
  letter-spacing: 0.08em;
  margin-top: 1.1rem !important;
}
</style>
