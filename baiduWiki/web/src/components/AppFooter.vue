<script setup lang="ts">
/**
 * 页脚：说明与备案占位
 */
</script>

<template>
  <footer class="footer">
    <div class="container footer__inner">
      <p>百科Wiki · 阶段一演示（mock 数据）</p>
      <p class="muted">不连接真实后端 · 不使用百度 token</p>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  border-top: 1px solid var(--border);
  background: var(--surface);
  padding: 1.25rem 0;
  color: var(--muted);
  font-size: 0.875rem;
}
.footer__inner {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.5rem;
  justify-content: space-between;
}
.muted {
  margin: 0;
}
p {
  margin: 0;
}
</style>
