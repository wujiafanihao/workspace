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
    <header class="masthead">
      <p class="masthead__eyebrow">ENCYCLOPEDIA · HOME</p>
      <h1>词条馆</h1>
      <p class="masthead__lede">
        自建知识首页。下列模块来自本地 mock，字段已对齐后续 API 合同。
      </p>
    </header>

    <p v-if="loading" class="state">正在编排首页…</p>
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
  gap: 1.35rem;
}
.masthead {
  padding: 0.5rem 0 0.25rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 0.35rem;
  max-width: 36rem;
}
.masthead__eyebrow {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.28em;
  color: var(--cinnabar);
  font-weight: 600;
}
.masthead h1 {
  margin: 0.35rem 0 0;
  font-size: clamp(2rem, 4vw, 2.65rem);
  font-weight: 700;
  letter-spacing: 0.18em;
}
.masthead__lede {
  margin: 0.65rem 0 1rem;
  color: var(--muted);
  font-size: 0.92rem;
  max-width: 32rem;
}
.home__grid {
  display: grid;
  grid-template-columns: 1.45fr 0.9fr;
  gap: 1.25rem;
  align-items: start;
}
.home__col {
  display: grid;
  gap: 1.25rem;
}
.state {
  color: var(--muted);
  font-family: var(--font-display);
}
.state--err {
  color: var(--cinnabar);
}
@media (max-width: 800px) {
  .home__grid {
    grid-template-columns: 1fr;
  }
}
</style>
