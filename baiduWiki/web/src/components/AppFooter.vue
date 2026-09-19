<script setup lang="ts">
/** 页脚 */
</script>

<template>
  <footer class="footer">
    <div class="container footer__inner">
      <p>百科Wiki · 阶段一演示（本地 mock）</p>
      <p>自建词条 · 不接外网 BFF</p>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  border-top: 1px solid var(--line);
  margin-top: 2rem;
  padding: 1.5rem 0 2rem;
  color: var(--muted);
  font-size: 0.8rem;
  letter-spacing: 0.06em;
}
.footer__inner {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 2rem;
  justify-content: space-between;
  border-top: 3px double var(--line);
  padding-top: 1.1rem;
}
p {
  margin: 0;
}
</style>
