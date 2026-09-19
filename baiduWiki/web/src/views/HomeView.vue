<script setup lang="ts">
/**
 * 首页：加载 getHome()，渲染全部模块
 */
import { onMounted, ref } from 'vue'
import { getHome, type HomeAggregate } from '../api/home'
import StatisticBar from '../components/home/StatisticBar.vue'
import HotLemmasRail from '../components/home/HotLemmasRail.vue'
import DynamicFeed from '../components/home/DynamicFeed.vue'
import EventsOnHistoryCard from '../components/home/EventsOnHistoryCard.vue'
import HomeModuleSection from '../components/home/HomeModuleSection.vue'

const loading = ref(true)
const error = ref('')
const data = ref<HomeAggregate | null>(null)

onMounted(async () => {
  try {
    data.value = await getHome()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="container home">
    <header class="home__hero">
      <h1>发现知识</h1>
      <p>阶段一演示 · 数据来自本地 mock</p>
    </header>

    <p v-if="loading" class="state">正在加载首页…</p>
    <p v-else-if="error" class="state state--err">{{ error }}</p>

    <template v-else-if="data">
      <StatisticBar :items="data.modules.statistic.items" />
      <HotLemmasRail :list="data.modules.hot_lemmas.list" />

      <div class="home__grid">
        <div class="home__col">
          <HomeModuleSection
            v-for="block in data.modules.module.blocks"
            :key="block.id"
            :block="block"
          />
        </div>
        <DynamicFeed :list="data.modules.dynamic.list" />
      </div>

      <EventsOnHistoryCard :list="data.modules.events_on_history.list" />
    </template>
  </div>
</template>

<style scoped>
.home {
  display: grid;
  gap: 1rem;
}
.home__hero h1 {
  margin: 0;
  font-size: 1.6rem;
  color: var(--ink);
}
.home__hero p {
  margin: 0.35rem 0 0.25rem;
  color: var(--muted);
}
.home__grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 1rem;
  align-items: start;
}
.home__col {
  display: grid;
  gap: 1rem;
}
.state {
  color: var(--muted);
}
.state--err {
  color: #b91c1c;
}
@media (max-width: 800px) {
  .home__grid {
    grid-template-columns: 1fr;
  }
}
</style>
