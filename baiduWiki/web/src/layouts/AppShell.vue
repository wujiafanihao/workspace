<script setup lang="ts">
/**
 * 顶栏 + 主内容 + 页脚
 */
import AppHeader from '../components/AppHeader.vue'
import AppFooter from '../components/AppFooter.vue'
</script>

<template>
  <div class="shell">
    <AppHeader />
    <main class="shell__main">
      <router-view />
    </main>
    <AppFooter />
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.shell__main {
  flex: 1;
  padding: 1.25rem 0 2.5rem;
}
</style>
