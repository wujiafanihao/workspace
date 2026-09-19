<script setup lang="ts">
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
  padding: 1.75rem 0 1rem;
}
</style>
