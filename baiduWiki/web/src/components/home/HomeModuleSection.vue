<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { ModuleBlock } from '../../api/home'

defineProps<{ block: ModuleBlock }>()
const router = useRouter()

function goSearch(title: string) {
  router.push({ path: '/search', query: { word: title } })
}
</script>

<template>
  <section class="mod card card--ruled" :aria-label="block.title">
    <h2 class="mod__title">{{ block.title }}</h2>
    <div class="mod__grid">
      <button
        v-for="item in block.items"
        :key="item.lemma_id"
        type="button"
        class="mod__card"
        @click="goSearch(item.title)"
      >
        <h3>{{ item.title }}</h3>
        <p>{{ item.summary }}</p>
      </button>
    </div>
  </section>
</template>

<style scoped>
.mod {
  padding: 1.05rem 1.25rem 1.2rem;
}
.mod__title {
  margin: 0 0 0.95rem;
  font-size: 1.05rem;
  letter-spacing: 0.14em;
  padding-bottom: 0.55rem;
  border-bottom: 1px dashed var(--line);
}
.mod__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 0.85rem;
}
.mod__card {
  text-align: left;
  border: none;
  border-top: 2px solid var(--ink);
  background: transparent;
  padding: 0.75rem 0.15rem 0.35rem;
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.mod__card:hover {
  border-top-color: var(--cinnabar);
}
.mod__card h3 {
  margin: 0;
  font-size: 1rem;
  letter-spacing: 0.08em;
}
.mod__card:hover h3 {
  color: var(--cinnabar);
}
.mod__card p {
  margin: 0.4rem 0 0;
  color: var(--muted);
  font-size: 0.86rem;
  line-height: 1.55;
}
</style>
